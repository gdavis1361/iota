# Contributing to IOTA

Thank you for your interest in contributing to IOTA! This guide will help you get started with our development process.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Version Management](#version-management)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Documentation](#documentation)
7. [Pull Requests](#pull-requests)

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/iota.git
   cd iota
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Git hooks:
   ```bash
   ./scripts/install_git_hooks.sh
   ```

## Development Environment

### Required Tools
- Python 3.9+
- Git
- Your favorite IDE (VSCode recommended)

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Keep functions focused and small
- Document all public functions and classes

## Version Management

### Version Numbers
We use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Version Bump Process
1. Determine the type of change
2. Use the version bump utility:
   ```bash
   ./scripts/bump_version.py [major|minor|patch] --changes "Your changes"
   ```
3. Verify the changes:
   - Check validation_rules.json
   - Review CHANGELOG.md
   - Run tests

## Making Changes

### Branch Naming
- feature/: New features
- fix/: Bug fixes
- docs/: Documentation updates
- refactor/: Code improvements

Example: `feature/add-custom-metadata`

### Commit Messages
Format:
```
type(scope): Brief description

Detailed description of changes
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- test: Adding tests
- refactor: Code improvement

Example:
```
feat(validation): Add custom metadata support

- Added CustomMetadata class
- Updated validation rules
- Added tests for custom fields
```

### Pre-commit Checks
The pre-commit hook will:
1. Validate schema version
2. Run relevant tests
3. Check documentation

Fix any issues before committing.

## Testing

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_version_compatibility.py

# Run with coverage
python -m pytest --cov=server
```

### Writing Tests
1. Add tests for new features
2. Cover edge cases
3. Test error conditions
4. Verify backward compatibility

## Documentation

### Required Documentation
1. Code documentation:
   - Docstrings for functions/classes
   - Type hints
   - Comments for complex logic

2. User documentation:
   - Update README.md if needed
   - Update migration guide for changes
   - Add examples for new features

3. Technical documentation:
   - ADRs for architectural changes
   - Update CHANGELOG.md
   - Update API documentation

## Pull Requests

### PR Process
1. Create a feature branch
2. Make your changes
3. Run tests locally
4. Update documentation
5. Push changes
6. Create PR

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Added unit tests
- [ ] Updated existing tests
- [ ] Manually tested

## Documentation
- [ ] Updated README
- [ ] Updated CHANGELOG
- [ ] Updated migration guide
- [ ] Added/updated docstrings

## Version Impact
- [ ] Patch (bug fix)
- [ ] Minor (new feature)
- [ ] Major (breaking change)
```

### Review Process
1. PR will be reviewed for:
   - Code quality
   - Test coverage
   - Documentation
   - Version management
2. Address review comments
3. Ensure CI passes
4. Get approval
5. Merge

## Questions?

If you have questions:
1. Check existing documentation
2. Search closed issues
3. Open a new issue

Thank you for contributing to IOTA!
