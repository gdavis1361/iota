import pytest
from pathlib import Path
from app.core.secrets import SecretsManager
from app.core.config import settings

@pytest.fixture
def secrets_manager():
    return SecretsManager()

def test_secret_set_get(secrets_manager):
    """Test basic secret setting and retrieval."""
    secrets_manager.set_secret("test_key", "test_value")
    secret = secrets_manager.get_secret("test_key")
    assert secret is not None
    assert secret.get_secret_value() == "test_value"

def test_secret_deletion(secrets_manager):
    """Test secret deletion."""
    secrets_manager.set_secret("test_key", "test_value")
    secrets_manager.delete_secret("test_key")
    assert secrets_manager.get_secret("test_key") is None

def test_environment_secret_retrieval(secrets_manager):
    """Test retrieving secrets from environment variables."""
    secret = secrets_manager.get_secret("SECRET_KEY")
    assert secret is not None
    assert secret.get_secret_value() == settings.SECRET_KEY.get_secret_value()

@pytest.mark.skipif(not Path("/run/secrets").exists(),
                    reason="Secrets directory not available")
def test_persistent_secret_storage(secrets_manager):
    """Test persistent secret storage."""
    test_value = "persistent_test_value"
    secrets_manager.set_secret("persistent_key", test_value, persist=True)
    
    # Create new manager instance to test persistence
    new_manager = SecretsManager()
    secret = new_manager.get_secret("persistent_key")
    assert secret is not None
    assert secret.get_secret_value() == test_value
