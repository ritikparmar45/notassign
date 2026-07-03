from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl
from app.models.notification import NotificationPriority, NotificationStatus

class NotificationCreate(BaseModel):
    user_id: str = Field(..., description="Recipient user's MongoDB ObjectId string")
    channels: List[str] = Field(..., description="List of channels: email, sms, push")
    priority: str = Field(default=NotificationPriority.NORMAL, description="Priority level: Critical, High, Normal, Low")
    template_name: str = Field(..., description="Name of template to use")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables for template rendering")
    webhook_url: Optional[str] = Field(default=None, description="Optional callback URL for status changes")

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one channel must be specified.")
        valid_channels = {"email", "sms", "push"}
        invalid = [c for c in v if c not in valid_channels]
        if invalid:
            raise ValueError(f"Invalid channel(s): {', '.join(invalid)}. Supported: email, sms, push.")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid_priorities = {
            NotificationPriority.CRITICAL,
            NotificationPriority.HIGH,
            NotificationPriority.NORMAL,
            NotificationPriority.LOW,
        }
        if v not in valid_priorities:
            raise ValueError(
                f"Invalid priority: {v}. Supported: {', '.join(valid_priorities)}."
            )
        return v

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("Webhook URL must start with http:// or https://")
        return v

class BatchNotificationCreate(BaseModel):
    notifications: List[NotificationCreate] = Field(..., min_items=1, description="List of notification creation objects")

class NotificationResponse(BaseModel):
    id: str = Field(..., description="Notification database ID")
    user_id: str = Field(..., description="Recipient User's ID")
    channels: List[str]
    priority: str
    template_name: str
    variables: Dict[str, Any]
    rendered_message: Dict[str, str]
    status: str
    retry_count: int
    idempotency_key: Optional[str]
    delivery_logs: List[Dict[str, Any]]
    webhook_url: Optional[str]
    created_at: datetime
    updated_at: datetime
