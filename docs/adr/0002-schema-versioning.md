# ADR 0002: Schema Versioning for Template Validation

## Status
Accepted

## Context
As our template validation framework evolves, we need a systematic way to:
1. Track changes to validation rules and schema
2. Ensure backward compatibility when possible
3. Provide clear migration paths when breaking changes are necessary
4. Integrate version checking into our CI/CD pipeline

## Decision
We will implement semantic versioning (SemVer) for our validation schema with the following components:

1. Version Structure:
   - MAJOR version for breaking changes (X.y.z)
   - MINOR version for backward-compatible features (x.Y.z)
   - PATCH version for backward-compatible fixes (x.y.Z)

2. Version Storage:
   - Version stored in `validation_rules.json`
   - Version class (`SchemaVersion`) in `config_schema.py`
   - Version compatibility checking in validation script

3. Version Validation:
   - Automated checks in CI/CD pipeline
   - Runtime validation during template checks
   - Version compatibility verification

## Consequences

### Positive
- Clear tracking of schema evolution
- Automated version compatibility checking
- Simplified migration planning
- Better documentation of changes

### Negative
- Additional complexity in schema management
- Need to maintain version compatibility logic
- Potential for version mismatch issues

## Implementation

1. Schema Version Class:
```python
class SchemaVersion(BaseModel):
    major: int
    minor: int
    patch: int
```

2. Version Storage:
```json
{
    "version": "1.0.0",
    "template_types": {
        "alert": {
            "version": "1.0.0",
            "fields": ["name", "description", "severity"]
        },
        "runbook": {
            "version": "1.0.0",
            "fields": ["title", "steps", "verification"]
        }
    }
}
```

3. CI/CD Integration:
- Version validation in GitHub Actions
- Automated tests for version compatibility
- Version checks during template validation

## Migration Guide

### For Template Authors
- No immediate action required for 1.0.0
- Future major versions will include migration guides
- Minor version updates are backward compatible

### For Framework Developers
1. Increment version numbers according to SemVer rules
2. Document all changes in CHANGELOG.md
3. Update tests to cover new version scenarios
4. Provide migration scripts for major version changes

## References
- [Semantic Versioning 2.0.0](https://semver.org/)
- [JSON Schema Versioning](https://json-schema.org/understanding-json-schema/reference/schema.html)
