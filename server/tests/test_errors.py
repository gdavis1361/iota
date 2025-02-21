import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_404_error():
    """Test not found error"""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

def test_validation_error():
    """Test validation error"""
    response = client.post("/api/v1/auth/register", json={
        "email": "not_an_email",  # Invalid email
        "password": "short"  # Too short password
    })
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) > 0

def test_unauthorized_error():
    """Test unauthorized error"""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()

def test_forbidden_error():
    """Test forbidden error"""
    # TODO: Create non-admin token
    headers = {"Authorization": "Bearer non_admin_token"}
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "forbidden" in data["detail"].lower()

def test_rate_limit_error():
    """Test rate limit error"""
    # Make multiple requests to trigger rate limit
    for _ in range(10):
        client.post("/api/v1/auth/token", 
                   data={"username": "test@example.com", "password": "test"})
    
    response = client.post("/api/v1/auth/token", 
                          data={"username": "test@example.com", "password": "test"})
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    assert "rate limit" in data["detail"].lower()
