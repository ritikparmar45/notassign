import re
from typing import Dict, Any
from app.utils.exceptions import TemplateException

class TemplateEngine:
    """
    Utility class for parsing and rendering template bodies.
    """
    @staticmethod
    def render(template_str: str, variables: Dict[str, Any]) -> str:
        """
        Replaces placeholders formatted as {{variable_name}} with values from the variables dict.
        Raises TemplateException if any variables are missing.
        """
        # Find all placeholders in the template (e.g. {{name}} or {{ name }})
        placeholders = set(re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", template_str))
        
        # Determine missing variables
        missing = [p for p in placeholders if p not in variables]
        if missing:
            raise TemplateException(
                message=f"Missing template variables: {', '.join(missing)}",
                missing_variables=missing
            )
            
        rendered = template_str
        for key, val in variables.items():
            # Replace placeholder occurrences
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            rendered = re.sub(pattern, str(val), rendered)
            
        return rendered
