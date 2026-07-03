from datetime import datetime, timezone
from beanie import Document, PydanticObjectId
from pydantic import Field

class UserPreference(Document):
    user_id: PydanticObjectId = Field(..., description="Reference to the User ID")
    email_enabled: bool = Field(default=True, description="True if user permits email notifications")
    sms_enabled: bool = Field(default=True, description="True if user permits SMS notifications")
    push_enabled: bool = Field(default=True, description="True if user permits Push notifications")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "user_preferences"
        indexes = [
            "user_id"
        ]
        # We can make user_id unique in preferences to avoid duplicates
        # user_id is the primary lookup.
