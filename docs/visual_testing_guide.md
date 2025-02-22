# Visual Testing Guide

## Overview

This guide covers the visual regression testing infrastructure for IOTA's Grafana dashboards. Our visual testing framework ensures dashboard consistency across updates by comparing screenshots of dashboard components and detecting visual regressions.

## Architecture

### Components
1. **Test Runner**: Pytest with Selenium WebDriver
2. **Image Processing**: Pillow for screenshot comparison
3. **CI Integration**: GitHub Actions workflow
4. **Services**: Grafana and Prometheus containers

### Directory Structure
```
iota/
├── tests/
│   ├── test_dashboard_visual.py    # Visual regression tests
│   ├── visual_baseline/            # Baseline screenshots
│   └── visual_diff/               # Difference images
├── config/
│   └── grafana/
│       └── validation_dashboard.json
└── .github/
    └── workflows/
        └── ci.yml                  # CI configuration
```

## Test Cases

### 1. Dashboard Layout (`test_dashboard_layout`)
- **Purpose**: Validates overall dashboard structure
- **Checks**:
  - Panel arrangement
  - Navigation elements
  - Header/footer components
- **Baseline**: `dashboard_layout.png`

### 2. Panel Layouts (`test_panel_layouts`)
- **Purpose**: Ensures individual panel consistency
- **Panels Tested**:
  - Errors panel
  - Warnings panel
  - Security panel
  - Duration panel
  - Timestamp panel
- **Baselines**: Individual `*-panel.png` files

### 3. Alert Indicators (`test_alert_indicators`)
- **Purpose**: Verifies alert visualization
- **States Tested**:
  - Normal state
  - Warning state
  - Critical state
- **Baseline**: `alert_indicators.png`

### 4. Time Range Selector (`test_time_range_selector`)
- **Purpose**: Tests time picker functionality
- **Elements**:
  - Range picker
  - Quick selectors
  - Custom range inputs
- **Baseline**: `time_picker.png`

### 5. Theme Testing (`test_dark_light_modes`)
- **Purpose**: Validates theme compatibility
- **Themes**:
  - Dark mode
  - Light mode
- **Baselines**: `dashboard_dark.png`, `dashboard_light.png`

## Running Tests

### Local Environment
```bash
# 1. Install dependencies
pip install -r requirements-test.txt

# 2. Start Grafana
docker run -d -p 3000:3000 grafana/grafana:latest

# 3. Start Prometheus
docker run -d -p 9090:9090 prom/prometheus:v2.45.0

# 4. Run tests
pytest tests/test_dashboard_visual.py -v
```

### CI Environment
Tests run automatically on pull requests and main branch pushes:
```yaml
visual-test:
  services:
    grafana:
      image: grafana/grafana:latest
      ports:
        - 3000:3000
```

## Managing Baselines

### Creating Baselines
- Initial baselines are created automatically when missing
- Store baselines in version control
- Review baselines before committing

### Updating Baselines
```bash
# 1. Delete old baseline
rm tests/visual_baseline/dashboard_layout.png

# 2. Run tests to generate new baseline
pytest tests/test_dashboard_visual.py::test_dashboard_layout
```

### Best Practices
1. Review changes before updating baselines
2. Document baseline updates in commit messages
3. Include before/after screenshots in PRs
4. Version control baseline images

## Analyzing Failures

### Understanding Diff Images
- Red pixels indicate changes
- Location indicates affected components
- Intensity shows degree of change

### Common Issues
1. **Theme Inconsistencies**
   - Symptom: Large areas of red in diff
   - Cause: Theme switching failure
   - Solution: Check theme state before capture

2. **Layout Shifts**
   - Symptom: Component misalignment
   - Cause: CSS/responsive design issues
   - Solution: Verify viewport size

3. **Missing Elements**
   - Symptom: Complete sections in red
   - Cause: Loading/timing issues
   - Solution: Increase wait times

4. **Alert State Differences**
   - Symptom: Alert indicators changed
   - Cause: Test data inconsistency
   - Solution: Reset alert state

## Performance Optimization

### Screenshot Capture
- Use viewport-specific captures
- Implement lazy loading
- Optimize wait conditions

### Image Comparison
- Use threshold-based comparison
- Implement region-specific checks
- Cache comparison results

### CI Performance
- Parallel test execution
- Optimize container startup
- Clean up artifacts regularly

## Troubleshooting Guide

### Common Problems

1. **Tests Fail in CI but Pass Locally**
   - Check browser versions
   - Verify screen resolution
   - Compare timing settings

2. **Inconsistent Screenshots**
   - Ensure stable test data
   - Check animation states
   - Verify loading completion

3. **High Memory Usage**
   - Reduce screenshot resolution
   - Implement garbage collection
   - Optimize diff storage

### Debug Tools
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Save intermediate screenshots
driver.save_screenshot(f"debug_{timestamp}.png")

# Print image differences
print(f"Difference ratio: {difference_ratio}")
```

## Best Practices

### Test Design
1. Keep tests focused and atomic
2. Use descriptive baseline names
3. Implement proper wait conditions
4. Handle dynamic content

### CI Integration
1. Set appropriate timeouts
2. Configure resource limits
3. Manage artifact retention
4. Document environment variables

### Maintenance
1. Regular baseline reviews
2. Performance monitoring
3. Dependency updates
4. Documentation updates

## Future Considerations

### Planned Improvements
1. Multi-browser testing
2. Performance benchmarking
3. Visual test reporting
4. Automated baseline updates

### Scalability
1. Parallel test execution
2. Distributed testing
3. Cloud storage for artifacts
4. Performance optimization

## Contributing

### Adding New Tests
1. Create baseline screenshots
2. Implement test cases
3. Document test purpose
4. Update CI configuration

### Updating Tests
1. Review existing baselines
2. Test in multiple environments
3. Update documentation
4. Verify CI integration

## Support

### Resources
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Pillow Documentation](https://pillow.readthedocs.io/)
- [Grafana HTTP API](https://grafana.com/docs/grafana/latest/http_api/)

### Contact
- Open issues for bugs
- Submit PRs for improvements
- Contact team for questions
