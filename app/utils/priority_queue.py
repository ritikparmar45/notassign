from app.models.notification import NotificationPriority

class PriorityQueueUtil:
    """
    Utility for mapping internal notification priorities to Celery queues and Redis priorities.
    """
    @staticmethod
    def get_queue_name(priority: str) -> str:
        """
        Maps internal priority names to Celery queue names.
        """
        p = priority.strip().capitalize()
        if p == NotificationPriority.CRITICAL:
            return "critical"
        elif p == NotificationPriority.HIGH:
            return "high"
        elif p == NotificationPriority.LOW:
            return "low"
        else:
            return "normal"

    @staticmethod
    def get_celery_priority(priority: str) -> int:
        """
        Maps internal priority names to Celery task priority integers (0-9).
        In Celery with Redis broker, lower number means higher priority.
        - Critical: 0 (Highest)
        - High: 3
        - Normal: 6
        - Low: 9 (Lowest)
        """
        p = priority.strip().capitalize()
        if p == NotificationPriority.CRITICAL:
            return 0
        elif p == NotificationPriority.HIGH:
            return 3
        elif p == NotificationPriority.LOW:
            return 9
        else:
            return 6
