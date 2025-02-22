"""Tests for secret key generation functionality."""

import base64

import pytest

from scripts.generate_secret_key import generate_secret_key


def test_generate_secret_key_length():
    """Test that generated key has correct length (32 bytes/256 bits when decoded)."""
    key = generate_secret_key()
    # Decode URL-safe base64
    decoded = base64.urlsafe_b64decode(key.encode("utf-8"))
    assert len(decoded) == 32, "Generated key should be 32 bytes (256 bits)"


def test_generate_secret_key_uniqueness():
    """Test that generated keys are unique."""
    keys = {generate_secret_key() for _ in range(100)}
    assert len(keys) == 100, "Generated keys should be unique"


def test_generate_secret_key_format():
    """Test that generated key is URL-safe base64 encoded."""
    key = generate_secret_key()
    # Should only contain URL-safe characters
    assert all(
        c in "-_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ=" for c in key
    ), "Key should be URL-safe base64 encoded"


def test_generate_secret_key_decodable():
    """Test that generated key can be decoded from base64."""
    key = generate_secret_key()
    try:
        base64.urlsafe_b64decode(key.encode("utf-8"))
    except Exception as e:
        pytest.fail(f"Key should be valid base64: {e}")
