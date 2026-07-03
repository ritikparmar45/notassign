import time
import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    """
    Exception raised when the circuit breaker is OPEN and blocking requests.
    """
    pass

class RedisCircuitBreaker:
    """
    A Redis-backed circuit breaker to manage shared state across Celery worker instances.
    States: CLOSED, OPEN, HALF-OPEN
    """
    def __init__(self, provider_name: str) -> None:
        self.name = provider_name
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self.state_key = f"circuit:{provider_name}:state"
        self.failure_key = f"circuit:{provider_name}:failures"
        self.open_until_key = f"circuit:{provider_name}:open_until"
        
        self.failure_threshold = settings.CIRCUIT_BREAKER_FAILURES_THRESHOLD
        self.recovery_time = settings.CIRCUIT_BREAKER_RECOVERY_TIME

    async def get_state(self) -> str:
        """
        Retrieves the current state. Resolves transitions from OPEN to HALF-OPEN based on TTL.
        """
        state = await self.redis.get(self.state_key)
        if not state:
            state = "CLOSED"
            await self.redis.set(self.state_key, "CLOSED")
            return state

        if state == "OPEN":
            # Check if the recovery timeout has expired
            open_until = await self.redis.get(self.open_until_key)
            if not open_until or time.time() > float(open_until):
                # Transition to HALF-OPEN
                logger.info(f"Circuit Breaker for {self.name} transitioned from OPEN to HALF-OPEN.")
                state = "HALF-OPEN"
                await self.redis.set(self.state_key, "HALF-OPEN")
                
        return state

    async def record_success(self) -> None:
        """
        Records a successful operation. Resets failure count and closes the circuit.
        """
        state = await self.get_state()
        if state in ("OPEN", "HALF-OPEN"):
            logger.info(f"Circuit Breaker for {self.name} reset to CLOSED after successful request.")
            await self.redis.set(self.state_key, "CLOSED")
            
        await self.redis.set(self.failure_key, 0)
        await self.redis.delete(self.open_until_key)

    async def record_failure(self) -> None:
        """
        Records a failure. Increments failure count. Trips to OPEN if threshold is crossed.
        """
        state = await self.get_state()
        if state == "HALF-OPEN":
            # Any failure in HALF-OPEN state trips it back to OPEN immediately
            await self.trip()
            return

        failures = await self.redis.incr(self.failure_key)
        logger.warning(f"Circuit Breaker for {self.name} failure count: {failures}/{self.failure_threshold}")
        
        if failures >= self.failure_threshold:
            await self.trip()

    async def trip(self) -> None:
        """
        Trips the circuit breaker, transitioning it to the OPEN state.
        """
        logger.error(f"Circuit Breaker for {self.name} tripped to OPEN. Cooldown active for {self.recovery_time}s.")
        await self.redis.set(self.state_key, "OPEN")
        await self.redis.set(self.open_until_key, time.time() + self.recovery_time)

    async def execute(self, func, *args, **kwargs):
        """
        Wraps and executes a function call through the circuit breaker.
        """
        state = await self.get_state()
        if state == "OPEN":
            raise CircuitBreakerOpenException(
                f"Circuit breaker for {self.name} is OPEN. Call blocked."
            )
            
        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            # Do not count CircuitBreakerOpenException itself as a failure
            if not isinstance(e, CircuitBreakerOpenException):
                await self.record_failure()
            raise e
