import pytest
from app.services.preference_service import PreferenceService
from app.services.template_service import TemplateService
from app.services.notification_service import NotificationService
from app.schemas.preference import UserPreferenceUpdate
from app.schemas.template import TemplateCreate
from app.schemas.notification import NotificationCreate
from app.models.user import User
from app.models.template import Template
from app.models.notification import Notification, NotificationStatus, NotificationPriority
from app.models.preference import UserPreference
from app.utils.exceptions import ValidationException
from beanie import PydanticObjectId

@pytest.mark.asyncio
async def test_preference_service_lifecycle(test_user: User):
    user_id = str(test_user.id)
    
    # 1. Get preference (should auto-create default)
    pref = await PreferenceService.get_by_user_id(user_id)
    assert pref is not None
    assert pref.user_id == test_user.id
    assert pref.email_enabled is True
    assert pref.sms_enabled is True
    assert pref.push_enabled is True

    # 2. Update preferences
    updates = UserPreferenceUpdate(email_enabled=False, push_enabled=False)
    updated_pref = await PreferenceService.update_preferences(user_id, updates)
    assert updated_pref.email_enabled is False
    assert updated_pref.sms_enabled is True  # Unchanged
    assert updated_pref.push_enabled is False

@pytest.mark.asyncio
async def test_preference_service_invalid_user():
    # Attempting to query non-existent user preferences should fail
    fake_user_id = str(PydanticObjectId())
    with pytest.raises(ValidationException):
        await PreferenceService.get_by_user_id(fake_user_id)

@pytest.mark.asyncio
async def test_template_service_lifecycle():
    # 1. Create template
    data = TemplateCreate(name="order_received", subject="Order Received", body="Hi {{name}}!")
    t = await TemplateService.create_template(data)
    assert t.name == "order_received"
    assert t.body == "Hi {{name}}!"
    
    # 2. Duplicate create should fail
    with pytest.raises(ValidationException):
        await TemplateService.create_template(data)

    # 3. Retrieve template
    retrieved = await TemplateService.get_by_name("order_received")
    assert retrieved.id == t.id

    # 4. List all
    all_t = await TemplateService.list_templates()
    assert len(all_t) == 1

@pytest.mark.asyncio
async def test_notification_service_channel_selection(test_user: User, test_template: Template):
    user_id = str(test_user.id)
    
    # Set preferences: disable SMS, enable Email and Push
    updates = UserPreferenceUpdate(email_enabled=True, sms_enabled=False, push_enabled=True)
    await PreferenceService.update_preferences(user_id, updates)

    # Dispatch notification request requesting email and sms
    req = NotificationCreate(
        user_id=user_id,
        channels=["email", "sms"],
        priority=NotificationPriority.HIGH,
        template_name=test_template.name,
        variables={"name": "John Doe", "order_id": "123"}
    )
    
    # Send
    notification = await NotificationService.create_notification(req)
    assert notification.status == NotificationStatus.QUEUED
    # Verify active channels only contains email (since sms was disabled)
    assert notification.channels == ["email"]
    
    # Verify rendered messages exist for requested channels
    assert "email" in notification.rendered_message
    assert "sms" in notification.rendered_message
    assert "Subject: Your order 123 has shipped" in notification.rendered_message["email"]

@pytest.mark.asyncio
async def test_notification_service_all_channels_disabled(test_user: User, test_template: Template):
    user_id = str(test_user.id)
    
    # Set preferences: disable email
    updates = UserPreferenceUpdate(email_enabled=False, sms_enabled=False, push_enabled=False)
    await PreferenceService.update_preferences(user_id, updates)

    req = NotificationCreate(
        user_id=user_id,
        channels=["email"],
        priority=NotificationPriority.NORMAL,
        template_name=test_template.name,
        variables={"name": "John Doe", "order_id": "123"}
    )
    
    notification = await NotificationService.create_notification(req)
    # Status should be skipped
    assert notification.status == NotificationStatus.SKIPPED
    assert "disabled by user preferences" in notification.delivery_logs[-1]["message"]
