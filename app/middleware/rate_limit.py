import time
import logging
import redis.asyncio as aioredis
from fastapi import HTTPException, status, Request
from app.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Sliding window rate limiter using Redis sorted sets.
    """
    def __init__(self) -> None:
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def is_rate_limited(self, user_id: str) -> bool:
        """
        Checks if a user has exceeded the rate limit (100 requests per hour).
        """
        # Build key specific to the user
        key = f"rate_limit:{user_id}"
        now = time.time()
        window_start = now - settings.RATE_LIMIT_WINDOW

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                # Remove requests older than the sliding window boundary
                pipe.zremrangebyscore(key, 0, window_start)
                # Record this request with timestamp as member and score
                member = f"{now}-{user_id}"
                pipe.zadd(key, {member: now})
                # Count total entries in the set for the window
                pipe.zcard(key)
                # Refresh key expiration
                pipe.expire(key, settings.RATE_LIMIT_WINDOW)
                
                _, _, count, _ = await pipe.execute()
                
            logger.info(f"Rate limit check for user {user_id}: {count}/{settings.RATE_LIMIT_LIMIT}")
            return count > settings.RATE_LIMIT_LIMIT
        except Exception as e:
            logger.error(f"Redis rate limiter exception: {e}", exc_info=True)
            # Fail-open or fail-closed? For notification service, we fail-open so notifications still go through if Redis is down
            return False

# Dependency instance
rate_limiter = RateLimiter()

async def check_rate_limit(user_id: str) -> None:
    """
    FastAPI dependency to verify notification dispatch rate limits.
    Raises 429 Too Many Requests if rate limit is exceeded.
    """
    if await rate_limiter.is_rate_limited(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_LIMIT} notifications per user per hour."
        )
