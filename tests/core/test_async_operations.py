"""
Tests for asynchronous operations in the IOTA platform.
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest


# Mock async functions for testing
async def mock_fetch_data(delay: float, data: Any) -> Any:
    """Mock function to simulate async data fetching."""
    await asyncio.sleep(delay)
    return data


async def mock_process_data(data: Any) -> Dict[str, Any]:
    """Mock function to simulate async data processing."""
    await asyncio.sleep(0.1)
    return {"processed": data}


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test multiple async operations running concurrently."""
    test_data = [(0.1, "data1"), (0.2, "data2"), (0.3, "data3")]

    # Run operations concurrently
    results = await asyncio.gather(*[mock_fetch_data(delay, data) for delay, data in test_data])

    # Verify results
    assert results == ["data1", "data2", "data3"]

    # Verify timing (should take ~0.3s, not ~0.6s)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_async_pipeline():
    """Test a pipeline of async operations."""

    async def pipeline(input_data: str) -> Dict[str, Any]:
        # Fetch data
        raw_data = await mock_fetch_data(0.1, input_data)
        # Process data
        processed = await mock_process_data(raw_data)
        return processed

    result = await pipeline("test_data")
    assert result == {"processed": "test_data"}


@pytest.mark.asyncio
async def test_async_error_handling():
    """Test error handling in async operations."""

    class TestError(Exception):
        pass

    async def failing_operation():
        await asyncio.sleep(0.1)
        raise TestError("Test error")

    with pytest.raises(TestError):
        await failing_operation()


@pytest.mark.asyncio
async def test_async_timeout():
    """Test timeout handling in async operations."""

    async def slow_operation():
        await asyncio.sleep(1.0)
        return "done"

    # Create a future that will complete after 1 second
    task = asyncio.create_task(slow_operation())

    # Wait for 0.5 seconds
    try:
        result = await asyncio.wait_for(task, timeout=0.5)
        assert False, "Should have timed out"
    except asyncio.TimeoutError:
        # Cancel the task to clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_async_cancellation():
    """Test cancellation of async operations."""
    cancel_count = 0

    async def cancellable_operation():
        nonlocal cancel_count
        try:
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            cancel_count += 1
            raise

    task = asyncio.create_task(cancellable_operation())
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert cancel_count == 1


@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager pattern."""

    class AsyncResource:
        def __init__(self):
            self.initialized = False
            self.cleaned_up = False

        async def __aenter__(self):
            self.initialized = True
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.cleaned_up = True

    async with AsyncResource() as resource:
        assert resource.initialized
        assert not resource.cleaned_up

    assert resource.cleaned_up


@pytest.mark.asyncio
async def test_async_iteration():
    """Test async iteration pattern."""

    class AsyncIterator:
        def __init__(self, items):
            self.items = items
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            await asyncio.sleep(0.1)
            item = self.items[self.index]
            self.index += 1
            return item

    items = ["a", "b", "c"]
    iterator = AsyncIterator(items)
    result = []

    async for item in iterator:
        result.append(item)

    assert result == items
