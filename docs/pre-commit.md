# Pre-commit Hooks Guide

## Overview
This guide explains the pre-commit hooks used in the project to maintain code quality and consistency.

## Setup

1. Install pre-commit:
```bash
pip install pre-commit
pre-commit install
```

2. The hooks will run automatically on `git commit`. To run manually:
```bash
pre-commit run --all-files
```

## Hooks Configuration

### Code Formatting
- **black**: Python code formatter (max line length: 79)
- **isort**: Import sorting
- **docformatter**: Docstring formatting
  - Wraps summaries at 79 characters
  - Wraps descriptions at 79 characters
  - Ensures consistent docstring style

### Linting
- **flake8**: Python linter
  - Checks code style
  - Enforces docstring standards
  - Validates import usage
  - Line length limit: 79 characters

### Type Checking
- **mypy**: Static type checker
  - Strict mode enabled
  - Checks all imported packages
  - Validates type hints

### Security
- **detect-private-key**: Prevents committing private keys
- **check-added-large-files**: Prevents large files (>500KB)

### File Maintenance
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with newline
- **check-yaml**: Validates YAML files
- **check-toml**: Validates TOML files

## Common Issues and Solutions

### Large Files
- Files exceeding 500KB will be rejected
- For templates or large data files:
  - Use .gitignore
  - Store templates separately
  - Consider using template generators

### Import Sorting
- Imports are sorted into sections:
  1. Standard library
  2. Third-party packages
  3. Local imports
- Use `# isort: skip` for special cases

### Type Checking
- All new code must include type hints
- Use `# type: ignore` sparingly and with comments
- Import types from `typing` module

### Docstring Standards
- Every public function/class needs a docstring
- Follow Google style format
- Include type information in docstrings
- Add examples for complex functions

## Best Practices

1. **Run Hooks Early**
   - Run `pre-commit run` before committing
   - Fix issues incrementally

2. **Keep Files Small**
   - Split large files into modules
   - Use proper code organization

3. **Maintain Documentation**
   - Update docs when changing code
   - Keep examples current

4. **Handle Exceptions**
   - Document any `# type: ignore` usage
   - Explain skipped validations

## Module Organization
- Keep related code together
- Avoid duplicate modules
- Use clear, consistent naming
- Follow the established package structure

## CI Integration
Pre-commit hooks are also run in CI:
- GitHub Actions workflow
- Required checks must pass
- Same configuration as local

## Related Documentation
- [Configuration Management](/Users/allan/Projects/iota/docs/adr/0001-configuration-management.md)
- [Contributing Guidelines](/Users/allan/Projects/iota/docs/contributing.md)
- [Development Setup](/Users/allan/Projects/iota/docs/development.md)
