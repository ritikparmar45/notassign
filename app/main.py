import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from app.core.config import settings

# Global overrides for MOCK_MODE (runs completely in-memory without external Redis or MongoDB)
if settings.MOCK_MODE:
    import redis.asyncio as aioredis
    import motor.motor_asyncio
    from mongomock_motor import AsyncMongoMockClient
    from app.utils.mock_redis import MockRedis
    from app.workers.celery_app import celery_app
    
    # Patch Redis connections globally
    aioredis.from_url = lambda *args, **kwargs: MockRedis()
    
    # Patch Motor MongoDB clients globally
    motor.motor_asyncio.AsyncIOMotorClient = lambda *args, **kwargs: AsyncMongoMockClient()
    
    # Intercept Celery send_task to execute tasks synchronously in-process
    def mock_send_task(name, args=None, kwargs=None, **opts):
        logging.getLogger(__name__).warning(f"[MOCK MODE] Intercepted Celery task dispatch for '{name}'")
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            running = True
        except RuntimeError:
            running = False

        if name == "app.workers.tasks.send_notification_task":
            notification_id = args[0]
            if running:
                from app.workers.tasks import async_execute_task
                loop.create_task(async_execute_task(None, notification_id))
            else:
                from app.workers.tasks import send_notification_task
                send_notification_task.apply(args=args, kwargs=kwargs)
        elif name == "app.workers.tasks.dispatch_webhook_task":
            url, payload = args[0], args[1]
            if running:
                from app.workers.tasks import async_execute_webhook
                loop.create_task(async_execute_webhook(None, url, payload))
            else:
                from app.workers.tasks import dispatch_webhook_task
                dispatch_webhook_task.apply(args=args, kwargs=kwargs)
            
    celery_app.send_task = mock_send_task

    # Patch Analytics.aggregate globally to bypass mongomock awaitable cursor bug in MOCK_MODE
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

    Analytics.aggregate = lambda pipeline, *args, **kwargs: MockAggregationQuery(pipeline)


from app.core.logging import setup_logging
from app.core.security import verify_api_key
from app.database.mongodb import init_db
from app.middleware.idempotency import IdempotencyMiddleware
from app.repositories.user_repository import UserRepository

# Setup logging configuration
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up Notification Service application...")
    await init_db()
    yield
    # Shutdown actions
    logger.info("Shutting down Notification Service application...")

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Asynchronous multi-channel notification backend microservice.",
    lifespan=lifespan
)

# Set CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"]
)

# Register custom Idempotency Middleware
app.add_middleware(IdempotencyMiddleware)

# Import routers
from app.api.notifications import router as notifications_router
from app.api.preferences import router as preferences_router
from app.api.templates import router as templates_router
from app.api.analytics import router as analytics_router

# Include routers
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(preferences_router, prefix=settings.API_V1_STR)
app.include_router(templates_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)

# Schema for user seeding
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str

@app.post(f"{settings.API_V1_STR}/users", status_code=status.HTTP_201_CREATED, tags=["Users"], dependencies=[Depends(verify_api_key)])
async def create_user(user: UserCreate):
    """
    Utility endpoint to register a new user in the database.
    Useful for testing notification delivery parameters.
    """
    db_user = await UserRepository.create(
        name=user.name,
        email=user.email,
        phone=user.phone
    )
    return {
        "id": str(db_user.id),
        "name": db_user.name,
        "email": db_user.email,
        "phone": db_user.phone,
        "created_at": db_user.created_at
    }

@app.get("/", include_in_schema=False)
async def docs_redirect():
    """
    Redirects root requests directly to Swagger OpenAPI UI.
    """
    return RedirectResponse(url="/docs")
