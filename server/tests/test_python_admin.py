import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def admin_headers():
    """Create admin authentication headers"""
    # TODO: Create admin token
    token = "admin_token"
    return {"Authorization": f"Bearer {token}"}

def test_admin_dashboard(admin_headers):
    """Test admin dashboard access"""
    response = client.get("/admin/", headers=admin_headers)
    assert response.status_code == 200
    assert "Dashboard" in response.text

def test_user_list(admin_headers):
    """Test user listing page"""
    response = client.get("/admin/users", headers=admin_headers)
    assert response.status_code == 200
    assert "Users" in response.text

def test_user_create(admin_headers):
    """Test user creation form"""
    response = client.get("/admin/users/create", headers=admin_headers)
    assert response.status_code == 200
    assert "Create User" in response.text

def test_unauthorized_access():
    """Test admin access without auth"""
    response = client.get("/admin/")
    assert response.status_code == 401

def test_non_admin_access():
    """Test admin access with non-admin user"""
    # TODO: Create non-admin token
    headers = {"Authorization": "Bearer non_admin_token"}
    response = client.get("/admin/", headers=headers)
    assert response.status_code == 403
