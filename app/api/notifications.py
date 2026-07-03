from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Header, Request
from app.core.security import verify_api_key
from app.schemas.notification import NotificationCreate, NotificationResponse, BatchNotificationCreate
from app.services.notification_service import NotificationService
from app.repositories.notification_repository import NotificationRepository
from app.middleware.rate_limit import check_rate_limit
from app.utils.exceptions import ValidationException

router = APIRouter(
    tags=["Notifications"],
    dependencies=[Depends(verify_api_key)]
)

def map_model_to_response(n) -> NotificationResponse:
    """Helper to convert Beanie Notification model to NotificationResponse schema."""
    return NotificationResponse(
        id=str(n.id),
        user_id=str(n.user_id),
        channels=n.channels,
        priority=n.priority,
        template_name=n.template_name,
        variables=n.variables,
        rendered_message=n.rendered_message,
        status=n.status,
        retry_count=n.retry_count,
        idempotency_key=n.idempotency_key,
        delivery_logs=n.delivery_logs,
        webhook_url=n.webhook_url,
        created_at=n.created_at,
        updated_at=n.updated_at
    )

@router.post("/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None)
) -> NotificationResponse:
    """
    Creates and enqueues a new multi-channel notification.
    Enforces hourly rate limiting per user and supports the Idempotency-Key header.
    """
    # Enforce rate limiting
    await check_rate_limit(data.user_id)

    try:
        notification = await NotificationService.create_notification(data, idempotency_key=idempotency_key)
        return map_model_to_response(notification)
    except ValidationException as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ve.message
        )

@router.post("/notifications/batch", response_model=List[NotificationResponse], status_code=status.HTTP_201_CREATED)
async def create_batch_notifications(
    data: BatchNotificationCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None)
) -> List[NotificationResponse]:
    """
    [Bonus Feature] Creates and enqueues a batch of notifications.
    Validates user, templates, and rate limits for all notifications in the payload.
    """
    results = []
    # If an idempotency key is provided for batch, it applies as a prefix or base key
    for idx, item in enumerate(data.notifications):
        # Apply rate limits
        await check_rate_limit(item.user_id)
        
        item_key = f"{idempotency_key}:{idx}" if idempotency_key else None
        try:
            notification = await NotificationService.create_notification(item, idempotency_key=item_key)
            results.append(map_model_to_response(notification))
        except ValidationException as ve:
            # For batch endpoint, raise error if any item fails validation
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch failed at index {idx}: {ve.message}"
            )
    return results

@router.get("/notifications/{id}", response_model=NotificationResponse)
async def get_notification_details(id: str) -> NotificationResponse:
    """
    Retrieves complete delivery details and logs for a specific notification.
    """
    notification = await NotificationRepository.get_by_id(id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {id} not found."
        )
    return map_model_to_response(notification)

@router.get("/users/{id}/notifications", response_model=List[NotificationResponse])
async def get_user_notification_history(id: str) -> List[NotificationResponse]:
    """
    Retrieves the complete notification history list for a user.
    """
    notifications = await NotificationRepository.get_history_by_user(id)
    return [map_model_to_response(n) for n in notifications]
