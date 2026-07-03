from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class UserPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = Field(default=None, description="Enable/disable email channel")
    sms_enabled: Optional[bool] = Field(default=None, description="Enable/disable SMS channel")
    push_enabled: Optional[bool] = Field(default=None, description="Enable/disable Push channel")

class UserPreferenceResponse(BaseModel):
    user_id: str = Field(..., description="The user identifier")
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    updated_at: datetime
