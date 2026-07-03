import logging
from typing import List, Optional
from app.models.template import Template
from app.schemas.template import TemplateCreate
from app.repositories.template_repository import TemplateRepository
from app.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)

class TemplateService:
    """
    Service layer for Template management.
    """
    @staticmethod
    async def create_template(data: TemplateCreate) -> Template:
        """
        Creates a new notification template. Raises ValidationException if template name is duplicate.
        """
        existing = await TemplateRepository.get_by_name(data.name)
        if existing:
            raise ValidationException(f"Template with name '{data.name}' already exists.")

        template = await TemplateRepository.create(
            name=data.name,
            subject=data.subject,
            body=data.body
        )
        logger.info(f"Created template: {data.name}")
        return template

    @staticmethod
    async def get_by_name(name: str) -> Template:
        """
        Retrieves a template by its name. Raises ValidationException if not found.
        """
        template = await TemplateRepository.get_by_name(name)
        if not template:
            raise ValidationException(f"Template with name '{name}' not found.")
        return template

    @staticmethod
    async def list_templates() -> List[Template]:
        """
        Lists all available templates.
        """
        return await TemplateRepository.list_all()
