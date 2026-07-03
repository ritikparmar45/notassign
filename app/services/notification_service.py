import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.models.notification import Notification, NotificationStatus, NotificationPriority
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.template_repository import TemplateRepository
from app.services.preference_service import PreferenceService
from app.services.analytics_service import AnalyticsService
from app.utils.template_engine import TemplateEngine
from app.utils.exceptions import ValidationException, TemplateException
from app.utils.priority_queue import PriorityQueueUtil
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Core service for orchestrating notification creation, template rendering,
    preference checks, database logging, and Celery queue dispatching.
    """
    @staticmethod
    async def create_notification(data: NotificationCreate, idempotency_key: str = None) -> Notification:
        """
        Creates a new notification request, validates parameters, checks preferences,
        renders content, and routes to Celery for delivery.
        """
        user_id = data.user_id
        
        # 1. Fetch User details
        user = await UserRepository.get_by_id(user_id)
        if not user:
            raise ValidationException(f"User with ID {user_id} not found.")

        # 2. Fetch Template details
        template = await TemplateRepository.get_by_name(data.template_name)
        if not template:
            raise ValidationException(f"Template with name '{data.template_name}' not found.")

        # 3. Check User Preferences for enabled channels
        prefs = await PreferenceService.get_by_user_id(user_id)
        
        active_channels: List[str] = []
        skipped_channels: List[str] = []

        for ch in data.channels:
            if ch == "email":
                if prefs.email_enabled:
                    active_channels.append(ch)
                else:
                    skipped_channels.append(ch)
            elif ch == "sms":
                if prefs.sms_enabled:
                    active_channels.append(ch)
                else:
                    skipped_channels.append(ch)
            elif ch == "push":
                if prefs.push_enabled:
                    active_channels.append(ch)
                else:
                    skipped_channels.append(ch)

        # 4. Render template content
        # We render the template for all requested channels (both active and skipped,
        # but only active ones will be sent to celery).
        rendered_messages: Dict[str, str] = {}
        try:
            # Render subject for email if present
            email_subject = ""
            if "email" in data.channels and template.subject:
                email_subject = TemplateEngine.render(template.subject, data.variables)

            rendered_body = TemplateEngine.render(template.body, data.variables)
            
            for ch in data.channels:
                if ch == "email":
                    # Combine subject and body for email JSON record
                    rendered_messages["email"] = f"Subject: {email_subject}\n\n{rendered_body}"
                else:
                    rendered_messages[ch] = rendered_body

        except TemplateException as te:
            logger.error(f"Template rendering failed: {te.message}")
            raise ValidationException(te.message, {"missing_variables": te.missing_variables})

        # Determine initial status
        if not active_channels:
            initial_status = NotificationStatus.SKIPPED
            log_msg = f"All requested channels ({', '.join(data.channels)}) were disabled by user preferences."
        else:
            initial_status = NotificationStatus.QUEUED
            log_msg = f"Notification queued for delivery via channels: {', '.join(active_channels)}."
            if skipped_channels:
                log_msg += f" Skipped channels due to user preferences: {', '.join(skipped_channels)}."

        # 5. Save notification record to MongoDB
        notification = await NotificationRepository.create(
            user_id=user_id,
            channels=active_channels if active_channels else data.channels,
            priority=data.priority,
            template_name=data.template_name,
            variables=data.variables,
            rendered_message=rendered_messages,
            status=initial_status,
            idempotency_key=idempotency_key,
            webhook_url=data.webhook_url
        )

        # Update logs on initial save
        await NotificationRepository.update_status(
            notification=notification,
            status=initial_status,
            log_message=log_msg
        )

        # Record initial analytical entries
        for ch in active_channels:
            await AnalyticsService.record_event(channel=ch, status=NotificationStatus.QUEUED)
        for ch in skipped_channels:
            await AnalyticsService.record_event(channel=ch, status=NotificationStatus.SKIPPED)

        # 6. Queue task in Celery if there are active channels
        if active_channels:
            queue_name = PriorityQueueUtil.get_queue_name(data.priority)
            celery_priority = PriorityQueueUtil.get_celery_priority(data.priority)
            
            logger.info(
                f"Dispatching notification {notification.id} to Celery queue '{queue_name}' "
                f"with priority {celery_priority}."
            )
            
            # Use app.workers.tasks.send_notification_task namespace
            celery_app.send_task(
                "app.workers.tasks.send_notification_task",
                args=[str(notification.id)],
                queue=queue_name,
                priority=celery_priority
            )

        return notification
