import json
import hashlib
from typing import Optional, Any

import redis.asyncio as aioredis
from app.config import settings


class CacheService:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def disconnect(self):
        if self.redis:
            await self.redis.aclose()

    def _make_key(self, url: str, start: str, end: str) -> str:
        raw = f"{url}:{start}:{end}"
        return "ical:" + hashlib.md5(raw.encode()).hexdigest()

    async def get_events(self, url: str, start: str, end: str) -> Optional[Any]:
        if not self.redis:
            return None
        key = self._make_key(url, start, end)
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_events(self, url: str, start: str, end: str, events: Any):
        if not self.redis:
            return
        key = self._make_key(url, start, end)
        await self.redis.setex(key, settings.CACHE_TTL, json.dumps(events, default=str))

    async def invalidate_calendar(self, url: str):
        """Remove all cached entries for a given calendar URL."""
        if not self.redis:
            return
        pattern = "ical:*"
        async for key in self.redis.scan_iter(pattern):
            await self.redis.delete(key)


cache = CacheService()
