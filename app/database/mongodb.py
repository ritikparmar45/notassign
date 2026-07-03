import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings

logger = logging.getLogger(__name__)

async def init_db() -> None:
    """
    Initializes Beanie ODM and sets up connection to MongoDB.
    """
    logger.info("Initializing MongoDB connection with Beanie...")
    
    # Import models inside the function to avoid circular dependency issues
    from app.models.user import User
    from app.models.preference import UserPreference
    from app.models.template import Template
    from app.models.notification import Notification
    from app.models.analytics import Analytics
    
    try:
        if settings.MOCK_MODE:
            logger.warning("MOCK_MODE is enabled. Initializing in-memory MongoDB via mongomock...")
            from mongomock_motor import AsyncMongoMockClient
            client = AsyncMongoMockClient()
            db = client[settings.DATABASE_NAME]
        else:
            client = AsyncIOMotorClient(settings.MONGODB_URL)
            # Check connection is valid
            await client.admin.command('ping')
            db = client[settings.DATABASE_NAME]
        
        await init_beanie(
            database=db,
            document_models=[
                User,
                UserPreference,
                Template,
                Notification,
                Analytics,
            ]
        )
        logger.info("MongoDB database and Beanie ODM initialized successfully.")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}", exc_info=True)
        raise e
