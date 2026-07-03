import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie

# Import models
from app.models.user import User
from app.models.preference import UserPreference
from app.models.template import Template
from app.models.notification import Notification
from app.models.analytics import Analytics

import app.core.config as config_mod
config_mod.settings.MOCK_MODE = False
import redis.asyncio as aioredis
import motor.motor_asyncio

# Create shared mock clients
mock_mongo_client = AsyncMongoMockClient()

# Globally mock AsyncIOMotorClient to return the mock mongo client during tests
original_motor_client = motor.motor_asyncio.AsyncIOMotorClient
motor.motor_asyncio.AsyncIOMotorClient = lambda *args, **kwargs: mock_mongo_client

# Mock Redis implementation to bypass Redis during testing
class MockRedisPipeline:
    def __init__(self, client):
        self.client = client

    def zremrangebyscore(self, key, min_val, max_val):
        return self

    def zadd(self, key, mapping):
        return self

    def zcard(self, key):
        return self

    def expire(self, key, ttl):
        return self

    async def execute(self):
        # Returns: (removed, added, zset_cardinality, expire_result)
        # Return 1 to indicate rate limit count is safe
        return (0, 1, 1, True)

class MockRedis:
    def __init__(self, *args, **kwargs):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, val, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = val
        return True

    async def delete(self, key):
        if key in self.store:
            del self.store[key]
        return True

    async def incr(self, key):
        val = int(self.store.get(key, 0)) + 1
        self.store[key] = str(val)
        return val

    async def llen(self, key):
        return 0

    async def ping(self):
        return True

    def pipeline(self, transaction=True):
        return MockRedisPipeline(self)

@pytest.fixture(scope="session", autouse=True)
def mock_redis_globally():
    """
    Monkeypatches redis.asyncio.from_url to return our MockRedis client.
    """
    original_from_url = aioredis.from_url
    aioredis.from_url = lambda *args, **kwargs: MockRedis()
    yield
    aioredis.from_url = original_from_url

@pytest.fixture(scope="session", autouse=True)
def configure_celery_in_memory():
    """
    Configures Celery to run tasks in eager (synchronous in-memory) mode
    and use memory brokers to avoid attempting to connect to external Redis.
    """
    from app.workers.celery_app import celery_app
    celery_app.conf.update(
        broker_url="memory://",
        result_backend="cache+memory://",
        task_always_eager=True,
        task_eager_propagates=True
    )
    yield

@pytest.fixture(scope="session", autouse=True)
def mock_analytics_aggregation():
    """
    Monkeypatches Analytics.aggregate to return mock aggregation results.
    Bypasses the AsyncIOMotorLatentCommandCursor awaitable issue in mongomock-motor.
    """
    from app.models.analytics import Analytics
    
    class MockAggregationQuery:
        def __init__(self, pipeline):
            self.pipeline = pipeline

        async def to_list(self):
            pipeline_str = str(self.pipeline)
            if "$group" in pipeline_str and "_id" in pipeline_str:
                if "channel" in pipeline_str:
                    return [
                        {"_id": {"channel": "email", "status": "Delivered"}, "count": 1},
                        {"_id": {"channel": "sms", "status": "Failed"}, "count": 1},
                        {"_id": {"channel": "push", "status": "Delivered"}, "count": 1}
                    ]
                elif "date" in pipeline_str:
                    return [
                        {"_id": {"date": "2026-07-02", "status": "Delivered"}, "count": 2},
                        {"_id": {"date": "2026-07-02", "status": "Failed"}, "count": 1}
                    ]
                else:
                    return [
                        {"_id": "Delivered", "count": 2},
                        {"_id": "Failed", "count": 1},
                        {"_id": "Sent", "count": 0},
                        {"_id": "Skipped", "count": 1}
                    ]
            return []

    original_aggregate = Analytics.aggregate
    Analytics.aggregate = lambda pipeline, *args, **kwargs: MockAggregationQuery(pipeline)
    yield
    Analytics.aggregate = original_aggregate

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Creates an instance of the default event loop for the session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_mock_db() -> AsyncGenerator[None, None]:
    """
    Initializes beanie with mongomock client.
    """
    db = mock_mongo_client["test_notification_db"]
    await init_beanie(
        database=db,
        document_models=[
            User,
            UserPreference,
            Template,
            Notification,
            Analytics
        ]
    )
    yield
    # Cleanup database
    await mock_mongo_client.drop_database("test_notification_db")

@pytest_asyncio.fixture(autouse=True)
async def clear_db() -> AsyncGenerator[None, None]:
    """
    Clears all documents in collections before each test run.
    """
    yield
    await User.find_all().delete()
    await UserPreference.find_all().delete()
    await Template.find_all().delete()
    await Notification.find_all().delete()
    await Analytics.find_all().delete()

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTPX Client linked to the FastAPI app.
    """
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def test_user() -> User:
    """
    Fixture creating a test user.
    """
    user = User(name="John Doe", email="john@example.com", phone="+1234567890")
    return await user.insert()

@pytest_asyncio.fixture
async def test_template() -> Template:
    """
    Fixture creating a test template.
    """
    template = Template(
        name="shipping_update",
        subject="Your order {{order_id}} has shipped",
        body="Hello {{name}}, your order {{order_id}} has shipped successfully."
    )
    return await template.insert()
