from celery import Celery
from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery Configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Configure Redis broker transport options for task priority support
    broker_transport_options={
        "priority_steps": list(range(10)),
        "sep": ":",
        "queue_order_strategy": "priority"
    },
    
    # Define explicitly bound priority queues
    task_queues={
        "critical": {"binding_key": "critical"},
        "high": {"binding_key": "high"},
        "normal": {"binding_key": "normal"},
        "low": {"binding_key": "low"}
    },
    
    # Default queue for routed tasks
    task_default_queue="normal",
    
    # Import the tasks file to register handlers
    imports=["app.workers.tasks"]
)
