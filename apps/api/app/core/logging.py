import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.config import LogLevel

STANDARD_LOG_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field_name, field_value in record.__dict__.items():
            if field_name not in STANDARD_LOG_FIELDS and field_value is not None:
                log_payload[field_name] = field_value
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload)


def configure_logging(log_level: LogLevel) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonLogFormatter())

    root_logger.addHandler(stream_handler)
    root_logger.setLevel(log_level.value)
