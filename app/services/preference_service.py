import logging
from datetime import datetime, timezone
from beanie import PydanticObjectId
from app.models.preference import UserPreference
from app.models.user import User
from app.schemas.preference import UserPreferenceUpdate
from app.utils.exceptions import PreferenceException, ValidationException

logger = logging.getLogger(__name__)

class PreferenceService:
    """
    Service layer for managing User Preferences.
    """
    @staticmethod
    async def get_by_user_id(user_id: str) -> UserPreference:
        """
        Retrieves user preferences. If none exist, initializes a default record with all channels enabled.
        """
        try:
            p_user_id = PydanticObjectId(user_id)
        except Exception:
            raise ValidationException(f"Invalid user ID format: {user_id}")

        # Ensure user exists in database
        user = await User.get(p_user_id)
        if not user:
            raise ValidationException(f"User with ID {user_id} not found.")

        # Find preference
        pref = await UserPreference.find_one(UserPreference.user_id == p_user_id)
        if not pref:
            # Create default preferences
            logger.info(f"Preferences not found for user {user_id}. Creating default preferences.")
            pref = UserPreference(
                user_id=p_user_id,
                email_enabled=True,
                sms_enabled=True,
                push_enabled=True
            )
            await pref.insert()
            
        return pref

    @staticmethod
    async def update_preferences(user_id: str, updates: UserPreferenceUpdate) -> UserPreference:
        """
        Updates user preferences. Validates user existence beforehand.
        """
        try:
            p_user_id = PydanticObjectId(user_id)
        except Exception:
            raise ValidationException(f"Invalid user ID format: {user_id}")

        # Check user existence
        user = await User.get(p_user_id)
        if not user:
            raise ValidationException(f"User with ID {user_id} not found.")

        # Get or create preferences
        pref = await UserPreference.find_one(UserPreference.user_id == p_user_id)
        if not pref:
            pref = UserPreference(
                user_id=p_user_id,
                email_enabled=True,
                sms_enabled=True,
                push_enabled=True
            )

        # Apply updates
        if updates.email_enabled is not None:
            pref.email_enabled = updates.email_enabled
        if updates.sms_enabled is not None:
            pref.sms_enabled = updates.sms_enabled
        if updates.push_enabled is not None:
            pref.push_enabled = updates.push_enabled

        pref.updated_at = datetime.now(timezone.utc)
        await pref.save()
        logger.info(f"Preferences updated successfully for user {user_id}.")
        return pref
