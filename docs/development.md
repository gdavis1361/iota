# Development Setup Guide

## Prerequisites

### Required Software
- Python 3.9+
- Git
- Docker (optional, for containerized development)
- Make (for running development commands)

### Python Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Initial Setup

### 1. Clone the Repository
```bash
git clone https://github.com/gdavis1361/iota.git
cd iota
```

### 2. Configure Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Run against all files (first time setup)
pre-commit run --all-files
```

See [Pre-commit Setup](/Users/allan/Projects/iota/docs/pre-commit.md) for detailed information about our pre-commit hooks.

### 3. Environment Configuration
#### Environment Variables
Required environment variables:
```bash
# Required settings
AUTH_SECRET_KEY=your-secret-key
AUTH_TOKEN_EXPIRE_MINUTES=60

# Optional settings
DEBUG=True
LOG_LEVEL=DEBUG
```

#### Configuration Files
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings:

See [Configuration Management](/Users/allan/Projects/iota/docs/adr/0001-configuration-management.md) for detailed configuration documentation.

## Development Environment

### Development Environment Setup
Follow these steps to set up your development environment:

### Local Development
```bash
# Start development server
python -m server.main

# Start with reload
python -m server.main --reload
```

### Testing Environment
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=server

# Run specific test file
pytest tests/test_config.py

# Run performance tests
pytest tests/performance/
```

See [Testing Guide](/Users/allan/Projects/iota/docs/testing.md) for detailed testing documentation.

## Development Workflow

### 1. Code Quality Tools
We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Style guide enforcement
- **Mypy**: Static type checking
- **Pytest**: Testing framework

These are all configured in `setup.cfg` and run automatically via pre-commit hooks.

### 2. Code Review Process
1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: your descriptive commit message"
   ```

3. Push and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Ensure all checks pass:
   - Pre-commit hooks
   - CI pipeline
   - Code review requirements

See [Contributing Guidelines](/Users/allan/Projects/iota/docs/contributing.md) for detailed contribution workflow.

## Troubleshooting

### Common Issues

1. **Pre-commit Hooks Failing**
   - Run `pre-commit run --all-files` to identify issues
   - Check [Pre-commit Setup](/Users/allan/Projects/iota/docs/pre-commit.md) for specific hook documentation

2. **Import Errors**
   - Ensure virtual environment is activated
   - Verify all dependencies are installed
   - Check [Configuration Management](/Users/allan/Projects/iota/docs/adr/0001-configuration-management.md) for import paths

3. **Test Failures**
   - Check test logs for specific errors
   - Verify environment configuration
   - See [Testing Guide](/Users/allan/Projects/iota/docs/testing.md) for debugging steps

### Getting Help
1. Check existing documentation:
   - [README.md](/Users/allan/Projects/iota/docs/../README.md)
   - [Configuration Management](/Users/allan/Projects/iota/docs/adr/0001-configuration-management.md)
   - [Pre-commit Setup](/Users/allan/Projects/iota/docs/pre-commit.md)

2. Review open and closed issues in the repository

3. Contact the development team:
   - Create a new issue
   - Ask in the development channel
   - Email the maintainers

## Additional Resources

### Documentation
- [Authentication Guide](/Users/allan/Projects/iota/docs/authentication.md)
- [Authorization Guide](/Users/allan/Projects/iota/docs/authorization.md)
- [Operations Guide](/Users/allan/Projects/iota/docs/operations/monitoring.md)
- [API Documentation](/Users/allan/Projects/iota/docs/api/README.md)

### External Resources
- [Python Documentation](https://docs.python.org/3.9/)
- [Git Documentation](https://git-scm.com/doc)
- [Pre-commit Documentation](https://pre-commit.com/)

## Contributing
See our [Contributing Guidelines](/Users/allan/Projects/iota/docs/contributing.md) for detailed information about contributing to the project.
