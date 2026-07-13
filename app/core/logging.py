import json
import logging
import os
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

_request_context: ContextVar[dict] = ContextVar("request_context", default={})

# Python's LogRecord contains many built-in fields such as pathname, process,
# and thread. We exclude those so our JSON logs stay focused on fields that help
# people understand what happened in the app.
_RESERVED_LOG_RECORD_ATTRIBUTES = {
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
}


class ContextFilter(logging.Filter):
    """Attach request-scoped context values to every log record."""

    def filter(self, record):
        # ContextVar stores values for the current request only. This lets logs
        # from different users/requests keep their own request_id and user_id
        # even when the server handles many requests at the same time.
        context = _request_context.get()
        for key, value in context.items():
            setattr(record, key, value)
        if not hasattr(record, "request_id"):
            setattr(record, "request_id", context.get("request_id", "local"))
        if not hasattr(record, "user_id"):
            setattr(record, "user_id", context.get("user_id"))
        return True


class JsonFormatter(logging.Formatter):
    """Render log entries as JSON with request-scoped metadata."""

    def format(self, record):
        context = _request_context.get()
        for key, value in context.items():
            setattr(record, key, value)

        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Keep all custom logger.extra fields. This is important for
        # observability because each code path may add its own useful facts,
        # such as tool_count, iteration, message_count, or response_chars.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRIBUTES:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def bind_request_context(**kwargs):
    """Merge values into the current request-scoped logging context."""

    context = dict(_request_context.get())
    for key, value in kwargs.items():
        if value is not None:
            context[key] = value
    _request_context.set(context)
    return context


def clear_request_context():
    """Clear the request-scoped logging context."""

    _request_context.set({})


def setup_logging():
    """Configure the root logger for structured JSON output."""

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Test runners and production servers often install handlers before the app
    # starts. Reuse them so we do not duplicate log lines; just make their
    # output structured and request-aware.
    if root_logger.handlers:
        for handler in root_logger.handlers:
            if not isinstance(handler.formatter, JsonFormatter):
                handler.setFormatter(JsonFormatter())
            if not any(isinstance(filter_obj, ContextFilter) for filter_obj in handler.filters):
                handler.addFilter(ContextFilter())
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())
    root_logger.addHandler(handler)


def make_request_id() -> str:
    return str(uuid.uuid4())
