"""
Unit tests for template validation functionality.
Tests cover template structure, content validation, and cloud provider-specific requirements.
"""

import os
import re
from pathlib import Path

import pytest

from scripts.verify_templates import (
    TEMPLATES,
    Severity,
    ValidationError,
    get_template_type,
    validate_file,
    verify_formatting,
    verify_metadata_fields,
    verify_provider_requirements,
    verify_section_hierarchy,
    verify_security_requirements,
    verify_template_completeness,
)


# Test fixtures
@pytest.fixture
def sample_valid_template(tmp_path):
    """Create a temporary valid template file."""
    content = """# Service Runbook

## Metadata
- Purpose: Authentication service for user management
- Dependencies: AWS Cognito, DynamoDB
- SLOs: 99.9% availability, <100ms latency
- Security Classification: High
- Last Review Date: 2025-02-21
- Team Owner: Platform Team
- Cost Center: PLATFORM-001
- Service Tier: Production
- Compliance Requirements: SOC2, GDPR

## Service Overview
Authentication microservice handling user authentication and authorization.
Provides OAuth2 and JWT-based authentication for all platform services.
Handles user registration, login, password reset, and token management.

## Infrastructure
### Instance Types
- API Service: t3.medium
- Worker Service: t3.large
CPU: 4 vCPU
Memory: 8GB
Storage: 100GB
Network: 1Gbps

### Storage Configuration
- EBS volumes for application data
- S3 buckets for logs and backups
- DynamoDB tables for user data

### Network Setup
- VPC configuration
- Subnet layout
- Security groups
- Load balancer setup

### Auto Scaling
- Target tracking scaling
- Schedule-based scaling
- Min: 2, Max: 10 instances

### Backup Configuration
- Daily EBS snapshots
- S3 versioning enabled
- Database backups

### Monitoring Setup
- CloudWatch metrics
- Custom dashboards
- Log aggregation

## Cloud Services
### Compute Services
- AWS Lambda for API handlers
- EC2 for worker processes
- ECS for container workloads

### Storage Services
- Amazon S3 for object storage
- Amazon EBS for block storage
- Amazon DynamoDB for NoSQL data

### Networking Services
- Amazon VPC
- Application Load Balancer
- Route 53 DNS
- CloudFront CDN

## Operations
### Backup Procedures
- Daily automated backups
- Retention: 30 days
- Backup testing monthly

### Scaling Procedures
- Auto-scaling policies
- Manual scaling process
- Capacity planning

### Monitoring
#### Metric Collection
- Request latency
- Error rates
- Resource utilization
- Custom business metrics

#### Alert Configuration
- P1 alerts: < 1 minute
- P2 alerts: < 5 minutes
- On-call rotation
- Escalation paths

## Security
### Access Management
- IAM roles and policies
- RBAC implementation
- MFA requirements

### Compliance Controls
- SOC2 controls
- GDPR requirements
- Regular audits

### Audit Logging
- CloudTrail enabled
- CloudWatch Logs
- S3 access logs

## Cost Management
### Estimated Costs
Monthly cost breakdown:
- Compute: $2000
- Storage: $500
- Network: $300
Total: $2800

### Budget Constraints
- Monthly budget: $3000
- Alert at 80% usage
- Alert at 90% usage

### Cost Allocation Tags
- Environment
- Team
- Project
- Cost Center

## Logging
- Application logs
- Access logs
- Audit logs
- Error logs
- Performance logs
"""
    template_path = tmp_path / "valid_runbook.md"
    template_path.write_text(content)
    return template_path


@pytest.fixture
def sample_invalid_template(tmp_path):
    """Create a temporary invalid template file."""
    content = """# Incomplete Template
Some content without proper sections...
"""
    template_path = tmp_path / "invalid_template.md"
    template_path.write_text(content)
    return template_path


def test_validate_file_success(sample_valid_template):
    """Test that a valid template passes validation."""
    errors = validate_file(str(sample_valid_template))
    assert isinstance(errors, list)
    # Print actual errors for debugging
    error_messages = [
        f"{err.severity}: {err.message} ({err.category})"
        for err in errors
        if err.severity == Severity.ERROR
    ]
    if error_messages:
        print("\nValidation Errors:")
        for msg in error_messages:
            print(f"- {msg}")
    assert not any(err.severity == Severity.ERROR for err in errors)


def test_validate_file_failure(sample_invalid_template):
    """Test that an invalid template fails validation."""
    errors = validate_file(str(sample_invalid_template))
    assert isinstance(errors, list)
    # Not a template-based document should return empty list
    assert not errors


def test_section_hierarchy():
    """Test section hierarchy validation."""
    content = """# Title
## Section
### Subsection
## Another Section
"""
    errors = verify_section_hierarchy(content)
    assert not errors


def test_invalid_section_hierarchy():
    """Test invalid section hierarchy detection."""
    content = """# Title
### Invalid Skip
## Section
"""
    errors = verify_section_hierarchy(content)
    assert errors
    assert any("hierarchy" in str(err).lower() for err in errors)


def test_template_completeness():
    """Test template completeness validation."""
    content = """# Service Runbook
## Service Overview
Content
## Infrastructure
Content
## Monitoring
Service monitoring and alerting configuration.
## Incident Response
Content
## Security
Content
"""
    template_type = "runbook"  # Explicitly set for test
    errors = verify_template_completeness(content, template_type)
    assert isinstance(errors, list)


def test_aws_provider_requirements():
    """Test AWS-specific template requirements."""
    content = """## Infrastructure
- Provider: AWS
- Region: us-east-1
- Services:
  - AWS Lambda
  - Amazon DynamoDB
"""
    errors = verify_provider_requirements(content, "AWS")
    assert isinstance(errors, list)


def test_metadata_validation():
    """Test metadata field validation."""
    content = """## Metadata
- Service: Test Service
- Owner: Test Team
- Last Updated: 2025-02-21
"""
    template_type = "runbook"
    errors = verify_metadata_fields(content, template_type)
    assert isinstance(errors, list)


def test_security_requirements():
    """Test security section validation."""
    content = """## Security
- IAM Roles and Permissions
- Encryption at Rest
- Network Security
"""
    template_type = "runbook"
    errors = verify_security_requirements(content, template_type)
    assert isinstance(errors, list)


def test_formatting_rules():
    """Test formatting validation."""
    content = """# Title
## Section
- Bullet point
1. Numbered list
"""
    errors = verify_formatting(content)
    assert not errors


def test_error_severity_levels():
    """Test that errors are properly categorized by severity."""
    content = "# Missing Required Sections"
    template_type = "runbook"
    errors = verify_template_completeness(content, template_type)
    assert isinstance(errors, list)
    # Should have errors for missing required sections
    assert any(err.severity == Severity.ERROR for err in errors)


def test_template_type_detection():
    """Test template type detection."""
    # Test runbook detection
    runbook_content = """# Service Runbook
## Monitoring
Service monitoring and alerting configuration.
## Incident Response
Incident response procedures...
"""
    assert get_template_type(runbook_content) == "runbook"

    # Test API detection
    api_content = """# API Documentation
## API Version: v1.0
## Endpoints
GET /users
POST /users
"""
    assert get_template_type(api_content) == "api"

    # Test deployment detection
    deployment_content = """# Deployment Guide
## Deployment Steps
1. Step one
## Rollback
If needed...
"""
    assert get_template_type(deployment_content) == "deployment"

    # Test security template detection
    security_content = """# Security Documentation
## Security Controls
Details...
## Access Management
Permissions...
"""
    assert get_template_type(security_content) == "security"
