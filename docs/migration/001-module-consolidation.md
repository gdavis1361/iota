# Module Consolidation Migration Guide

## Overview
This guide explains the recent consolidation of duplicate modules and provides instructions for updating import paths in your code.

## Changes Made

### 1. Configuration Module
- **Old Location**: `server/core/config.py`
- **New Location**: `server/core/config/base.py`
- **Reason**: Consolidated configuration management into a single, well-organized module

#### Update Instructions
```python
# Before
from server.core.config import Config

# After
from server.core.config.base import Config
```

### 2. Sentry Integration
- **Old Location**: `server/core/sentry.py`
- **New Location**: `server/core/middleware/sentry.py`
- **Reason**: Moved Sentry integration to middleware where it logically belongs

#### Update Instructions
```python
# Before
from server.core.sentry import init_sentry

# After
from server.core.middleware.sentry import init_sentry
```

### 3. Database Migrations
- **Old Location**: `server/migrations/env.py`
- **New Location**: `server/alembic/env.py`
- **Reason**: Standardized Alembic configuration location

#### Update Instructions
```python
# No code changes needed - Alembic configuration updated internally
```

### 4. Test Configuration
- **Old Location**: `server/tests/conftest.py`
- **New Location**: `conftest.py`
- **Reason**: Simplified test configuration management

#### Update Instructions
```python
# Your existing test imports should continue to work
# pytest will automatically find the root conftest.py
```

## Verification Steps

1. Run the type checker:
```bash
mypy .
```

2. Verify imports work:
```bash
python -c "from server.core.config.base import Config"
python -c "from server.core.middleware.sentry import init_sentry"
```

3. Run the test suite:
```bash
pytest
```

## Common Issues

### Import Errors
If you see `ModuleNotFoundError`, check:
1. You're using the new import paths
2. Your PYTHONPATH includes the project root
3. You have `__init__.py` files in all parent directories

### Type Checking Errors
If you see mypy errors about duplicate modules:
1. Clear your mypy cache: `mypy --clear-cache`
2. Ensure you're not importing from old locations
3. Check for any remaining duplicate files

## Need Help?
- Review the [Configuration Management ADR](/docs/adr/0001-configuration-management.md)
- Check the [Contributing Guidelines](/docs/contributing.md)
- Raise an issue if you encounter problems
