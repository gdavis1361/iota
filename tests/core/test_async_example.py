"""Test async functionality examples."""

import asyncio
from typing import AsyncGenerator

import pytest


@pytest.fixture
async def async_gen() -> AsyncGenerator[int, None]:
    """Example async generator fixture."""
    for i in range(3):
        await asyncio.sleep(0.1)
        yield i


@pytest.mark.asyncio
async def test_async_generator(async_gen: AsyncGenerator[int, None]):
    """Test async generator functionality."""
    values = [value async for value in async_gen]
    assert values == [0, 1, 2]


@pytest.mark.asyncio
async def test_async_sleep():
    """Test basic async functionality."""
    start = asyncio.get_event_loop().time()
    await asyncio.sleep(0.1)
    duration = asyncio.get_event_loop().time() - start
    assert duration > 0.1
