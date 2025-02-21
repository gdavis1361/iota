"""Example of async testing with pytest-asyncio."""
import asyncio
import pytest
from server.core.config import get_settings

async def async_settings_operation():
    """Example async operation that gets settings."""
    await asyncio.sleep(0.1)  # Simulate some async work
    settings = get_settings()
    return settings.APP_NAME

@pytest.mark.asyncio
async def test_async_settings():
    """Test an async operation with settings."""
    result = await async_settings_operation()
    assert result == "iota"

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test multiple async operations running concurrently."""
    # Run multiple async operations concurrently
    results = await asyncio.gather(
        *[async_settings_operation() for _ in range(3)]
    )
    
    # Verify all operations completed successfully
    assert all(result == "iota" for result in results)
    assert len(results) == 3
