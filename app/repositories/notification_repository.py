from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from beanie import PydanticObjectId
from app.models.notification import Notification

class NotificationRepository:
    """
    Repository class handling operations on the Notifications collection.
    """
    @staticmethod
    async def get_by_id(notification_id: str) -> Optional[Notification]:
        """
        Retrieves a notification by its MongoDB ObjectId string.
        """
        try:
            return await Notification.get(PydanticObjectId(notification_id))
        except Exception:
            return None

    @staticmethod
    async def get_by_idempotency_key(key: str) -> Optional[Notification]:
        """
        Retrieves a notification matching the idempotency key.
        """
        return await Notification.find_one(Notification.idempotency_key == key)

    @staticmethod
    async def create(
        user_id: str,
        channels: List[str],
        priority: str,
        template_name: str,
        variables: Dict[str, Any],
        rendered_message: Dict[str, str],
        status: str,
        idempotency_key: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> Notification:
        """
        Creates and stores a new notification record.
        """
        notification = Notification(
            user_id=PydanticObjectId(user_id),
            channels=channels,
            priority=priority,
            template_name=template_name,
            variables=variables,
            rendered_message=rendered_message,
            status=status,
            idempotency_key=idempotency_key,
            webhook_url=webhook_url
        )
        return await notification.insert()

    @staticmethod
    async def update_status(
        notification: Notification,
        status: str,
        log_message: Optional[str] = None,
        increment_retry: bool = False
    ) -> Notification:
        """
        Updates a notification's status, appends to the delivery log,
        and manages retry counter updates.
        """
        now = datetime.now(timezone.utc)
        notification.status = status
        notification.updated_at = now
        
        if increment_retry:
            notification.retry_count += 1
            
        if log_message:
            notification.delivery_logs.append({
                "timestamp": now.isoformat(),
                "status": status,
                "message": log_message,
                "retry_count": notification.retry_count
            })
            
        return await notification.save()

    @staticmethod
    async def get_history_by_user(user_id: str) -> List[Notification]:
        """
        Retrieves the notification history for a user, sorted newest first.
        """
        try:
            p_user_id = PydanticObjectId(user_id)
            return await Notification.find(
                Notification.user_id == p_user_id
            ).sort(-Notification.created_at).to_list()
        except Exception:
            return []
