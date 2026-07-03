from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field
from pymongo import IndexModel, ASCENDING

class Template(Document):
    name: str = Field(..., description="Unique template identifier (e.g., order_shipped)")
    subject: Optional[str] = Field(default=None, description="Subject line for email notifications")
    body: str = Field(..., description="Message template content, e.g. 'Hello {{name}}'")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "templates"
        indexes = [
            IndexModel([("name", ASCENDING)], unique=True),
            "created_at"
        ]
