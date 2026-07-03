import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format.
    """
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.default_keys = kwargs

    def format(self, record: logging.LogRecord) -> str:
        # Create log record payload
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func_name": record.funcName,
            "line_number": record.lineno,
        }

        # Merge additional custom fields from record extra dict if present
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            for key, val in record.extra.items():
                log_data[key] = val

        # Handle exception tracebacks if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Merge standard default keys
        for key, val in self.default_keys.items():
            log_data[key] = val

        return json.dumps(log_data)

def setup_logging(level: str = "INFO") -> None:
    """
    Sets up the logging configuration with a JSON formatter for stdout and stderr.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        logger.handlers.clear()

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Use JSON Formatter
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)

    # Set third-party logger levels to prevent log noise
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("beanie").setLevel(logging.WARNING)
    
    # Ensure all logs route through our config
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "celery"):
        sub_logger = logging.getLogger(logger_name)
        sub_logger.handlers = [handler]
        sub_logger.propagate = False
