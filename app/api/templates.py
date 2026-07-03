from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import verify_api_key
from app.schemas.template import TemplateCreate, TemplateResponse
from app.services.template_service import TemplateService
from app.utils.exceptions import ValidationException

router = APIRouter(
    prefix="/templates",
    tags=["Templates"],
    dependencies=[Depends(verify_api_key)]
)

@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(data: TemplateCreate) -> TemplateResponse:
    """
    Creates a new notification template.
    """
    try:
        template = await TemplateService.create_template(data)
        return TemplateResponse(
            id=str(template.id),
            name=template.name,
            subject=template.subject,
            body=template.body,
            created_at=template.created_at
        )
    except ValidationException as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ve.message
        )

@router.get("", response_model=List[TemplateResponse])
async def list_templates() -> List[TemplateResponse]:
    """
    Lists all configured notification templates.
    """
    templates = await TemplateService.list_templates()
    return [
        TemplateResponse(
            id=str(t.id),
            name=t.name,
            subject=t.subject,
            body=t.body,
            created_at=t.created_at
        ) for t in templates
    ]
