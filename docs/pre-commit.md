# Pre-commit Hooks Guide

## Overview

We use pre-commit hooks to automate code quality checks and ensure consistent standards across our codebase. These checks run automatically before each commit, helping catch issues early in the development process.

## Setup

1. Install pre-commit:
```bash
pip install pre-commit
```

2. Install the git hook scripts:
```bash
pre-commit install
```

## Available Hooks

### Code Formatting
- **black**: Formats Python code
  - Line length: 100 characters
  - Python version: 3.9+

### Import Sorting
- **isort**: Sorts Python imports
  - Compatible with black
  - Groups: stdlib, third-party, local

### Linting
- **flake8**: Checks code style and quality
  - Plugins:
    - flake8-docstrings: Documentation style
    - flake8-bugbear: Likely bugs
    - flake8-comprehensions: List/dict/set comprehension style

### Type Checking
- **mypy**: Static type checking
  - Strict mode enabled
  - Additional type stubs: requests, PyYAML, redis

### Security
- **detect-private-key**: Prevents committing private keys
- **check-yaml**: Validates YAML files
- **check-toml**: Validates TOML files
- **check-added-large-files**: Prevents large file commits

## Common Issues and Solutions

### First Run
The first run of pre-commit will be slower as it sets up environments for each tool. Subsequent runs will be much faster.

### Unstaged Changes
If you see "Unstaged files detected":
1. The hook will automatically stash unstaged changes
2. Run checks on staged changes only
3. Restore unstaged changes after completion

### Hook Failures

#### Black/isort Failures
```bash
# Automatically fix formatting
pre-commit run black --all-files
pre-commit run isort --all-files
```

#### Type Check Failures
1. Add missing type annotations
2. Use `# type: ignore` sparingly and with comments

#### Large File Warning
1. Consider if the file should be in version control
2. Use Git LFS if necessary
3. Split into smaller files if possible

### Bypassing Hooks

**WARNING**: Only bypass hooks in exceptional circumstances!

```bash
git commit -m "message" --no-verify
```

Document why you bypassed the hooks in your commit message.

## Maintenance

### Updating Hooks
```bash
pre-commit autoupdate
```

### Clean Cache
If hooks misbehave:
```bash
pre-commit clean
```

### Performance
- Hooks add 5-10 seconds to commit time
- First run: 2-3 minutes for environment setup
- Disk usage: ~500MB for tool environments

## Best Practices

1. **Commit Frequency**
   - Make smaller, focused commits
   - Easier for hooks to process
   - Faster feedback loop

2. **Pre-commit Run**
   - Run hooks before committing:
     ```bash
     pre-commit run --all-files
     ```
   - Fixes issues before commit attempt

3. **Hook Configuration**
   - Don't disable hooks without team discussion
   - Document any configuration changes
   - Keep hook versions updated

4. **Type Annotations**
   - Add types to new code
   - Update existing code gradually
   - Use type checkers in IDE

## Troubleshooting

### Common Error Messages

1. "Module not found"
   - Solution: `pip install -r requirements-dev.txt`

2. "Cache directory not found"
   - Solution: `pre-commit clean && pre-commit install`

3. "Hook X failed"
   - Check specific tool documentation
   - Run hook manually for details
   - Ask team for help if stuck

### Getting Help

1. Check this documentation
2. Run hook with verbose output:
   ```bash
   pre-commit run hook-id -v
   ```
3. Consult team chat/wiki
4. Create an issue if persistent

## References

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
