"""Visual regression testing for Grafana dashboards using Selenium."""

import os
import time
from datetime import datetime

import pytest
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from scripts.metrics_exporter import ConfigValidationMetrics


class TestDashboardVisual:
    @pytest.fixture(scope="class")
    def driver(self):
        """Initialize Chrome WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(options=options)
        yield driver
        driver.quit()

    @pytest.fixture
    def grafana_url(self):
        """Grafana dashboard URL."""
        return "http://localhost:3000"

    @pytest.fixture
    def baseline_dir(self):
        """Directory for baseline screenshots."""
        return "tests/visual_baseline"

    @pytest.fixture
    def diff_dir(self):
        """Directory for difference images."""
        return "tests/visual_diff"

    @pytest.fixture
    def metrics_exporter(self):
        """Initialize metrics exporter."""
        return ConfigValidationMetrics()

    def setup_method(self):
        """Ensure directories exist."""
        os.makedirs("tests/visual_baseline", exist_ok=True)
        os.makedirs("tests/visual_diff", exist_ok=True)

    def login_to_grafana(self, driver, grafana_url):
        """Login to Grafana dashboard."""
        driver.get(f"{grafana_url}/login")

        # Wait for login form
        username = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "user"))
        )
        password = driver.find_element(By.NAME, "password")

        # Login
        username.send_keys("admin")
        password.send_keys("admin")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Wait for dashboard
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".dashboard-container"))
        )

    def compare_screenshots(self, baseline_path, current_screenshot, diff_path, threshold=0.1):
        """Compare screenshots and generate diff if needed."""
        if not os.path.exists(baseline_path):
            current_screenshot.save(baseline_path)
            return True

        baseline = Image.open(baseline_path)
        current = Image.open(current_screenshot)

        # Ensure same size
        if baseline.size != current.size:
            current = current.resize(baseline.size)

        # Compare images
        diff = Image.new("RGB", baseline.size)
        pixels_different = 0
        total_pixels = baseline.size[0] * baseline.size[1]

        for x in range(baseline.size[0]):
            for y in range(baseline.size[1]):
                r1, g1, b1 = baseline.getpixel((x, y))
                r2, g2, b2 = current.getpixel((x, y))

                if abs(r1 - r2) > 10 or abs(g1 - g2) > 10 or abs(b1 - b2) > 10:
                    diff.putpixel((x, y), (255, 0, 0))
                    pixels_different += 1
                else:
                    diff.putpixel((x, y), (r1, g1, b1))

        difference_ratio = pixels_different / total_pixels
        if difference_ratio > threshold:
            diff.save(diff_path)
            return False
        return True

    def test_dashboard_layout(self, driver, grafana_url, baseline_dir, diff_dir):
        """Test overall dashboard layout."""
        self.login_to_grafana(driver, grafana_url)
        driver.get(f"{grafana_url}/d/validation-dashboard")

        # Wait for dashboard to load
        time.sleep(5)

        # Take screenshot
        screenshot = driver.get_screenshot_as_png()

        # Compare with baseline
        baseline_path = f"{baseline_dir}/dashboard_layout.png"
        diff_path = f"{diff_dir}/dashboard_layout_diff.png"

        assert self.compare_screenshots(
            baseline_path, screenshot, diff_path
        ), "Dashboard layout has changed. Check diff image for details."

    def test_panel_layouts(self, driver, grafana_url, baseline_dir, diff_dir):
        """Test individual panel layouts."""
        self.login_to_grafana(driver, grafana_url)
        driver.get(f"{grafana_url}/d/validation-dashboard")

        # Wait for panels to load
        time.sleep(5)

        panels = [
            "errors-panel",
            "warnings-panel",
            "security-panel",
            "duration-panel",
            "timestamp-panel",
        ]

        for panel_id in panels:
            # Find and screenshot panel
            panel = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, panel_id))
            )
            screenshot = panel.screenshot_as_png

            # Compare with baseline
            baseline_path = f"{baseline_dir}/{panel_id}.png"
            diff_path = f"{diff_dir}/{panel_id}_diff.png"

            assert self.compare_screenshots(
                baseline_path, screenshot, diff_path
            ), f"Panel {panel_id} layout has changed. Check diff image for details."

    def test_alert_indicators(self, driver, grafana_url, baseline_dir, diff_dir, metrics_exporter):
        """Test alert state indicators."""
        # Generate test data to trigger alerts
        metrics_exporter.record_validation_error()
        metrics_exporter.record_validation_warning()
        metrics_exporter.record_security_issue()

        self.login_to_grafana(driver, grafana_url)
        driver.get(f"{grafana_url}/d/validation-dashboard")

        # Wait for alerts to process
        time.sleep(10)

        # Take screenshot of alert section
        alert_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert-list-panel"))
        )
        screenshot = alert_section.screenshot_as_png

        # Compare with baseline
        baseline_path = f"{baseline_dir}/alert_indicators.png"
        diff_path = f"{diff_dir}/alert_indicators_diff.png"

        assert self.compare_screenshots(
            baseline_path, screenshot, diff_path
        ), "Alert indicators have changed. Check diff image for details."

    def test_time_range_selector(self, driver, grafana_url, baseline_dir, diff_dir):
        """Test time range selector appearance."""
        self.login_to_grafana(driver, grafana_url)
        driver.get(f"{grafana_url}/d/validation-dashboard")

        # Open time range picker
        time_picker = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "time-picker"))
        )
        time_picker.click()

        # Wait for picker to open
        time.sleep(2)

        # Take screenshot
        screenshot = driver.get_screenshot_as_png()

        # Compare with baseline
        baseline_path = f"{baseline_dir}/time_picker.png"
        diff_path = f"{diff_dir}/time_picker_diff.png"

        assert self.compare_screenshots(
            baseline_path, screenshot, diff_path
        ), "Time range selector has changed. Check diff image for details."

    def test_dark_light_modes(self, driver, grafana_url, baseline_dir, diff_dir):
        """Test dashboard appearance in dark and light modes."""
        self.login_to_grafana(driver, grafana_url)

        for theme in ["dark", "light"]:
            # Set theme
            driver.get(f"{grafana_url}/org/preferences")
            theme_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "theme"))
            )
            theme_select.click()
            driver.find_element(By.CSS_SELECTOR, f"option[value='{theme}']").click()
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

            # Go to dashboard
            driver.get(f"{grafana_url}/d/validation-dashboard")
            time.sleep(5)

            # Take screenshot
            screenshot = driver.get_screenshot_as_png()

            # Compare with baseline
            baseline_path = f"{baseline_dir}/dashboard_{theme}.png"
            diff_path = f"{diff_dir}/dashboard_{theme}_diff.png"

            assert self.compare_screenshots(
                baseline_path, screenshot, diff_path
            ), f"Dashboard appearance in {theme} mode has changed. Check diff image for details."
