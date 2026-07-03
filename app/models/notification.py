from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel, ASCENDING

class NotificationStatus:
    PENDING = "Pending"
    QUEUED = "Queued"
    PROCESSING = "Processing"
    SENT = "Sent"
    DELIVERED = "Delivered"
    FAILED = "Failed"
    RETRYING = "Retrying"
    SKIPPED = "Skipped"

class NotificationPriority:
    CRITICAL = "Critical"
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"

class Notification(Document):
    user_id: PydanticObjectId = Field(..., description="Recipient user's ID")
    channels: List[str] = Field(..., description="List of communication channels to use (email, sms, push)")
    priority: str = Field(default=NotificationPriority.NORMAL, description="Priority level (Critical, High, Normal, Low)")
    template_name: str = Field(..., description="Name of template used")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables passed to render the template")
    rendered_message: Dict[str, str] = Field(default_factory=dict, description="Rendered template message per channel")
    status: str = Field(default=NotificationStatus.PENDING, description="Delivery status of the notification")
    retry_count: int = Field(default=0, description="Number of times sending has been retried")
    idempotency_key: Optional[str] = Field(default=None, description="Unique key to prevent duplicate delivery requests")
    delivery_logs: List[Dict[str, Any]] = Field(default_factory=list, description="Array of log history for delivery attempts")
    webhook_url: Optional[str] = Field(default=None, description="Optional webhook URL to receive status updates")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notifications"
        indexes = [
            "user_id",
            "status",
            "priority",
            "created_at",
            # Sparse unique index for idempotency keys to allow multiple null values
            IndexModel([("idempotency_key", ASCENDING)], unique=True, sparse=True)
        ]
