"""Example of UI testing with Playwright."""
import pytest
from playwright.async_api import Page, expect

@pytest.mark.asyncio
async def test_homepage_title(page: Page):
    """Test the homepage title."""
    # Navigate to your application
    await page.goto("http://localhost:8000")
    
    # Check the page title
    assert await page.title() == "IOTA Platform"

@pytest.mark.asyncio
async def test_homepage_content(page: Page):
    """Test the homepage content."""
    await page.goto("http://localhost:8000")
    
    # Check for main heading
    heading = page.locator("h1")
    await expect(heading).to_be_visible()
    await expect(heading).to_contain_text("IOTA Platform")
    
    # Check for navigation elements
    nav = page.locator("nav")
    await expect(nav).to_be_visible()
    
    # Check for footer
    footer = page.locator("footer")
    await expect(footer).to_be_visible()

@pytest.mark.asyncio
async def test_error_page(page: Page):
    """Test the error page."""
    # Navigate to a non-existent page
    response = await page.goto("http://localhost:8000/nonexistent")
    
    # Verify we get a 404 status
    assert response.status == 404
    
    # Check for error message
    error_message = page.locator(".error-message")
    await expect(error_message).to_be_visible()
    await expect(error_message).to_contain_text("Page not found")
