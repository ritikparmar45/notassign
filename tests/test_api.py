import pytest
from httpx import AsyncClient
from fastapi import status
from app.models.user import User
from app.models.template import Template
from app.models.notification import Notification

API_KEY_HEADERS = {"X-API-Key": "dev-api-key-12345"}

@pytest.mark.asyncio
async def test_auth_failure(client: AsyncClient):
    """
    Verifies that requests without API key header receive 401 Unauthorized.
    """
    response = await client.get("/api/v1/templates")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_templates_api(client: AsyncClient):
    """
    Verifies creating and listing templates via API.
    """
    # Create template
    payload = {
        "name": "promo_code",
        "subject": "Discount for {{name}}",
        "body": "Use code {{code}} for 20% off!"
    }
    
    response = await client.post("/api/v1/templates", json=payload, headers=API_KEY_HEADERS)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "promo_code"
    assert "id" in data
    
    # List templates
    list_response = await client.get("/api/v1/templates", headers=API_KEY_HEADERS)
    assert list_response.status_code == status.HTTP_200_OK
    assert len(list_response.json()) == 1

@pytest.mark.asyncio
async def test_preferences_api(client: AsyncClient, test_user: User):
    """
    Verifies fetching and updating notification preferences.
    """
    user_id = str(test_user.id)
    
    # Fetch default preferences (should auto-create)
    response = await client.get(f"/api/v1/users/{user_id}/preferences", headers=API_KEY_HEADERS)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email_enabled"] is True
    assert data["sms_enabled"] is True
    assert data["push_enabled"] is True

    # Update preferences
    update_payload = {"email_enabled": False, "sms_enabled": False}
    update_response = await client.post(
        f"/api/v1/users/{user_id}/preferences",
        json=update_payload,
        headers=API_KEY_HEADERS
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_data = update_response.json()
    assert updated_data["email_enabled"] is False
    assert updated_data["sms_enabled"] is False
    assert updated_data["push_enabled"] is True  # Left unchanged

@pytest.mark.asyncio
async def test_notifications_dispatch_api(client: AsyncClient, test_user: User, test_template: Template):
    """
    Verifies notification dispatch endpoints including details fetching,
    history listings, and idempotency header handling.
    """
    user_id = str(test_user.id)
    
    payload = {
        "user_id": user_id,
        "channels": ["email", "push"],
        "priority": "High",
        "template_name": test_template.name,
        "variables": {"name": "Alice", "order_id": "987"}
    }
    
    # Create notification with Idempotency-Key
    headers = {**API_KEY_HEADERS, "Idempotency-Key": "unique-key-1"}
    response = await client.post("/api/v1/notifications", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "Queued"
    assert data["priority"] == "High"
    notification_id = data["id"]
    
    # Send identical request with same Idempotency-Key (should return identical status and 200 OK)
    dup_response = await client.post("/api/v1/notifications", json=payload, headers=headers)
    assert dup_response.status_code == status.HTTP_200_OK
    assert dup_response.headers.get("X-Cache-Idempotency") == "true"
    assert dup_response.json()["id"] == notification_id

    # Retrieve notification details
    details_resp = await client.get(f"/api/v1/notifications/{notification_id}", headers=API_KEY_HEADERS)
    assert details_resp.status_code == status.HTTP_200_OK
    assert details_resp.json()["id"] == notification_id

    # Retrieve user history
    history_resp = await client.get(f"/api/v1/users/{user_id}/notifications", headers=API_KEY_HEADERS)
    assert history_resp.status_code == status.HTTP_200_OK
    assert len(history_resp.json()) == 1

@pytest.mark.asyncio
async def test_analytics_and_health_apis(client: AsyncClient):
    """
    Verifies analytics, health checking, and system metrics endpoints.
    """
    # 1. Health check (Public endpoint)
    health_resp = await client.get("/api/v1/health")
    assert health_resp.status_code == status.HTTP_200_OK
    assert health_resp.json()["status"] == "healthy"

    # 2. Metrics check (Public endpoint)
    metrics_resp = await client.get("/api/v1/metrics")
    assert metrics_resp.status_code == status.HTTP_200_OK
    assert "celery_queues_size" in metrics_resp.json()

    # 3. Analytics report (Secure endpoint)
    analytics_resp = await client.get("/api/v1/analytics", headers=API_KEY_HEADERS)
    assert analytics_resp.status_code == status.HTTP_200_OK
    assert "summary" in analytics_resp.json()
