from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TemplateCreate(BaseModel):
    name: str = Field(..., description="Unique template identifier name")
    subject: Optional[str] = Field(default=None, description="Optional subject line (usually for emails)")
    body: str = Field(..., description="Template body content with variables like {{name}}")

class TemplateResponse(BaseModel):
    id: str = Field(..., description="Template database ID")
    name: str
    subject: Optional[str]
    body: str
    created_at: datetime
