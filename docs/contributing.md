# Contributing to IOTA

## Getting Started

1. Fork the repository
2. Clone your fork
3. Set up development environment

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code improvements
- `test/` - Test improvements

### 2. Make Changes

Follow our coding standards:
- [Pre-commit Guide](/Users/allan/Projects/iota/docs/pre-commit.md)
- [Testing Guide](/Users/allan/Projects/iota/docs/testing.md)
- [Observability Guide](/Users/allan/Projects/iota/docs/observability.md)

### 3. Commit Changes

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Test updates
- `chore`: Maintenance

Example:
```
feat(rate-limiter): add Redis-based rate limiting

- Implement token bucket algorithm
- Add configuration options
- Update documentation

Closes #123
```

### 4. Quality Checks

Our pre-commit hooks ensure:
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8)
- Type checking (mypy)
- Security checks

Run manually:
```bash
pre-commit run --all-files
```

### 5. Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific tests
pytest tests/path/to/test.py
```

Ensure:
- All tests pass
- Coverage meets 80% minimum
- New features have tests
- Edge cases are covered

### 6. Documentation

Update documentation for:
- New features
- API changes
- Configuration updates
- Breaking changes

Follow our [Documentation Style Guide](/Users/allan/Projects/iota/docs/style-guide.md) for:
- File organization
- Header formatting
- Link formatting
- Code examples
- Security documentation

### 7. Pull Request

1. Push changes to your fork
2. Create PR to main branch
3. Fill PR template
4. Request review

PR Template:
```markdown
## Description
What changes does this PR introduce?

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Added/updated unit tests
- [ ] Added/updated integration tests
- [ ] Tested manually

## Documentation
- [ ] Updated README
- [ ] Updated API docs
- [ ] Updated configuration docs
- [ ] Added ADR if needed

## Additional Notes
Any other context?
```

### 8. Code Review

- Address review comments
- Keep PR focused
- Update tests if needed
- Maintain commit history

### 9. Merge

After approval:
1. Rebase if needed
2. Merge to main
3. Delete branch

## Release Process

1. Version Update
   - Update version in pyproject.toml
   - Create changelog entry

2. Create Release
   - Tag version
   - Write release notes
   - Create GitHub release

3. Deploy
   - CI/CD handles deployment
   - Monitor metrics
   - Watch for issues

## Getting Help

- Check documentation
- Ask in team chat
- Create an issue
- Request pair programming

## Code of Conduct

- Be respectful
- Welcome contributions
- Help others learn
- Give constructive feedback

## Resources

- [Documentation Style Guide](/Users/allan/Projects/iota/docs/style-guide.md)
- [Pre-commit Guide](/Users/allan/Projects/iota/docs/pre-commit.md)
- [Testing Guide](/Users/allan/Projects/iota/docs/testing.md)
- [Observability Guide](/Users/allan/Projects/iota/docs/observability.md)
- [Architecture Decisions](/Users/allan/Projects/iota/docs/adr)
