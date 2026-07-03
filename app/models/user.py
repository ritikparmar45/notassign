from datetime import datetime, timezone
from beanie import Document
from pydantic import Field, EmailStr

class User(Document):
    name: str = Field(..., description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    phone: str = Field(..., description="User's phone number in international format (e.g. +1234567890)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [
            "email",
            "created_at"
        ]
