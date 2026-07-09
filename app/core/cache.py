import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

from app.core.config import CACHE_ENABLED, REDIS_URL


try:
    from redis import Redis

except Exception:
    Redis = None


_redis_client = None


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
        return None

    try:
        value = client.get(key)

    except Exception:
        return None

    if value is None:
        return None

    try:
        return json.loads(value)

    except json.JSONDecodeError:
        return None


def set_json(
        key: str,
        value,
        ttl_seconds: int
):
    """Store JSON data in Redis and ignore cache write failures."""

    client = get_redis_client()

    if client is None:
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

    except Exception:
        return
