import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal

from app.core.config import CACHE_DEBUG, CACHE_ENABLED, REDIS_URL


try:
    from redis import Redis

except Exception:
    Redis = None


_redis_client = None
logger = logging.getLogger(__name__)


def _debug_cache_event(
        event: str,
        key: str | None = None,
        error: Exception | None = None
):
    """Emit opt-in cache diagnostics without noisy production logs."""

    if not CACHE_DEBUG:
        return

    if error is not None:
        logger.debug(
            "cache.%s key=%s error=%s",
            event,
            key,
            error
        )
        return

    logger.debug(
        "cache.%s key=%s",
        event,
        key
    )


def _json_default(value):
    """Serialize common database values before storing them in Redis."""

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return str(value)


def get_redis_client():
    """Return a lazily-created Redis client when caching is configured."""

    global _redis_client

    if not CACHE_ENABLED or not REDIS_URL or Redis is None:
        return None

    if _redis_client is None:
        _redis_client = Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2
        )

    return _redis_client


def make_cache_key(
        prefix: str,
        payload: dict
) -> str:
    """Build a stable cache key without storing long user input in the key."""

    raw_payload = json.dumps(
        payload,
        sort_keys=True,
        default=_json_default
    )

    digest = hashlib.sha256(
        raw_payload.encode("utf-8")
    ).hexdigest()

    return f"{prefix}:{digest}"


def get_json(key: str):
    """Read JSON data from Redis, returning None on misses or cache errors."""

    client = get_redis_client()

    if client is None:
        _debug_cache_event(
            "disabled",
            key
        )
        return None

    try:
        value = client.get(key)

    except Exception as e:
        _debug_cache_event(
            "read_error",
            key,
            e
        )
        return None

    if value is None:
        _debug_cache_event(
            "miss",
            key
        )
        return None

    try:
        parsed_value = json.loads(value)

    except json.JSONDecodeError as e:
        _debug_cache_event(
            "decode_error",
            key,
            e
        )
        return None

    _debug_cache_event(
        "hit",
        key
    )

    return parsed_value


def set_json(
        key: str,
        value,
        ttl_seconds: int
):
    """Store JSON data in Redis and ignore cache write failures."""

    client = get_redis_client()

    if client is None:
        _debug_cache_event(
            "disabled",
            key
        )
        return

    try:
        client.setex(
            key,
            ttl_seconds,
            json.dumps(
                value,
                default=_json_default
            )
        )

    except Exception as e:
        _debug_cache_event(
            "write_error",
            key,
            e
        )
        return

    _debug_cache_event(
        "write",
        key
    )
