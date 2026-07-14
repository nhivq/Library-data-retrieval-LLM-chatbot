import json
import logging

from app.core.logging import JsonFormatter, bind_request_context, clear_request_context


def test_json_formatter_includes_request_and_user_context():
    clear_request_context()
    # Bind the values a real request middleware would attach, then confirm they
    # appear on any log created during that request.
    bind_request_context(request_id="req-123", user_id=42)

    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.event = "test_event"
    record.latency_ms = 12.5

    formatted = JsonFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["level"] == "INFO"
    assert payload["message"] == "hello"
    assert payload["request_id"] == "req-123"
    assert payload["user_id"] == 42
    assert payload["event"] == "test_event"
    assert payload["latency_ms"] == 12.5

    clear_request_context()


def test_json_formatter_preserves_custom_extra_fields():
    clear_request_context()

    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="loaded",
        args=(),
        exc_info=None,
    )
    record.event = "tool_schemas_loaded"
    record.tool_count = 8
    record.iteration = 2

    # Observability fields differ by code path. The formatter should keep new
    # fields automatically instead of requiring a code change for each one.
    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "tool_schemas_loaded"
    assert payload["tool_count"] == 8
    assert payload["iteration"] == 2
