from fastapi.testclient import TestClient
from app.main import app, run_server
import pytest
from unittest.mock import patch
import uvicorn

client = TestClient(app)

def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "JSquared API Server" in response.text
    assert "Swagger UI" in response.text
    assert "ReDoc" in response.text
    assert "API Guide" in response.text

def test_cors():
    """Test CORS headers"""
    # Make an OPTIONS request to check CORS headers
    response = client.options(
        "/api/v1/auth/token",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-allow-methods"] == "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
    assert "content-type" in response.headers["access-control-allow-headers"].lower()

def test_auth_router_included():
    """Test auth router is included"""
    # Get OpenAPI schema to verify auth endpoints are included
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    # Check auth endpoints exist in schema
    paths = schema["paths"]
    assert "/api/v1/auth/token" in paths
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/me" in paths

@patch('uvicorn.run')
def test_main_run(mock_run):
    """Test running the app directly"""
    # Run the server function
    run_server()
    
    # Verify uvicorn.run was called with correct arguments
    mock_run.assert_called_once_with(app, host="0.0.0.0", port=8000)
