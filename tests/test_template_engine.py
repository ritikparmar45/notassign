import pytest
from app.utils.template_engine import TemplateEngine
from app.utils.exceptions import TemplateException

def test_template_rendering_success():
    """
    Verifies rendering replaces all placeholders successfully.
    """
    template_str = "Hello {{name}}, your order {{order_id}} has shipped!"
    variables = {"name": "Ritik", "order_id": "ORD1001"}
    
    result = TemplateEngine.render(template_str, variables)
    assert result == "Hello Ritik, your order ORD1001 has shipped!"

def test_template_rendering_missing_variables():
    """
    Verifies rendering raises TemplateException listing missing variables.
    """
    template_str = "Hello {{name}}, your order {{order_id}} has shipped to {{address}}!"
    variables = {"name": "Ritik"}
    
    with pytest.raises(TemplateException) as exc_info:
        TemplateEngine.render(template_str, variables)
        
    assert "Missing template variables" in str(exc_info.value)
    # Order-independent sets for assertions
    assert set(exc_info.value.missing_variables) == {"order_id", "address"}

def test_template_rendering_extra_variables():
    """
    Verifies template engine ignores extra variables.
    """
    template_str = "Hello {{name}}!"
    variables = {"name": "Ritik", "age": 25, "city": "Delhi"}
    
    result = TemplateEngine.render(template_str, variables)
    assert result == "Hello Ritik!"
