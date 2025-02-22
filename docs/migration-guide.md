# IOTA Template Migration Guide

This guide helps you migrate templates between different versions of the IOTA validation framework.

## Version Compatibility

IOTA uses semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes requiring template updates
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

## Current Version: 1.0.0

Version 1.0.0 introduces schema versioning and enhanced validation. Key changes:

1. Added version field to validation rules
2. Enhanced error reporting
3. Improved validation for nested structures

### Migrating to 1.0.0

1. Update `validation_rules.json`:
   ```json
   {
     "version": "1.0.0",
     "template_types": {
       // ... existing configuration
     }
   }
   ```

2. Run validation:
   ```bash
   python scripts/validate_config.py
   ```

3. Update templates if needed:
   - Add missing required fields
   - Fix any validation errors
   - Test with new validation rules

## Migration Process

When migrating between versions:

1. **Check Compatibility**
   ```bash
   python scripts/validate_config.py
   ```
   - Review validation results
   - Note any compatibility issues

2. **Update Configuration**
   - Use version bump utility for controlled updates:
     ```bash
     ./scripts/bump_version.py [major|minor|patch] --changes "description"
     ```
   - Review CHANGELOG.md for required changes

3. **Test Templates**
   - Run validation on all templates
   - Fix any validation errors
   - Test template functionality

4. **Update Documentation**
   - Update template examples
   - Document any breaking changes
   - Update usage instructions

## Version-Specific Changes

### 1.0.0 → 2.0.0 (Future)
- TBD: Will document breaking changes
- Will include automated migration scripts
- Will provide template conversion tools

### 0.1.0 → 1.0.0
- Added version field (required)
- Enhanced validation rules
- Improved error messages

## Troubleshooting

### Common Issues

1. **Version Parsing Errors**
   - Ensure version follows X.Y.Z format
   - Use only numeric values
   - Example: "1.0.0"

2. **Validation Failures**
   - Check required fields
   - Verify field types
   - Review nested structures

3. **Schema Compatibility**
   - Verify MAJOR version matches
   - Update to latest PATCH version
   - Review breaking changes

### Getting Help

1. Check documentation:
   - README.md
   - CHANGELOG.md
   - ADRs in docs/adr/

2. Run validation with debug:
   ```bash
   python scripts/validate_config.py --debug
   ```

3. Review test results:
   ```bash
   python -m pytest tests/ -v
   ```

## Best Practices

1. **Version Management**
   - Use version bump utility
   - Include clear changelog entries
   - Test before and after updates

2. **Template Updates**
   - Make incremental changes
   - Test each change
   - Document modifications

3. **Configuration Management**
   - Back up configurations
   - Use version control
   - Review changes carefully

## Future Migrations

As the validation framework evolves:
1. New versions will include migration guides
2. Breaking changes will be clearly documented
3. Migration tools will be provided
4. Test coverage will be maintained

Keep your templates and validation rules updated to ensure compatibility with future versions.
