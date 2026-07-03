from datetime import datetime, timezone
from beanie import Document
from pydantic import Field

class Analytics(Document):
    channel: str = Field(..., description="Channel name, e.g. email, sms, push")
    status: str = Field(..., description="Delivery status, e.g. Sent, Delivered, Failed, Skipped")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "analytics"
        indexes = [
            "channel",
            "status",
            "timestamp"
        ]
