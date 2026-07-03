import json
import logging
import redis.asyncio as aioredis
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.models.notification import Notification

logger = logging.getLogger(__name__)

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to prevent duplicate request processing using an Idempotency-Key header.
    """
    def __init__(self, app) -> None:
        super().__init__(app)
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check idempotency only for POST notification requests
        path = request.url.path
        is_post = request.method == "POST"
        is_notification_endpoint = "/notifications" in path
        
        idempotency_key = request.headers.get("idempotency-key")
        
        if not (is_post and is_notification_endpoint and idempotency_key):
            return await call_next(request)
            
        logger.info(f"Checking idempotency for key: {idempotency_key}")
        
        # 1. Check MongoDB for existing completed notification
        try:
            existing = await Notification.find_one(Notification.idempotency_key == idempotency_key)
            if existing:
                logger.info(f"Idempotent request matched existing notification: {existing.id}")
                # Return the existing notification
                content = {
                    "id": str(existing.id),
                    "user_id": str(existing.user_id),
                    "channels": existing.channels,
                    "priority": existing.priority,
                    "template_name": existing.template_name,
                    "variables": existing.variables,
                    "rendered_message": existing.rendered_message,
                    "status": existing.status,
                    "retry_count": existing.retry_count,
                    "idempotency_key": existing.idempotency_key,
                    "delivery_logs": existing.delivery_logs,
                    "webhook_url": existing.webhook_url,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                    "updated_at": existing.updated_at.isoformat() if existing.updated_at else None,
                }
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=content,
                    headers={"X-Cache-Idempotency": "true"}
                )
        except Exception as e:
            logger.error(f"Error querying database for idempotency: {e}", exc_info=True)

        # 2. Prevent concurrent identical requests using Redis lock
        redis_lock_key = f"idempotency_lock:{idempotency_key}"
        # Set lock with TTL of 10 seconds to cover processing time
        locked = await self.redis.set(redis_lock_key, "processing", ex=10, nx=True)
        
        if not locked:
            logger.warning(f"Concurrent request detected for idempotency key: {idempotency_key}")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "Request with this idempotency key is already in progress."}
            )
            
        try:
            # Continue request processing
            response = await call_next(request)
            
            # If request resulted in a client error or server error, delete lock
            # so they can correct/retry the request
            if response.status_code >= 400:
                await self.redis.delete(redis_lock_key)
                
            return response
            
        except Exception as e:
            # On exception, clear the Redis lock
            await self.redis.delete(redis_lock_key)
            logger.error(f"Request exception with idempotency key: {idempotency_key}", exc_info=True)
            raise e
