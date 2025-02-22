"""Test settings endpoint functionality."""
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils.factories import create_test_setting, create_test_user


@pytest.mark.asyncio
async def test_create_setting_success(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test successful setting creation."""
    # Create admin user
    admin = create_test_user(full_name="Admin User")
    async_session.add(admin)
    await async_session.commit()

    # Create setting
    response = await async_client.post(
        "/api/v1/settings",
        json={"key": "rate_limit", "value": 60, "description": "API rate limit per minute"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "rate_limit"
    assert data["value"] == 60


@pytest.mark.asyncio
async def test_create_setting_duplicate_key(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test setting creation with duplicate key."""
    # Create existing setting
    setting = create_test_setting(key="rate_limit", value=60)
    async_session.add(setting)
    await async_session.commit()

    # Try to create setting with same key
    response = await async_client.post(
        "/api/v1/settings",
        json={"key": "rate_limit", "value": 100, "description": "New rate limit"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_setting_success(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test successful setting update."""
    # Create existing setting
    setting = create_test_setting(
        key="email_config", value={"smtp_host": "smtp.example.com", "smtp_port": 587}
    )
    async_session.add(setting)
    await async_session.commit()

    # Update setting
    response = await async_client.put(
        f"/api/v1/settings/{setting.key}",
        json={"value": {"smtp_host": "new.example.com", "smtp_port": 465}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["value"]["smtp_host"] == "new.example.com"
    assert data["value"]["smtp_port"] == 465


@pytest.mark.asyncio
async def test_get_setting_not_found(app: FastAPI, async_client: AsyncClient):
    """Test getting non-existent setting."""
    response = await async_client.get("/api/v1/settings/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_list_settings_pagination(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test settings list with pagination."""
    # Create multiple settings
    settings = [create_test_setting(key=f"setting_{i}", value=i) for i in range(5)]
    for setting in settings:
        async_session.add(setting)
    await async_session.commit()

    # Get first page
    response = await async_client.get("/api/v1/settings?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5

    # Get second page
    response = await async_client.get("/api/v1/settings?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
