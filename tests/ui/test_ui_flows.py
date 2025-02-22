"""
End-to-end UI tests using Playwright.
Tests key user flows and interactions with the IOTA platform UI.
"""

import asyncio
import os
from typing import Any, Dict

import pytest
from playwright.async_api import Browser, Page, expect

# Test data
TEST_USER = {"username": "test_user", "password": "test_password123", "email": "test@example.com"}

# Skip all tests if server is not running
pytestmark = pytest.mark.skipif(
    not os.environ.get("SERVER_RUNNING"), reason="Server is not running. Start the server first."
)


async def fill_form(page: Page, form_data: Dict[str, str], submit: bool = True) -> None:
    """Helper to fill form fields."""
    for field, value in form_data.items():
        await page.fill(f"input[name='{field}']", value)
    if submit:
        await page.click("button[type='submit']")


@pytest.mark.asyncio
async def test_homepage_loads(page: Page):
    """Test that the homepage loads correctly."""
    await page.goto("http://localhost:8000")

    # Check main elements
    await expect(page.locator("h1")).to_contain_text("Welcome to IOTA")
    await expect(page.locator("nav")).to_be_visible()
    await expect(page.locator("footer")).to_be_visible()


@pytest.mark.asyncio
async def test_registration_flow(page: Page):
    """Test the user registration process."""
    await page.goto("http://localhost:8000/register")

    # Fill registration form
    await fill_form(
        page,
        {
            "username": TEST_USER["username"],
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
            "confirm_password": TEST_USER["password"],
        },
    )

    # Should redirect to login
    await expect(page).to_have_url("http://localhost:8000/login")
    await expect(page.locator(".alert-success")).to_contain_text("Registration successful")


@pytest.mark.asyncio
async def test_login_flow(page: Page):
    """Test the login process."""
    await page.goto("http://localhost:8000/login")

    # Fill login form
    await fill_form(page, {"username": TEST_USER["username"], "password": TEST_USER["password"]})

    # Should redirect to dashboard
    await expect(page).to_have_url("http://localhost:8000/dashboard")
    await expect(page.locator("h1")).to_contain_text("Dashboard")


@pytest.mark.asyncio
async def test_error_handling(page: Page):
    """Test error handling in forms."""
    await page.goto("http://localhost:8000/login")

    # Submit empty form
    await page.click("button[type='submit']")

    # Check error messages
    await expect(page.locator(".error-message")).to_be_visible()
    await expect(page.locator(".error-message")).to_contain_text("required")

    # Submit invalid credentials
    await fill_form(page, {"username": "invalid", "password": "invalid"})

    await expect(page.locator(".alert-error")).to_contain_text("Invalid credentials")


@pytest.mark.asyncio
async def test_responsive_design(page: Page):
    """Test responsive design at different viewport sizes."""
    await page.goto("http://localhost:8000")

    # Test mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})
    await expect(page.locator(".mobile-menu-button")).to_be_visible()

    # Test tablet viewport
    await page.set_viewport_size({"width": 768, "height": 1024})
    await expect(page.locator(".mobile-menu-button")).to_be_hidden()

    # Test desktop viewport
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await expect(page.locator("nav")).to_be_visible()


@pytest.mark.asyncio
async def test_form_validation(page: Page):
    """Test client-side form validation."""
    await page.goto("http://localhost:8000/register")

    test_cases = [
        {"field": "email", "value": "invalid-email", "error": "valid email"},
        {"field": "password", "value": "short", "error": "at least 8 characters"},
        {
            "field": "confirm_password",
            "value": "different_password",
            "error": "passwords must match",
        },
    ]

    for test in test_cases:
        await page.fill(f"input[name='{test['field']}']", test["value"])
        await page.click("button[type='submit']")
        error_message = page.locator(f"#{test['field']}-error")
        await expect(error_message).to_contain_text(test["error"])


@pytest.mark.asyncio
async def test_accessibility(page: Page):
    """Test basic accessibility features."""
    await page.goto("http://localhost:8000")

    # Check for ARIA labels
    await expect(page.locator("[aria-label]")).to_have_count(pytest.assume_any_number)

    # Check for alt text on images
    images = await page.locator("img").all()
    for img in images:
        assert await img.get_attribute("alt") is not None

    # Check for form labels
    forms = await page.locator("form").all()
    for form in forms:
        inputs = await form.locator("input").all()
        for input_el in inputs:
            label_for = await input_el.get_attribute("id")
            if label_for:
                assert await page.locator(f"label[for='{label_for}']").count() > 0


@pytest.mark.asyncio
async def test_navigation(page: Page):
    """Test navigation between pages."""
    # Start at homepage
    await page.goto("http://localhost:8000")

    # Click navigation links
    nav_items = [
        ("About", "/about"),
        ("Contact", "/contact"),
        ("Login", "/login"),
        ("Register", "/register"),
    ]

    for text, path in nav_items:
        await page.click(f"text={text}")
        await expect(page).to_have_url(f"http://localhost:8000{path}")

        # Test back navigation
        await page.go_back()
        await expect(page).to_have_url("http://localhost:8000/")


@pytest.mark.asyncio
async def test_dark_mode_toggle(page: Page):
    """Test dark mode toggle functionality."""
    await page.goto("http://localhost:8000")

    # Find and click dark mode toggle
    await page.click("#dark-mode-toggle")

    # Check if dark mode class is applied
    html = page.locator("html")
    await expect(html).to_have_class("dark-mode")

    # Toggle back to light mode
    await page.click("#dark-mode-toggle")
    await expect(html).not_to_have_class("dark-mode")
