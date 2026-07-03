from typing import Optional, List
from app.models.template import Template

class TemplateRepository:
    """
    Repository class handling operations on the Templates collection.
    """
    @staticmethod
    async def get_by_name(name: str) -> Optional[Template]:
        """
        Retrieves a template by its unique name (e.g. 'welcome_email').
        """
        return await Template.find_one(Template.name == name)

    @staticmethod
    async def create(name: str, subject: Optional[str], body: str) -> Template:
        """
        Creates and saves a new template.
        """
        template = Template(name=name, subject=subject, body=body)
        return await template.insert()

    @staticmethod
    async def list_all() -> List[Template]:
        """
        Lists all templates.
        """
        return await Template.find_all().to_list()
