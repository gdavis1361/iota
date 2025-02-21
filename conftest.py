"""
Root conftest.py for pytest configuration.
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Set test environment
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENV_FILE", "tests/core/test_settings.env")
