from app.utils.priority_queue import PriorityQueueUtil
from app.models.notification import NotificationPriority

def test_priority_queue_names():
    """
    Verifies priority strings map to correct Celery queue names.
    """
    assert PriorityQueueUtil.get_queue_name(NotificationPriority.CRITICAL) == "critical"
    assert PriorityQueueUtil.get_queue_name(NotificationPriority.HIGH) == "high"
    assert PriorityQueueUtil.get_queue_name(NotificationPriority.NORMAL) == "normal"
    assert PriorityQueueUtil.get_queue_name(NotificationPriority.LOW) == "low"
    # Case insensitivity checks
    assert PriorityQueueUtil.get_queue_name("critical ") == "critical"
    assert PriorityQueueUtil.get_queue_name("HIGH") == "high"

def test_priority_celery_integers():
    """
    Verifies priority strings map to correct Celery task priority integers.
    """
    assert PriorityQueueUtil.get_celery_priority(NotificationPriority.CRITICAL) == 0
    assert PriorityQueueUtil.get_celery_priority(NotificationPriority.HIGH) == 3
    assert PriorityQueueUtil.get_celery_priority(NotificationPriority.NORMAL) == 6
    assert PriorityQueueUtil.get_celery_priority(NotificationPriority.LOW) == 9
    assert PriorityQueueUtil.get_celery_priority("NORMAL") == 6
