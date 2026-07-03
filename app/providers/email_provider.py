import random
import logging
from app.core.config import settings
from app.utils.circuit_breaker import RedisCircuitBreaker
from app.utils.exceptions import NotificationException

logger = logging.getLogger(__name__)

class EmailProvider:
    """
    Mock Email Provider with circuit breaker protection and simulated failure rate.
    """
    def __init__(self) -> None:
        self.breaker = RedisCircuitBreaker("email")

    async def send(self, to_email: str, subject: str, body: str) -> str:
        """
        Sends an email notification via mock logic wrapped in the circuit breaker.
        """
        async def _mock_send():
            # Simulate a 20% chance of failure
            if random.random() < settings.PROVIDER_FAIL_RATE:
                logger.warning(f"Simulating random Email delivery failure to {to_email}")
                raise NotificationException("Failed to connect to SMTP server.")
            
            logger.info(f"Successfully sent mock Email to {to_email} (Subject: {subject})")
            return f"email_msg_id_{random.randint(100000, 999999)}"

        return await self.breaker.execute(_mock_send)
