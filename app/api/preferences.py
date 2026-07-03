from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import verify_api_key
from app.schemas.preference import UserPreferenceUpdate, UserPreferenceResponse
from app.services.preference_service import PreferenceService
from app.utils.exceptions import ValidationException

router = APIRouter(
    prefix="/users",
    tags=["Preferences"],
    dependencies=[Depends(verify_api_key)]
)

@router.get("/{id}/preferences", response_model=UserPreferenceResponse)
async def get_preferences(id: str) -> UserPreferenceResponse:
    """
    Fetches notification preferences for a specific user.
    If preferences don't exist, they are initialized with default enabled values.
    """
    try:
        pref = await PreferenceService.get_by_user_id(id)
        return UserPreferenceResponse(
            user_id=str(pref.user_id),
            email_enabled=pref.email_enabled,
            sms_enabled=pref.sms_enabled,
            push_enabled=pref.push_enabled,
            updated_at=pref.updated_at
        )
    except ValidationException as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ve.message
        )

@router.post("/{id}/preferences", response_model=UserPreferenceResponse)
async def update_preferences(id: str, updates: UserPreferenceUpdate) -> UserPreferenceResponse:
    """
    Updates notification preferences for a specific user.
    """
    try:
        pref = await PreferenceService.update_preferences(id, updates)
        return UserPreferenceResponse(
            user_id=str(pref.user_id),
            email_enabled=pref.email_enabled,
            sms_enabled=pref.sms_enabled,
            push_enabled=pref.push_enabled,
            updated_at=pref.updated_at
        )
    except ValidationException as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ve.message
        )
