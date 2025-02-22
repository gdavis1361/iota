# Documentation Style Guide

This guide outlines the standards and best practices for writing documentation in the IOTA project. Following these guidelines ensures consistency, maintainability, and reliability across our documentation.

## Table of Contents

- [General Principles](#general-principles)
- [File Organization](#file-organization)
- [Header Formatting](#header-formatting)
- [Link Formatting](#link-formatting)
- [Code Examples](#code-examples)
- [Configuration Examples](#configuration-examples)
- [Security Documentation](#security-documentation)
- [API Documentation](#api-documentation)
- [Testing Documentation](#testing-documentation)
- [Operations Documentation](#operations-documentation)
- [Review & Maintenance](#review--maintenance)

## General Principles

- **Clarity:** Write clear, concise explanations targeting both new and experienced developers
- **Consistency:** Follow these guidelines across all documentation
- **Completeness:** Include all necessary information, examples, and cross-references
- **Security:** Never include sensitive information like API keys or credentials
- **Validation:** Test all code examples and configuration snippets

## File Organization

### Directory Structure
```
docs/
├── api/           # API documentation
├── adr/           # Architecture Decision Records
├── operations/    # Operational guides
├── development.md # Development setup
├── contributing.md # Contributing guidelines
└── style-guide.md # This guide

tests/
├── integration/   # Integration test docs
├── performance/   # Performance test docs
└── scripts/       # Test utility docs
```

### File Naming
- Use lowercase with hyphens for separation
- Keep names short but descriptive
- Include version numbers in ADRs (e.g., `0001-configuration-management.md`)

## Header Formatting

- Use ATX-style headers (`#` prefix)
- Maximum header depth: 4 levels
- Include a single space after the `#`
- Capitalize first word and proper nouns

Example:
```markdown
# Document Title
## Major Section
### Subsection
#### Minor details
```

## Link Formatting

### Internal Links
- Always use relative paths
- Never start with `/`
- Include file extension

✅ Correct:
```markdown
[Configuration Guide](/Users/allan/Projects/iota/docs/../config/setup.md)
[Security Policy](/Users/allan/Projects/iota/docs/../security.md#security-policy)
```

❌ Incorrect:
```markdown
[Configuration Guide](/Users/allan/Projects/iota/docs/../docs/config/setup.md)
[Security](/Users/allan/Projects/iota/docs/security)
```

### External Links
- Include HTTPS protocol
- Add relevant link text
- Consider adding link checking to CI/CD

## Code Examples

### Python Code
- Include type hints
- Add docstrings for functions
- Use consistent indentation (4 spaces)

```python
def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return all(required in config for required in REQUIRED_FIELDS)
```

### Configuration Examples
- Use YAML for configuration examples
- Include comments for each setting
- Show both required and optional fields

```yaml
# Server Configuration
server:
  host: localhost  # Server hostname
  port: 8080      # HTTP port

  # Optional SSL configuration
  ssl:
    enabled: true
    cert_file: path/to/cert.pem
```

## Security Documentation

### Required Sections
1. Authentication methods
2. Authorization levels
3. Security best practices
4. Error handling
5. Rate limiting
6. Input validation

### Sensitive Information
- Never include real credentials
- Use placeholder values clearly marked as examples
- Document security requirements without implementation details

## API Documentation

### Endpoint Documentation
- Include HTTP method
- Document request/response formats
- List all possible status codes
- Provide curl examples

Example:
```markdown
### Create User

POST /api/v1/users

Request:
```json
{
    "username": "example",
    "email": "user@example.com"
}
```

Response (201 Created):
```json
{
    "id": "user_123",
    "username": "example"
}
```
```

## Testing Documentation

### Test Documentation Requirements
- Setup instructions
- Test data preparation
- Expected results
- Troubleshooting guide
- Performance benchmarks

### Test Examples
- Include both success and failure cases
- Document edge cases
- Show expected output

## Operations Documentation

### Required Sections
1. Monitoring setup
2. Alert configuration
3. Backup procedures
4. Recovery steps
5. Scaling guidelines

### Metrics Documentation
- Document what each metric means
- Include normal ranges
- Specify alert thresholds

## Review & Maintenance

### Regular Reviews
- Monthly documentation audits
- Quarterly security review
- Continuous link verification

### Automated Checks
- Link validation
- Path format verification
- Header structure validation
- Code example syntax checking

### Version Control
- Document significant changes
- Keep a changelog
- Tag documentation versions with releases

---

## Contributing

When contributing to the documentation:
1. Follow this style guide
2. Run verification scripts
3. Test all examples
4. Update cross-references
5. Review security implications

For questions or suggestions about this style guide, please open an issue or contact the documentation team.
