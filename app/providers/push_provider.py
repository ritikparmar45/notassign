import random
import logging
from app.core.config import settings
from app.utils.circuit_breaker import RedisCircuitBreaker
from app.utils.exceptions import NotificationException

logger = logging.getLogger(__name__)

class PushProvider:
    """
    Mock Push Notification Provider with circuit breaker protection and simulated failure rate.
    """
    def __init__(self) -> None:
        self.breaker = RedisCircuitBreaker("push")

    async def send(self, user_id: str, body: str) -> str:
        """
        Sends a Push notification via mock logic wrapped in the circuit breaker.
        """
        async def _mock_send():
            if random.random() < settings.PROVIDER_FAIL_RATE:
                logger.warning(f"Simulating random Push notification failure for user {user_id}")
                raise NotificationException("Failed to reach Apple APNS / Google FCM service.")
            
            logger.info(f"Successfully sent mock Push to user {user_id}: {body[:30]}...")
            return f"push_msg_id_{random.randint(100000, 999999)}"

        return await self.breaker.execute(_mock_send)
