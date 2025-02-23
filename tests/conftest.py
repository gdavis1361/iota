"""
Shared pytest fixtures and configuration.
"""
import os
import asyncio
import pytest
from pathlib import Path
from typing import AsyncGenerator, Generator
from playwright.async_api import async_playwright, Browser, Page

@pytest.fixture(autouse=True)
def test_env():
    """Automatically set test environment for all tests."""
    original_env = dict(os.environ)
    
    # Set base test environment
    test_env_vars = {
        "ENVIRONMENT": "test",
        "ENV_FILE": "tests/core/test_settings.env",
        "APP_NAME": "iota-test",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "SECRET_KEY": "test-secret-key",
        "SENTRY_ENABLED": "false",
        "SENTRY_DSN": "",
        "SENTRY_ENVIRONMENT": "test",
        "SENTRY_TRACES_SAMPLE_RATE": "0.0",
        "SENTRY_PROFILES_SAMPLE_RATE": "0.0",
        "SENTRY_DEBUG": "false",
        "SENTRY_METADATA": "{}"
    }
    
    os.environ.update(test_env_vars)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def server_dir(project_root: Path) -> Path:
    """Get server directory."""
    return project_root / "server"

@pytest.fixture
def test_dir(project_root: Path) -> Path:
    """Get tests directory."""
    return project_root / "tests"

@pytest.fixture
def test_data_dir(test_dir: Path) -> Path:
    """Get test data directory."""
    data_dir = test_dir / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

@pytest.fixture
async def browser() -> AsyncGenerator[Browser, None]:
    """Create a browser instance for UI testing."""
    async with async_playwright() as p:
        # Use chromium in headless mode
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox']
        )
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser: Browser) -> AsyncGenerator[Page, None]:
    """Create a new page for each test."""
    page = await browser.new_page()
    yield page
    await page.close()

@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_time(monkeypatch):
    """Mock time.time() for consistent testing."""
    MOCK_TIME = 1000.0
    
    class MockTime:
        _time = MOCK_TIME
        
        @classmethod
        def time(cls):
            return cls._time
        
        @classmethod
        def sleep(cls, seconds):
            cls._time += seconds
    
    monkeypatch.setattr("time.time", MockTime.time)
    monkeypatch.setattr("time.sleep", MockTime.sleep)
    return MockTime

@pytest.fixture
def base_test_settings():
    """Create a base test settings instance."""
    from server.core.config import Settings, initialize_settings
    
    # Reset any existing settings
    initialize_settings()
    
    # Create and return new settings instance
    return Settings()
