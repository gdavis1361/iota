# 2. Configuration Version Management

Date: 2025-02-21
Status: Accepted
Deciders: Development Team

## Context

The configuration system needs to handle multiple versions of configuration files while ensuring compatibility and providing clear migration paths. We need a robust way to:
- Track configuration versions
- Validate compatibility
- Guide users through migrations
- Monitor version mismatches

## Decision

We've implemented a comprehensive version management system that:

1. Uses explicit version tracking:
```python
VERSION="2.0"  # Required in configuration files
```

2. Implements version validation in ConfigurationMonitor:
- Compares configuration version against schema version
- Logs warnings for mismatches
- Tracks version-related metrics

3. Provides structured documentation:
- Version compatibility matrix
- Migration guidelines
- Best practices
- Security considerations

## Consequences

### Positive
- Clear version tracking and validation
- Early detection of version mismatches
- Improved monitoring and observability
- Better user experience during upgrades
- Reduced configuration errors

### Negative
- Additional complexity in configuration management
- Need to maintain version compatibility documentation
- Increased testing requirements

### Neutral
- Requires explicit version specification
- Migration guidance needed for version updates

## Technical Details

### Version Tracking
```python
class ConfigurationMonitor:
    def _update_metrics(self):
        current_version = self.settings.get_version()
        schema_version = self.settings.get_schema_version()

        if current_version != schema_version:
            self.total_warnings += 1
            logger.warning("version_mismatch",
                         current=current_version,
                         expected=schema_version)
```

### Monitoring Metrics
```python
{
    "config_version": str,
    "schema_version": str,
    "total_warnings": int,
    "total_validations": int
}
```

## Implementation Guidelines

1. Version Specification:
   - Use semantic versioning (MAJOR.MINOR)
   - Document breaking changes
   - Provide migration paths

2. Validation Rules:
   - Check version format
   - Compare against schema version
   - Log appropriate warnings

3. Monitoring:
   - Track version mismatches
   - Monitor validation metrics
   - Alert on persistent issues

## Migration Strategy

1. For Minor Version Updates:
   - Backward compatible changes
   - No migration required
   - Update version number

2. For Major Version Updates:
   - Document breaking changes
   - Provide migration guide
   - Consider migration tooling

## Security Considerations

1. Version Validation:
   - Prevent use of unsupported versions
   - Validate security-critical settings
   - Environment-specific rules

2. Monitoring:
   - Track validation failures
   - Alert on security misconfigurations
   - Log version mismatches

## Future Considerations

1. Version 3.0 Planning:
   - Automated migration tools
   - Enhanced validation rules
   - Improved error messages

2. Documentation:
   - Keep compatibility matrix updated
   - Maintain migration guides
   - Document security implications

## References

- [Configuration System README](/Users/allan/Projects/iota/docs/adr/../../server/core/README.md)
- [Version Compatibility Guide](/Users/allan/Projects/iota/docs/adr/../../server/core/VERSION_COMPATIBILITY.md)
- [Configuration Schema](/Users/allan/Projects/iota/docs/adr/../../server/core/config_schema.py)
