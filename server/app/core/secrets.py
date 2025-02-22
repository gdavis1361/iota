import json
from pathlib import Path
from typing import Optional

from app.core.config import settings
from cryptography.fernet import Fernet
from pydantic import SecretStr


class SecretsManager:
    """
    Basic secrets management solution that can be extended later.
    Currently supports:
    1. Encrypted file-based secrets
    2. Environment variable secrets
    3. In-memory secrets cache
    """

    def __init__(self):
        self._secrets_cache = {}
        self._fernet = None
        self._init_encryption()

    def _init_encryption(self) -> None:
        """Initialize encryption key for secrets."""
        key = settings.SECRET_KEY.get_secret_value().encode()
        # In production, use a separate key for secrets encryption
        if settings.ENVIRONMENT.is_production():
            key_path = Path("/run/secrets/secret_key")
            if key_path.exists():
                key = key_path.read_bytes()
        self._fernet = Fernet(Fernet.generate_key())

    def get_secret(self, key: str) -> Optional[SecretStr]:
        """
        Get a secret by key. Checks multiple sources in order:
        1. Memory cache
        2. Environment variables
        3. Encrypted file storage
        """
        # Check cache first
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # Check environment variables
        if hasattr(settings, key):
            value = getattr(settings, key)
            if isinstance(value, SecretStr):
                self._secrets_cache[key] = value
                return value

        # Check encrypted file storage
        secret_file = Path(f"/run/secrets/{key}")
        if secret_file.exists():
            encrypted_data = secret_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            secret = SecretStr(decrypted_data.decode())
            self._secrets_cache[key] = secret
            return secret

        return None

    def set_secret(self, key: str, value: str, persist: bool = False) -> None:
        """
        Set a secret value. Optionally persist to encrypted storage.
        """
        secret = SecretStr(value)
        self._secrets_cache[key] = secret

        if persist and self._fernet:
            secret_file = Path(f"/run/secrets/{key}")
            secret_file.parent.mkdir(parents=True, exist_ok=True)
            encrypted_data = self._fernet.encrypt(value.encode())
            secret_file.write_bytes(encrypted_data)

    def delete_secret(self, key: str) -> None:
        """
        Delete a secret from all storage locations.
        """
        self._secrets_cache.pop(key, None)
        secret_file = Path(f"/run/secrets/{key}")
        if secret_file.exists():
            secret_file.unlink()


# Global secrets manager instance
secrets = SecretsManager()
