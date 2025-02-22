# Version Management and Git Hooks

## Overview

This document describes the version management system and Git hook functionality in IOTA. The system provides tools for managing semantic versioning, changelog generation, and automated validation through Git hooks.

## Version Management

### SchemaVersion Class

The `SchemaVersion` class handles semantic versioning with proper parsing and compatibility checking.

```python
from scripts.bump_version import SchemaVersion

# Create version object
version = SchemaVersion.from_str("1.0.0")

# Check compatibility
other_version = SchemaVersion.from_str("1.1.0")
is_compatible = version.is_compatible_with(other_version)
```

#### Version Compatibility Rules

- Major version must match for compatibility
- Minor version must be greater than or equal
- Patch version does not affect compatibility

### Version Bump Utility

The version bump utility supports semantic versioning increments:

```bash
# Bump major version (e.g., 1.0.0 -> 2.0.0)
python scripts/bump_version.py --type major

# Bump minor version (e.g., 1.0.0 -> 1.1.0)
python scripts/bump_version.py --type minor

# Bump patch version (e.g., 1.0.0 -> 1.0.1)
python scripts/bump_version.py --type patch
```

## Changelog Management

The changelog system supports both simple lists and categorized changes:

### Simple List Format

```python
from scripts.update_changelog import update_changelog

# Simple list of changes
changes = [
    "Added new feature X",
    "Fixed bug in component Y",
    "Updated documentation"
]

update_changelog("1.1.0", changes)
```

### Categorized Changes

```python
# Categorized changes
changes = {
    "Added": [
        "New feature X",
        "Support for Y"
    ],
    "Fixed": [
        "Bug in component Z",
        "Performance issue in W"
    ]
}

update_changelog("1.1.0", changes)
```

## Git Hooks

### Installation

Install Git hooks using the provided script:

```bash
./scripts/install_git_hooks.sh
```

### Available Hooks

#### Pre-commit Hook

The pre-commit hook performs the following validations:

1. Configuration validation
2. Template verification
3. Version compatibility check

### Customizing Hooks

To customize the pre-commit hook, modify `scripts/git-hooks/pre-commit`. Example:

```bash
#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# Add custom validation
python "$PROJECT_ROOT/scripts/custom_validation.py"
if [ $? -ne 0 ]; then
    echo "❌ Custom validation failed"
    exit 1
fi
```

## Error Handling

### Common Errors

1. **Invalid Version String**
   ```
   ValueError: Invalid version string: invalid_version
   ```
   - Ensure version follows semantic versioning format (X.Y.Z)
   - All components must be non-negative integers

2. **Missing Git Directory**
   ```
   Error: .git directory not found
   ```
   - Run the hook installation from the project root
   - Ensure the repository is initialized

3. **Version Compatibility**
   ```
   ValueError: Incompatible version
   ```
   - Check major version matches
   - Ensure minor version is not decreased

## Logging

The system uses structured logging with multiple levels:

```python
from server.core.logging_config import setup_logger

logger = setup_logger()
logger.debug("Detailed debugging information")
logger.info("General operational information")
logger.warning("Warning messages for potentially harmful situations")
logger.error("Error messages for serious problems")
logger.critical("Critical messages for fatal errors")
```

## Best Practices

1. **Version Management**
   - Always use semantic versioning
   - Document breaking changes in major version bumps
   - Update changelog with every version change

2. **Git Hooks**
   - Keep hooks focused and fast
   - Add proper error messages
   - Handle edge cases gracefully

3. **Error Handling**
   - Validate inputs early
   - Provide clear error messages
   - Log errors with appropriate context

## Contributing

When contributing to the version management system:

1. Add tests for new functionality
2. Update documentation
3. Follow semantic versioning rules
4. Include changelog entries
