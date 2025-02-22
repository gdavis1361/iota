#!/usr/bin/env python3
"""Generate a secure secret key for the application."""
import base64
import secrets


def generate_secret_key(length: int = 32) -> str:
    """Generate a secure secret key.

    Args:
        length: Length of the key in bytes. Default is 32 bytes (256 bits).

    Returns:
        A URL-safe base64-encoded string.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode("utf-8")


if __name__ == "__main__":
    secret_key = generate_secret_key()
    print("\nGenerated Secret Key:")
    print("--------------------")
    print(secret_key)
    print("\nAdd this to your .env file as:")
    print(f"SECRET_KEY={secret_key}\n")
