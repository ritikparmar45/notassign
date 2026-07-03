import logging
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import verify_api_key
from app.core.config import settings
from app.services.analytics_service import AnalyticsService
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Analytics & Monitoring"]
)

@router.get("/analytics", dependencies=[Depends(verify_api_key)])
async def get_analytics():
    """
    [Bonus Feature] Compiles complete statistics for notification channels
    including totals, success rates, and daily trends.
    """
    try:
        return await AnalyticsService.get_statistics()
    except Exception as e:
        logger.error(f"Error gathering analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not compile analytics reports."
        )

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    [Bonus Feature] Endpoint verifying database and message broker health status.
    Returns 200 OK if healthy, otherwise 503 Service Unavailable.
    """
    health_status = {
        "status": "healthy",
        "mongodb": "unknown",
        "redis": "unknown"
    }
    
    # 1. Check MongoDB Connection
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
        await client.admin.command('ping')
        health_status["mongodb"] = "healthy"
    except Exception as e:
        logger.error(f"Health check failed for MongoDB: {e}")
        health_status["mongodb"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # 2. Check Redis Connection
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Health check failed for Redis: {e}")
        health_status["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
        
    return health_status

@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics():
    """
    [Bonus Feature] Exposes basic monitoring metrics (e.g. queue state, provider health status).
    """
    # Create simple metrics payload
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        # Check Celery queue size
        queue_lengths = {}
        for queue in ["critical", "high", "normal", "low"]:
            # Celery uses list length in Redis
            length = await r.llen(queue)
            queue_lengths[queue] = length

        # Get circuit breaker states from Redis
        circuit_states = {}
        for provider in ["email", "sms", "push"]:
            state = await r.get(f"circuit:{provider}:state")
            circuit_states[provider] = state if state else "CLOSED"

        return {
            "celery_queues_size": queue_lengths,
            "circuit_breaker_states": circuit_states
        }
    except Exception as e:
        logger.error(f"Error gathering metrics: {e}")
        return {"error": "Failed to query system metrics"}
