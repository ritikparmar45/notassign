class NotificationException(Exception):
    """
    Exception raised for errors in notification processing or delivery.
    """
    def __init__(self, message: str, details: str = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

class TemplateException(Exception):
    """
    Exception raised for errors in template parsing or rendering.
    """
    def __init__(self, message: str, missing_variables: list[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.missing_variables = missing_variables or []

class PreferenceException(Exception):
    """
    Exception raised for preference conflicts or verification errors.
    """
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

class ValidationException(Exception):
    """
    Exception raised for validation failures (e.g. user/template existence, invalid values).
    """
    def __init__(self, message: str, errors: dict = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or {}
