"""Test error handlers."""
import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.error_handlers import (
    APIError,
    handle_api_error,
    handle_integrity_error,
    handle_unhandled_error,
    setup_error_handlers,
)


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test FastAPI app with error handlers."""
    app = FastAPI()

    # Add test routes
    @app.get("/test-api-error")
    async def test_api_error():
        raise APIError(
            message="Test error",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TEST_ERROR",
        )

    @app.get("/test-integrity-error")
    async def test_integrity_error():
        raise IntegrityError(None, None, None)

    @app.get("/test-unhandled-error")
    async def test_unhandled_error():
        # Ensure this is not caught by any middleware
        raise ValueError("Test error")

    # Set up error handlers after routes
    setup_error_handlers(app)

    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client."""
    return TestClient(test_app)


def test_api_error(test_client):
    """Test custom API error handling."""
    response = test_client.get("/test-api-error")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"] == "Test error"
    assert data["error_code"] == "TEST_ERROR"
    assert data["status_code"] == status.HTTP_400_BAD_REQUEST
    assert "correlation_id" in data


def test_integrity_error(test_client):
    """Test integrity error handling."""
    response = test_client.get("/test-integrity-error")
    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["detail"] == "Resource already exists"
    assert data["error_code"] == "DUPLICATE_RESOURCE"
    assert data["status_code"] == status.HTTP_409_CONFLICT
    assert "correlation_id" in data


def test_unhandled_error(test_client):
    """Test unhandled error handling."""
    response = test_client.get("/test-unhandled-error")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["detail"] == "Internal server error"
    assert data["error_code"] == "INTERNAL_ERROR"
    assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "correlation_id" in data
