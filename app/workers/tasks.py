import asyncio
import logging
import httpx
from datetime import datetime, timezone
from celery import Task
from celery.exceptions import MaxRetriesExceededError
from app.workers.celery_app import celery_app
from app.database.mongodb import init_db
from app.models.notification import Notification, NotificationStatus
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.providers.email_provider import EmailProvider
from app.providers.sms_provider import SMSProvider
from app.providers.push_provider import PushProvider
from app.services.analytics_service import AnalyticsService
from app.utils.circuit_breaker import CircuitBreakerOpenException
from app.utils.exceptions import NotificationException

logger = logging.getLogger(__name__)

# Cache connection init flag
_db_initialized = False

async def ensure_db() -> None:
    """
    Ensures Beanie is initialized in the current worker process context.
    """
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

def run_async(coro):
    """
    Helper to run asynchronous coroutines from synchronous Celery tasks.
    """
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # Fallback if loop is already running (e.g. during testing)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

@celery_app.task(bind=True, max_retries=3)
def send_notification_task(self: Task, notification_id: str) -> str:
    """
    Celery task that processes and sends multi-channel notifications.
    Supports channel deduplication upon retry, structured logging,
    and automatic exponential backoff retries.
    """
    return run_async(async_execute_task(self, notification_id))

# Extend Task to keep code clean and testable in async
async def async_execute_task(self_task: Task, notification_id: str) -> str:
    await ensure_db()

    notification = await NotificationRepository.get_by_id(notification_id)
    if not notification:
        logger.error(f"Notification with ID {notification_id} not found in worker.")
        return "NOT_FOUND"

    if notification.status in (NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.SKIPPED):
        logger.info(f"Notification {notification_id} is already in state '{notification.status}'. Skipping.")
        return notification.status

    # Update notification to Processing
    await NotificationRepository.update_status(
        notification=notification,
        status=NotificationStatus.PROCESSING,
        log_message="Celery worker started processing notification."
    )

    # Resolve recipient contact information
    user = await User.get(notification.user_id)
    if not user:
        err_msg = f"User with ID {notification.user_id} not found during delivery attempt."
        await NotificationRepository.update_status(
            notification=notification,
            status=NotificationStatus.FAILED,
            log_message=err_msg
        )
        await trigger_webhook_dispatch(notification)
        return NotificationStatus.FAILED

    # Track already sent channels during previous retries to avoid duplication
    delivered_channels = set()
    for log in notification.delivery_logs:
        if log.get("status") == "Channel_Delivered":
            delivered_channels.add(log.get("channel"))

    channels_to_send = [c for c in notification.channels if c not in delivered_channels]
    
    if not channels_to_send:
        # All channels were already delivered in a previous run
        await NotificationRepository.update_status(
            notification=notification,
            status=NotificationStatus.DELIVERED,
            log_message="All channels already marked as Delivered in database."
        )
        await trigger_webhook_dispatch(notification)
        return NotificationStatus.DELIVERED

    failures = {}
    successes = []

    # Initialize providers
    email_prov = EmailProvider()
    sms_prov = SMSProvider()
    push_prov = PushProvider()

    for channel in channels_to_send:
        try:
            logger.info(f"Attempting delivery on channel '{channel}' for notification {notification_id}")
            msg_body = notification.rendered_message.get(channel, "")
            
            if channel == "email":
                # Parse subject if possible
                subject = "Notification"
                body = msg_body
                if msg_body.startswith("Subject: "):
                    parts = msg_body.split("\n\n", 1)
                    subject = parts[0].replace("Subject: ", "")
                    body = parts[1] if len(parts) > 1 else ""
                
                await email_prov.send(user.email, subject, body)
                
            elif channel == "sms":
                await sms_prov.send(user.phone, msg_body)
                
            elif channel == "push":
                await push_prov.send(str(user.id), msg_body)
                
            # Log success for individual channel
            notification.delivery_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "Channel_Delivered",
                "channel": channel,
                "message": f"Successfully delivered via {channel}"
            })
            successes.append(channel)
            await AnalyticsService.record_event(channel=channel, status=NotificationStatus.DELIVERED)
            
        except CircuitBreakerOpenException as cbe:
            err_msg = f"Circuit breaker is OPEN for {channel}."
            logger.error(err_msg)
            failures[channel] = err_msg
            notification.delivery_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "Channel_Failed",
                "channel": channel,
                "message": err_msg
            })
            await AnalyticsService.record_event(channel=channel, status=NotificationStatus.FAILED)
            
        except Exception as e:
            err_msg = f"Failed to send on {channel}: {str(e)}"
            logger.error(err_msg, exc_info=True)
            failures[channel] = err_msg
            notification.delivery_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "Channel_Failed",
                "channel": channel,
                "message": err_msg
            })
            await AnalyticsService.record_event(channel=channel, status=NotificationStatus.FAILED)

    # Update state in DB
    await notification.save()

    if failures:
        # Determine retry or terminal failure
        retries = self_task.request.retries
        if retries < self_task.max_retries:
            # We must retry!
            # Set state to Retrying
            await NotificationRepository.update_status(
                notification=notification,
                status=NotificationStatus.RETRYING,
                log_message=f"Delivery failed for channels: {list(failures.keys())}. Scheduling retry."
            )
            # Calculate backoff: 1s, 2s, 4s
            countdown = 2 ** retries
            logger.info(f"Retrying task in {countdown} seconds (Retry {retries + 1}/{self_task.max_retries})")
            
            # Raise retry exception
            self_task.retry(countdown=countdown)
        else:
            # Terminal failure
            await NotificationRepository.update_status(
                notification=notification,
                status=NotificationStatus.FAILED,
                log_message=f"Delivery failed permanently for channels: {list(failures.keys())}. Retries exhausted."
            )
            await trigger_webhook_dispatch(notification)
            return NotificationStatus.FAILED
    else:
        # All channels sent successfully!
        await NotificationRepository.update_status(
            notification=notification,
            status=NotificationStatus.DELIVERED,
            log_message="All channels delivered successfully."
        )
        await trigger_webhook_dispatch(notification)
        return NotificationStatus.DELIVERED

# Attach helper method to Celery task class for clean code
celery_app.task(bind=True, max_retries=3)(send_notification_task)
send_notification_task.async_execute = async_execute_task

async def trigger_webhook_dispatch(notification: Notification) -> None:
    """
    Enqueues the webhook dispatch task if a webhook URL was configured.
    """
    if notification.webhook_url:
        logger.info(f"Queueing webhook dispatch for notification {notification.id} to {notification.webhook_url}")
        # Send payload
        payload = {
            "notification_id": str(notification.id),
            "status": notification.status,
            "delivery_logs": notification.delivery_logs,
            "updated_at": notification.updated_at.isoformat() if notification.updated_at else None
        }
        celery_app.send_task(
            "app.workers.tasks.dispatch_webhook_task",
            args=[notification.webhook_url, payload]
        )

@celery_app.task(bind=True, max_retries=3)
def dispatch_webhook_task(self: Task, url: str, payload: dict) -> str:
    """
    Background worker task to dispatch delivery reports to a registered webhook URL.
    Attempts with exponential backoff if the client server is unavailable.
    """
    return run_async(async_execute_webhook(self, url, payload))

async def async_execute_webhook(self_task: Task, url: str, payload: dict) -> str:
    logger.info(f"Dispatching webhook to URL: {url}")
    try:
        async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            if response.status_code >= 400:
                raise Exception(f"Webhook returned HTTP status code: {response.status_code}")
                
        logger.info(f"Webhook successfully dispatched to {url}.")
        return "SUCCESS"
    except Exception as e:
        logger.error(f"Webhook dispatch failed to {url}: {e}", exc_info=True)
        retries = self_task.request.retries
        if retries < self_task.max_retries:
            countdown = 2 ** retries
            self_task.retry(countdown=countdown)
        else:
            logger.error(f"Webhook dispatch permanently failed for {url} after {self_task.max_retries} retries.")
            return "FAILED"

dispatch_webhook_task.async_execute_webhook = async_execute_webhook
