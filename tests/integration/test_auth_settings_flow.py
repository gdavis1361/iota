"""Integration tests for authentication and settings workflows."""
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils.factories import (
    create_test_audit_log,
    create_test_refresh_token,
    create_test_setting,
    create_test_user,
)


@pytest.mark.asyncio
async def test_login_and_update_settings_flow(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test complete flow: login, token refresh, and settings update."""
    # Create test user and initial setting
    user = create_test_user(email="admin@example.com", password="complex123!", is_active=True)
    setting = create_test_setting(key="rate_limit", value=60, description="API rate limit")
    async_session.add(user)
    async_session.add(setting)
    await async_session.commit()

    # Step 1: Login
    login_response = await async_client.post(
        "/api/v1/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": user.email, "password": "complex123!"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]

    # Step 2: Use access token to update setting
    update_response = await async_client.put(
        "/api/v1/settings/rate_limit",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"value": 100},
    )
    assert update_response.status_code == 200
    updated_setting = update_response.json()
    assert updated_setting["value"] == 100

    # Step 3: Verify audit log was created
    audit_response = await async_client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"action": "setting.update"},
    )
    assert audit_response.status_code == 200
    logs = audit_response.json()
    assert len(logs["items"]) > 0
    assert any(
        log["action"] == "setting.update" and log["resource_id"] == "rate_limit"
        for log in logs["items"]
    )


@pytest.mark.asyncio
async def test_login_with_expired_token(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test handling of expired refresh tokens."""
    from datetime import datetime, timedelta, timezone

    # Create user with expired refresh token
    user = create_test_user()
    expired_token = create_test_refresh_token(
        user_id=user.id, expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    async_session.add(user)
    async_session.add(expired_token)
    await async_session.commit()

    # Try to refresh access token
    refresh_response = await async_client.post(
        "/api/v1/login/refresh-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"refresh_token": expired_token.token},
    )
    assert refresh_response.status_code == 400

    # Verify audit log captures failed attempt
    audit_log = create_test_audit_log(
        user_id=user.id, action="token.refresh_failed", details={"reason": "expired"}
    )
    async_session.add(audit_log)
    await async_session.commit()


@pytest.mark.asyncio
async def test_concurrent_settings_update(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test handling of concurrent setting updates."""
    # Create test user and setting
    user = create_test_user()
    setting = create_test_setting(key="max_connections", value=1000)
    async_session.add(user)
    async_session.add(setting)
    await async_session.commit()

    # Login to get access token
    login_response = await async_client.post(
        "/api/v1/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": user.email, "password": "testpass123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Simulate concurrent updates
    import asyncio

    update_tasks = []
    for value in range(1100, 1300, 100):
        task = asyncio.create_task(
            async_client.put(
                "/api/v1/settings/max_connections", headers=auth_headers, json={"value": value}
            )
        )
        update_tasks.append(task)

    # Wait for all updates
    responses = await asyncio.gather(*update_tasks)

    # Verify only one update succeeded, others got conflict error
    success_count = sum(1 for r in responses if r.status_code == 200)
    conflict_count = sum(1 for r in responses if r.status_code == 409)
    assert success_count == 1
    assert conflict_count == len(responses) - 1

    # Verify final state
    get_response = await async_client.get("/api/v1/settings/max_connections", headers=auth_headers)
    assert get_response.status_code == 200
    final_value = get_response.json()["value"]
    assert isinstance(final_value, int)
    assert 1100 <= final_value <= 1200


@pytest.mark.asyncio
async def test_invalid_setting_values(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test handling of invalid setting values."""
    # Create test user and setting
    user = create_test_user()
    setting = create_test_setting(
        key="email_config",
        value={"smtp_host": "smtp.example.com", "smtp_port": 587, "use_tls": True},
    )
    async_session.add(user)
    async_session.add(setting)
    await async_session.commit()

    # Login
    login_response = await async_client.post(
        "/api/v1/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": user.email, "password": "testpass123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Test cases for invalid values
    test_cases = [
        # Wrong type (string instead of dict)
        {"value": "not_a_dict", "expected_status": 422},
        # Missing required field
        {"value": {"smtp_port": 587, "use_tls": True}, "expected_status": 422},
        # Invalid port number
        {
            "value": {"smtp_host": "smtp.example.com", "smtp_port": -1, "use_tls": True},
            "expected_status": 422,
        },
        # Invalid boolean
        {
            "value": {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "use_tls": "yes",  # should be boolean
            },
            "expected_status": 422,
        },
    ]

    # Run test cases
    for case in test_cases:
        response = await async_client.put(
            "/api/v1/settings/email_config", headers=auth_headers, json={"value": case["value"]}
        )
        assert response.status_code == case["expected_status"]

        # Verify original value unchanged
        get_response = await async_client.get("/api/v1/settings/email_config", headers=auth_headers)
        assert get_response.status_code == 200
        current = get_response.json()
        assert current["value"]["smtp_host"] == "smtp.example.com"
        assert current["value"]["smtp_port"] == 587
        assert current["value"]["use_tls"] is True
