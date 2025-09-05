import hashlib
import json
from typing import Any, Optional, Dict
import diskcache as dc
from pathlib import Path
import logging

from core.config import CACHE_TTL_HOURS

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".proffinder_cache"
CACHE_DIR.mkdir(exist_ok=True)

cache = dc.Cache(str(CACHE_DIR), size_limit=1024**3)  # 1GB limit


def make_cache_key(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Create a cache key from URL and parameters."""
    key_data = {"url": url}
    if params:
        key_data["params"] = sorted(params.items())
    
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cached(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """Get cached response."""
    try:
        key = make_cache_key(url, params)
        return cache.get(key)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


def set_cache(url: str, data: Any, params: Optional[Dict[str, Any]] = None, 
              ttl_hours: int = CACHE_TTL_HOURS) -> None:
    """Set cached response."""
    try:
        key = make_cache_key(url, params)
        cache.set(key, data, expire=ttl_hours * 3600)
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


def clear_cache() -> None:
    """Clear all cached data."""
    try:
        cache.clear()
        logger.info("Cache cleared")
    except Exception as e:
        logger.warning(f"Cache clear error: {e}")


async def cached_get_json(client, url: str, params: Optional[Dict[str, Any]] = None, 
                         headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Get JSON with caching."""
    cached_result = get_cached(url, params)
    if cached_result is not None:
        logger.debug(f"Cache hit for {url}")
        return cached_result
    
    logger.debug(f"Cache miss for {url}")
    result = await client.get_json(url, params, headers)
    if result is not None:
        set_cache(url, result, params)
    
    return result


async def cached_get_text(client, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Get text with caching."""
    cached_result = get_cached(url)
    if cached_result is not None:
        logger.debug(f"Cache hit for {url}")
        return cached_result
    
    logger.debug(f"Cache miss for {url}")
    result = await client.get_text(url, headers)
    if result is not None:
        set_cache(url, result)
    
    return result