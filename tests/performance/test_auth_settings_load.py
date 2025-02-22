"""Performance and load tests for authentication and settings endpoints."""
import asyncio
import time
from datetime import datetime, timezone
from typing import List, Tuple
from urllib.parse import urlencode

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils.factories import create_test_setting, create_test_user


async def measure_response_time(
    callable_func, expected_status: int = 200, error_message: str = None
) -> Tuple[float, bool, dict]:
    """Measure response time of an async callable.

    Args:
        callable_func: Async function to measure
        expected_status: Expected HTTP status code
        error_message: Custom error message if assertion fails

    Returns:
        Tuple of (response_time_seconds, success_boolean, response_data)
    """
    start_time = time.perf_counter()
    response = await callable_func()
    end_time = time.perf_counter()

    success = response.status_code == expected_status
    if not success and error_message:
        print(f"Error: {error_message} - Status: {response.status_code}")

    return (end_time - start_time, success, response.json() if success else {})


@pytest.mark.asyncio
async def test_login_performance(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test login endpoint performance under load.

    Tests both successful and failed login attempts under concurrent load.
    Verifies response times and error handling.
    """
    # Create test users
    users = []
    for i in range(10):
        user = create_test_user(
            email=f"user{i}@example.com", password="testpass123", is_active=True
        )
        users.append(user)
        async_session.add(user)
    await async_session.commit()

    # Measure login performance
    login_times = []
    success_count = 0

    async def login(user, password="testpass123"):
        form_data = {
            "grant_type": "password",
            "username": user.email,
            "password": password,
            "scope": "",
            "client_id": "",
            "client_secret": "",
        }
        return await async_client.post(
            "/api/v1/auth/login/access-token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=urlencode(form_data),
        )

    # Sequential logins for baseline
    for user in users:
        response_time, success, data = await measure_response_time(
            lambda: login(user), error_message=f"Failed login for user {user.email}"
        )
        login_times.append(response_time)
        if success:
            success_count += 1

    avg_time = sum(login_times) / len(login_times)
    assert avg_time < 2.0, f"Average login time {avg_time:.2f}s exceeds threshold"
    assert success_count == len(users), f"Only {success_count}/{len(users)} logins succeeded"

    # Concurrent successful logins
    start_time = time.perf_counter()
    responses = await asyncio.gather(*[login(user) for user in users])
    total_time = time.perf_counter() - start_time

    # Verify concurrent performance
    assert total_time < sum(login_times), "Concurrent logins slower than sequential"
    assert all(r.status_code == 200 for r in responses), "Some concurrent logins failed"

    # Test concurrent failed logins
    failed_responses = await asyncio.gather(*[login(user, "wrongpass") for user in users])
    assert all(
        r.status_code == 401 for r in failed_responses
    ), "Invalid logins not properly rejected"


@pytest.mark.asyncio
async def test_settings_load(async_session: AsyncSession, app: FastAPI, async_client: AsyncClient):
    """Test settings endpoints under concurrent load.

    Tests both individual and bulk operations under load:
    - Concurrent reads and writes
    - Bulk operations
    - Error handling
    - State consistency
    """
    # Create test user and get access token
    user = create_test_user(
        email="settings_test@example.com", password="testpass123", is_active=True
    )
    async_session.add(user)
    await async_session.commit()

    form_data = {
        "grant_type": "password",
        "username": user.email,
        "password": "testpass123",
        "scope": "",
        "client_id": "",
        "client_secret": "",
    }
    login_response = await async_client.post(
        "/api/v1/auth/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=urlencode(form_data),
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    # Create test settings
    settings: List[Tuple[str, int]] = [(f"load_test_{i}", i) for i in range(10)]
    for key, value in settings:
        setting = create_test_setting(key=key, value=value, owner_id=user.id)
        async_session.add(setting)
    await async_session.commit()

    # Test concurrent reads
    async def get_setting(key: str):
        return await async_client.get(f"/api/v1/settings/{key}", headers=auth_headers)

    start_time = time.perf_counter()
    read_responses = await asyncio.gather(*[get_setting(key) for key, _ in settings])
    total_read_time = time.perf_counter() - start_time

    # Verify read performance
    assert total_read_time < 2.0, f"Concurrent reads took {total_read_time:.2f}s"
    assert all(r.status_code == 200 for r in read_responses), "Some reads failed"

    # Test concurrent updates
    async def update_setting(key: str, value: int):
        return await async_client.put(
            f"/api/v1/settings/{key}", headers=auth_headers, json={"value": value + 100}
        )

    start_time = time.perf_counter()
    update_responses = await asyncio.gather(
        *[update_setting(key, value) for key, value in settings]
    )
    total_update_time = time.perf_counter() - start_time

    # Verify update performance and consistency
    assert total_update_time < 3.0, f"Concurrent updates took {total_update_time:.2f}s"
    success_count = sum(1 for r in update_responses if r.status_code == 200)
    assert success_count == len(settings), f"Only {success_count}/{len(settings)} updates succeeded"

    # Test bulk operations
    bulk_settings = [{"key": f"bulk_test_{i}", "value": i} for i in range(5)]

    # Bulk create
    bulk_create_start = time.perf_counter()
    bulk_create_response = await async_client.post(
        "/api/v1/settings/bulk", headers=auth_headers, json={"settings": bulk_settings}
    )
    bulk_create_time = time.perf_counter() - bulk_create_start

    assert bulk_create_response.status_code == 200, "Bulk create failed"
    assert bulk_create_time < 2.0, f"Bulk create took {bulk_create_time:.2f}s"

    # Bulk update
    for setting in bulk_settings:
        setting["value"] += 200

    bulk_update_start = time.perf_counter()
    bulk_update_response = await async_client.put(
        "/api/v1/settings/bulk", headers=auth_headers, json={"settings": bulk_settings}
    )
    bulk_update_time = time.perf_counter() - bulk_update_start

    assert bulk_update_response.status_code == 200, "Bulk update failed"
    assert bulk_update_time < 2.0, f"Bulk update took {bulk_update_time:.2f}s"

    # Verify final state
    for key, original_value in settings:
        response = await get_setting(key)
        assert response.status_code == 200, f"Failed to get setting {key}"
        data = response.json()
        assert data["value"] == original_value + 100, f"Incorrect value for {key}"


@pytest.mark.asyncio
async def test_audit_log_performance(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test audit log creation and query performance.

    Tests audit log performance under load:
    - Concurrent log creation
    - Query performance with filters
    - Pagination performance
    """
    # Create test user and get access token
    user = create_test_user(email="audit_test@example.com", password="testpass123", is_active=True)
    async_session.add(user)
    await async_session.commit()

    form_data = {
        "grant_type": "password",
        "username": user.email,
        "password": "testpass123",
        "scope": "",
        "client_id": "",
        "client_secret": "",
    }
    login_response = await async_client.post(
        "/api/v1/auth/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=urlencode(form_data),
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    # Create test audit logs
    now = datetime.now(timezone.utc)
    audit_logs = []
    for i in range(50):  # Create more logs for pagination testing
        log = {
            "action": f"test_action_{i % 5}",  # 5 different actions
            "resource_id": str(i),
            "timestamp": now.isoformat(),
            "details": {"test_key": f"value_{i}"},
        }
        audit_logs.append(log)

    # Test concurrent log creation
    async def create_log(log_data):
        return await async_client.post("/api/v1/audit-logs", headers=auth_headers, json=log_data)

    start_time = time.perf_counter()
    create_responses = await asyncio.gather(*[create_log(log) for log in audit_logs])
    total_create_time = time.perf_counter() - start_time

    assert total_create_time < 5.0, f"Bulk log creation took {total_create_time:.2f}s"
    assert all(r.status_code == 200 for r in create_responses), "Some log creations failed"

    # Test query performance with filters
    async def query_logs(params: dict):
        query_string = urlencode(params)
        return await async_client.get(f"/api/v1/audit-logs?{query_string}", headers=auth_headers)

    # Test different query scenarios
    query_scenarios = [
        ({"action": "test_action_0"}, "action filter"),
        ({"start_time": now.isoformat()}, "time range filter"),
        ({"limit": 10, "offset": 0}, "first page"),
        ({"limit": 10, "offset": 40}, "last page"),
        ({"action": "test_action_0", "limit": 5}, "combined filters"),
    ]

    for params, scenario in query_scenarios:
        start_time = time.perf_counter()
        response = await query_logs(params)
        query_time = time.perf_counter() - start_time

        assert response.status_code == 200, f"Query failed for {scenario}"
        assert query_time < 1.0, f"Query too slow for {scenario}: {query_time:.2f}s"

        # Verify response data
        data = response.json()
        assert "items" in data, f"Missing items in response for {scenario}"
        assert "total" in data, f"Missing total in response for {scenario}"

        if "limit" in params:
            assert len(data["items"]) <= params["limit"], f"Too many items returned for {scenario}"
