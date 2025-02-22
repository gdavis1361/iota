#!/usr/bin/env python3
import socket
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


def wait_for_service(host: str, port: int, service_name: str, timeout: int = 30):
    """Wait for a service to become available."""
    start_time = time.time()

    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                print(f"✅ {service_name} is ready!")
                return True
        except (socket.timeout, socket.gaierror, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                print(f"❌ {service_name} not available after {timeout} seconds")
                return False
            print(f"⏳ Waiting for {service_name}...")
            time.sleep(1)


def main():
    """Check all required services."""
    services = [
        ("postgres", 5432),
        ("redis", 6379),
    ]

    for service_name, port in services:
        if not wait_for_service(service_name, port, service_name.title()):
            sys.exit(1)

    print("✅ All services are ready!")


if __name__ == "__main__":
    main()
