from typing import Optional, List
from beanie import PydanticObjectId
from app.models.user import User

class UserRepository:
    """
    Repository class handling operations on the Users collection.
    """
    @staticmethod
    async def get_by_id(user_id: str) -> Optional[User]:
        """
        Retrieves a user by their MongoDB ObjectId.
        """
        try:
            return await User.get(PydanticObjectId(user_id))
        except Exception:
            return None

    @staticmethod
    async def get_by_email(email: str) -> Optional[User]:
        """
        Retrieves a user by their email address.
        """
        return await User.find_one(User.email == email)

    @staticmethod
    async def create(name: str, email: str, phone: str) -> User:
        """
        Creates and saves a new user.
        """
        user = User(name=name, email=email, phone=phone)
        return await user.insert()

    @staticmethod
    async def list_all() -> List[User]:
        """
        Lists all users.
        """
        return await User.find_all().to_list()
