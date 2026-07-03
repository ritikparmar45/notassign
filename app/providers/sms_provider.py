import random
import logging
from app.core.config import settings
from app.utils.circuit_breaker import RedisCircuitBreaker
from app.utils.exceptions import NotificationException

logger = logging.getLogger(__name__)

class SMSProvider:
    """
    Mock SMS Provider with circuit breaker protection and simulated failure rate.
    """
    def __init__(self) -> None:
        self.breaker = RedisCircuitBreaker("sms")

    async def send(self, to_phone: str, body: str) -> str:
        """
        Sends an SMS notification via mock logic wrapped in the circuit breaker.
        """
        async def _mock_send():
            if random.random() < settings.PROVIDER_FAIL_RATE:
                logger.warning(f"Simulating random SMS delivery failure to {to_phone}")
                raise NotificationException("Failed to transmit SMS via SMS Gateway.")
            
            logger.info(f"Successfully sent mock SMS to {to_phone}: {body[:30]}...")
            return f"sms_msg_id_{random.randint(100000, 999999)}"

        return await self.breaker.execute(_mock_send)
