#!/usr/bin/env python3
"""Template validation script for documentation.

This script verifies that documentation files follow our template standards by:
1. Checking required sections are present
2. Validating section hierarchy
3. Ensuring required metadata is included
4. Verifying formatting standards
5. Validating cloud-specific requirements
6. Checking security documentation
7. Verifying operational readiness
8. Ensuring cost management documentation
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    message: str
    file: str
    line: Optional[int]
    severity: Severity
    category: str
    suggestion: Optional[str] = None

    def to_github_error(self) -> str:
        """Convert to GitHub Actions error format."""
        prefix = f"::{self.severity.value} file={self.file}"
        if self.line:
            prefix += f",line={self.line}"
        return f"{prefix}::{self.message}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "severity": self.severity.value,
            "category": self.category,
            "suggestion": self.suggestion,
        }


# Cloud provider specific requirements
CLOUD_PROVIDERS = {
    "AWS": {
        "compute": [
            "EC2",
            "ECS",
            "EKS",
            "Lambda",
            "Fargate",
            "Batch",
            "Elastic Beanstalk",
            "Lightsail",
        ],
        "storage": ["S3", "EBS", "EFS", "FSx", "Storage Gateway", "S3 Glacier", "Lake Formation"],
        "database": [
            "RDS",
            "DynamoDB",
            "ElastiCache",
            "Redshift",
            "DocumentDB",
            "Neptune",
            "QLDB",
            "Timestream",
        ],
        "networking": [
            "VPC",
            "Route53",
            "CloudFront",
            "API Gateway",
            "Direct Connect",
            "Global Accelerator",
            "Transit Gateway",
        ],
        "security": [
            "IAM",
            "KMS",
            "CloudHSM",
            "Shield",
            "WAF",
            "Security Hub",
            "GuardDuty",
            "Macie",
        ],
        "monitoring": [
            "CloudWatch",
            "CloudTrail",
            "Config",
            "EventBridge",
            "X-Ray",
            "Service Health Dashboard",
        ],
        "cost_management": [
            "Cost Explorer",
            "Budgets",
            "Cost and Usage Report",
            "Savings Plans",
            "Reserved Instances",
        ],
    },
    "GCP": {
        "compute": [
            "Compute Engine",
            "GKE",
            "Cloud Functions",
            "Cloud Run",
            "App Engine",
            "Sole-tenant Nodes",
        ],
        "storage": [
            "Cloud Storage",
            "Persistent Disk",
            "Filestore",
            "Transfer Service",
            "Archive Storage",
        ],
        "database": [
            "Cloud SQL",
            "Cloud Spanner",
            "Cloud Bigtable",
            "Firestore",
            "Memorystore",
            "BigQuery",
        ],
        "networking": [
            "VPC",
            "Cloud DNS",
            "Cloud CDN",
            "Cloud Load Balancing",
            "Cloud Interconnect",
            "Cloud VPN",
        ],
        "security": [
            "IAM",
            "KMS",
            "Secret Manager",
            "Cloud Armor",
            "Security Command Center",
            "Cloud Asset Inventory",
        ],
        "monitoring": [
            "Cloud Monitoring",
            "Cloud Logging",
            "Error Reporting",
            "Cloud Trace",
            "Cloud Profiler",
        ],
        "cost_management": [
            "Cost Management",
            "Billing API",
            "Committed Use Discounts",
            "Preemptible VMs",
            "Sustained Use Discounts",
        ],
    },
    "Azure": {
        "compute": [
            "Virtual Machines",
            "AKS",
            "Functions",
            "App Service",
            "Container Instances",
            "Batch",
            "Service Fabric",
        ],
        "storage": [
            "Blob Storage",
            "Disk Storage",
            "Files",
            "Archive Storage",
            "Data Lake Storage",
            "StorSimple",
        ],
        "database": [
            "Azure SQL",
            "Cosmos DB",
            "Database for MySQL",
            "Database for PostgreSQL",
            "Cache for Redis",
        ],
        "networking": [
            "Virtual Network",
            "DNS",
            "CDN",
            "Load Balancer",
            "Application Gateway",
            "ExpressRoute",
        ],
        "security": [
            "Active Directory",
            "Key Vault",
            "DDoS Protection",
            "Security Center",
            "Sentinel",
            "Information Protection",
        ],
        "monitoring": [
            "Monitor",
            "Log Analytics",
            "Application Insights",
            "Network Watcher",
            "Service Health",
        ],
        "cost_management": [
            "Cost Management",
            "Billing API",
            "Reserved Instances",
            "Spot VMs",
            "Hybrid Benefit",
        ],
    },
}


# Load validation configuration
def load_validation_config() -> Dict[str, Any]:
    """Load validation rules from configuration file."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "validation_rules.json"
    )
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load validation config: {e}")
        return {}


VALIDATION_CONFIG = load_validation_config()

# Additional template types
TEMPLATES = {
    "api": {
        "path": "docs/templates/api.md",
        "required_sections": [
            "# ",  # Title
            "## Overview",
            "## Authentication",
            "## Endpoints",
            "## Error Handling",
            "## Rate Limiting",
            "## Security Considerations",
            "## Monitoring",
            "## Performance",
            "## Scalability",
            "## Service Dependencies",
            "## Data Flow",
            "## Infrastructure Requirements",
        ],
        "metadata_fields": [
            "API Version",
            "Last Updated",
            "Status",
            "Security Classification",
            "Data Sensitivity Level",
            "Required Authentication",
            "Infrastructure Requirements",
            "Scaling Thresholds",
            "Rate Limits",
            "Response Time SLA",
            "Availability Target",
            "Region Availability",
        ],
        "security_requirements": [
            "Authentication",
            "Authorization",
            "Rate Limiting",
            "Data Encryption",
            "Access Control",
            "API Key Management",
            "Token Expiry",
            "CORS Policy",
            "Input Validation",
            "Output Sanitization",
        ],
        "cloud_requirements": {
            "scaling": [
                "Auto-scaling Configuration",
                "Load Balancing Strategy",
                "Scaling Metrics",
                "Scaling Thresholds",
            ],
            "reliability": [
                "Failover Strategy",
                "Backup Procedures",
                "Disaster Recovery",
                "Data Replication",
            ],
            "monitoring": [
                "Health Checks",
                "Performance Metrics",
                "Error Rate Tracking",
                "Resource Utilization",
                "Cost Monitoring",
            ],
            "networking": ["CDN Configuration", "DNS Requirements", "VPC Setup", "Security Groups"],
        },
    },
    "deployment": {
        "path": "docs/templates/deployment.md",
        "required_sections": [
            "# ",  # Title
            "## Overview",
            "## Prerequisites",
            "## Security Requirements",
            "## Resource Requirements",
            "## Infrastructure Setup",
            "## Network Configuration",
            "## Deployment Steps",
            "## Verification",
            "## Rollback Procedure",
            "## Monitoring Setup",
            "## Scaling Configuration",
            "## Cost Estimation",
        ],
        "metadata_fields": [
            "Component Version",
            "Last Updated",
            "Environment",
            "Resource Requirements",
            "Security Level",
            "Backup Requirements",
            "Cloud Provider",
            "Region",
            "Instance Types",
            "Network Requirements",
            "Storage Requirements",
            "Estimated Costs",
        ],
        "security_requirements": [
            "Access Controls",
            "Network Security",
            "Data Protection",
            "Compliance Requirements",
            "Backup Strategy",
            "IAM Policies",
            "Security Groups",
            "Encryption Requirements",
            "Certificate Management",
            "Secret Management",
        ],
        "cloud_requirements": {
            "infrastructure": [
                "Instance Types",
                "Storage Configuration",
                "Network Setup",
                "Load Balancer Configuration",
            ],
            "security": ["IAM Roles", "Security Groups", "KMS Configuration", "SSL/TLS Setup"],
            "monitoring": [
                "CloudWatch Metrics",
                "Log Aggregation",
                "Alerting Rules",
                "Dashboard Setup",
            ],
            "automation": [
                "Infrastructure as Code",
                "CI/CD Pipeline",
                "Automated Testing",
                "Deployment Automation",
            ],
        },
    },
    "runbook": {
        "path": "docs/templates/runbook.md",
        "required_sections": [
            "# ",  # Title
            "## Service Overview",
            "## Architecture",
            "## Infrastructure",
            "## Monitoring",
            "## Incident Response",
            "## Routine Operations",
            "## Security Protocols",
            "## Disaster Recovery",
            "## Compliance",
            "## Cost Management",
            "## Performance Optimization",
        ],
        "metadata_fields": [
            "Purpose",
            "Dependencies",
            "SLOs",
            "Security Classification",
            "Compliance Requirements",
            "Last Review Date",
            "Cloud Provider",
            "Primary Region",
            "DR Region",
            "Service Tier",
            "Cost Center",
            "Team Owner",
        ],
        "security_requirements": [
            "Access Management",
            "Incident Response",
            "Compliance Controls",
            "Data Protection",
            "Audit Logging",
            "Key Rotation",
            "Vulnerability Scanning",
            "Penetration Testing",
            "Security Monitoring",
            "Compliance Reporting",
        ],
        "cloud_requirements": {
            "operations": [
                "Backup Procedures",
                "Scaling Procedures",
                "Failover Process",
                "Maintenance Windows",
            ],
            "monitoring": [
                "Metric Collection",
                "Log Analysis",
                "Alert Configuration",
                "Dashboard Access",
            ],
            "security": [
                "Access Control",
                "Data Protection",
                "Network Security",
                "Compliance Checks",
            ],
            "cost": [
                "Budget Tracking",
                "Resource Optimization",
                "Cost Allocation",
                "Usage Monitoring",
            ],
        },
    },
    "security": {
        "path": "docs/templates/security.md",
        "required_sections": [
            "# ",  # Title
            "## Overview",
            "## Security Controls",
            "## Access Management",
            "## Data Protection",
            "## Network Security",
            "## Compliance",
            "## Security Monitoring",
            "## Incident Response",
            "## Vulnerability Management",
            "## Security Testing",
            "## Audit Logging",
        ],
        "metadata_fields": [
            "Security Level",
            "Data Classification",
            "Compliance Framework",
            "Last Security Review",
            "Next Review Date",
            "Security Owner",
            "Incident Contact",
        ],
        "cloud_requirements": {
            "identity": [
                "IAM Configuration",
                "Role-Based Access",
                "Service Accounts",
                "Federation Setup",
            ],
            "encryption": [
                "Data at Rest",
                "Data in Transit",
                "Key Management",
                "Certificate Management",
            ],
            "network": [
                "Network Segmentation",
                "Firewall Rules",
                "VPC Configuration",
                "Security Groups",
            ],
            "monitoring": [
                "Security Logging",
                "Audit Trails",
                "Threat Detection",
                "Compliance Monitoring",
            ],
        },
    },
    "disaster_recovery": {
        "path": "docs/templates/dr.md",
        "required_sections": [
            "# ",  # Title
            "## Overview",
            "## Recovery Objectives",
            "## DR Strategy",
            "## Backup Procedures",
            "## Recovery Procedures",
            "## Testing Plan",
            "## Communication Plan",
            "## Roles and Responsibilities",
            "## Recovery Validation",
            "## Post-Recovery Actions",
        ],
        "metadata_fields": [
            "RPO",
            "RTO",
            "DR Region",
            "Last DR Test",
            "Next Test Date",
            "DR Coordinator",
            "Business Impact",
        ],
        "cloud_requirements": {
            "replication": [
                "Data Replication",
                "Database Mirroring",
                "Storage Synchronization",
                "Configuration Backup",
            ],
            "failover": [
                "DNS Failover",
                "Load Balancer Configuration",
                "Auto-scaling Setup",
                "Health Checks",
            ],
            "recovery": [
                "Recovery Automation",
                "Data Restoration",
                "Service Recovery",
                "Validation Steps",
            ],
            "testing": [
                "DR Testing Schedule",
                "Test Scenarios",
                "Success Criteria",
                "Test Results",
            ],
        },
    },
    "monitoring": {
        "path": "docs/templates/monitoring.md",
        "required_sections": [
            "# ",  # Title
            "## Overview",
            "## Metrics and KPIs",
            "## Alert Configuration",
            "## Dashboard Setup",
            "## Log Management",
            "## Incident Detection",
            "## Performance Monitoring",
            "## Cost Monitoring",
            "## Health Checks",
            "## Reporting",
        ],
        "metadata_fields": [
            "Service Name",
            "Alert Contacts",
            "Dashboard URL",
            "Log Retention",
            "Update Frequency",
            "Critical Metrics",
            "SLO Targets",
        ],
        "cloud_requirements": {
            "metrics": ["Custom Metrics", "System Metrics", "Business Metrics", "SLO Metrics"],
            "logging": ["Log Collection", "Log Analysis", "Log Storage", "Log Security"],
            "alerting": [
                "Alert Rules",
                "Notification Channels",
                "Escalation Policies",
                "Alert Severity",
            ],
            "visualization": [
                "Dashboard Layout",
                "Metric Widgets",
                "Custom Views",
                "Access Control",
            ],
        },
    },
}


def get_template_type(content: str) -> Optional[str]:
    """Determine the template type based on content analysis."""
    content_lower = content.lower()

    if "api version" in content_lower and "endpoints" in content_lower:
        return "api"
    elif "deployment steps" in content_lower and "rollback" in content_lower:
        return "deployment"
    elif "incident response" in content_lower and "monitoring" in content_lower:
        return "runbook"
    elif "security controls" in content_lower and "access management" in content_lower:
        return "security"
    elif "recovery objectives" in content_lower and "dr strategy" in content_lower:
        return "disaster_recovery"
    elif "metrics and kpis" in content_lower and "alert configuration" in content_lower:
        return "monitoring"

    return None


def verify_section_hierarchy(content: str) -> List[ValidationError]:
    """Verify header hierarchy."""
    errors = []
    lines = content.split("\n")
    current_level = 0
    header_count = {1: 0, 2: 0, 3: 0, 4: 0}

    for i, line in enumerate(lines, 1):
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level == 1:
                header_count[1] += 1
                if header_count[1] > 1:
                    errors.append(
                        ValidationError(
                            message="Multiple h1 headers found in document",
                            file="",
                            line=i,
                            severity=Severity.ERROR,
                            category="header_hierarchy",
                        )
                    )

            if level > current_level + 1:
                errors.append(
                    ValidationError(
                        message=f"Header level skipped from {current_level} to {level}: {line.strip()}",
                        file="",
                        line=i,
                        severity=Severity.ERROR,
                        category="header_hierarchy",
                    )
                )
            elif level > 4:
                errors.append(
                    ValidationError(
                        message=f"Header level {level} too deep: {line.strip()}",
                        file="",
                        line=i,
                        severity=Severity.ERROR,
                        category="header_hierarchy",
                    )
                )

            # Check header format
            header_text = line.strip("#").strip()
            if not header_text:
                errors.append(
                    ValidationError(
                        message="Empty header detected",
                        file="",
                        line=i,
                        severity=Severity.ERROR,
                        category="header_format",
                    )
                )
            elif len(header_text) > 100:
                errors.append(
                    ValidationError(
                        message=f"Header exceeds 100 characters: {header_text[:50]}...",
                        file="",
                        line=i,
                        severity=Severity.ERROR,
                        category="header_format",
                    )
                )

            current_level = level

    return errors


def verify_template_completeness(content: str, template_type: str) -> List[ValidationError]:
    """Verify template completeness with detailed feedback."""
    errors = []
    sections = TEMPLATES[template_type]["required_sections"]

    for section in sections:
        if not re.search(rf"{section}", content, re.MULTILINE | re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing required section: {section.strip()}",
                    file="",
                    line=None,
                    severity=Severity.ERROR,
                    category="template_structure",
                    suggestion=f"Add section '{section.strip()}' with appropriate content",
                )
            )
        else:
            # Check section content
            section_content = re.search(
                rf"{section}.*?\n(.*?)(?=\n#|$)", content, re.DOTALL | re.MULTILINE
            )
            if section_content and len(section_content.group(1).strip()) < 50:
                errors.append(
                    ValidationError(
                        message=f"Section '{section.strip()}' content may be too brief",
                        file="",
                        line=None,
                        severity=Severity.WARNING,
                        category="content_quality",
                        suggestion="Expand section with more detailed information",
                    )
                )

    return errors


def verify_provider_requirements(content: str, provider: str) -> List[ValidationError]:
    """Verify cloud provider specific requirements."""
    errors = []
    provider_reqs = CLOUD_PROVIDERS[provider]

    for category, services in provider_reqs.items():
        found_services = []
        for service in services:
            if re.search(rf"\b{service}\b", content):
                found_services.append(service)

        if not found_services:
            errors.append(
                ValidationError(
                    message=f"No {category} services specified for {provider}",
                    file="",
                    line=None,
                    severity=Severity.ERROR,
                    category="cloud_provider",
                    suggestion=f"Consider adding these {provider} {category} services: {', '.join(services[:3])}",
                )
            )
        elif len(found_services) < 2:
            errors.append(
                ValidationError(
                    message=f"Limited {category} service coverage for {provider}",
                    file="",
                    line=None,
                    severity=Severity.WARNING,
                    category="cloud_provider",
                    suggestion=f"Consider adding more {provider} {category} services like: {', '.join(set(services) - set(found_services))[:3]}",
                )
            )

    return errors


def verify_metadata_fields(content: str, template_type: str) -> List[ValidationError]:
    """Verify required metadata fields are present and valid."""
    errors = []

    # Get template-specific rules
    template_rules = VALIDATION_CONFIG.get("template_types", {}).get(template_type, {})
    metadata_rules = template_rules.get("metadata_fields", {})

    # Check required fields
    required_fields = metadata_rules.get("required", {})
    for field, severity in required_fields.items():
        field_pattern = rf"{field}:\s*(.+)"
        match = re.search(field_pattern, content, re.MULTILINE | re.IGNORECASE)

        if not match:
            errors.append(
                ValidationError(
                    message=f"Missing required metadata field: {field}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.ERROR),
                    category="metadata",
                    suggestion=f"Add field '{field}' with appropriate value",
                )
            )
        else:
            value = match.group(1).strip()
            if not value:
                errors.append(
                    ValidationError(
                        message=f"Empty metadata field: {field}",
                        file="",
                        line=None,
                        severity=getattr(Severity, severity, Severity.ERROR),
                        category="metadata",
                        suggestion=f"Provide a value for field '{field}'",
                    )
                )
            elif field == "Last Review Date":
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    errors.append(
                        ValidationError(
                            message=f"Invalid date format for {field}: {value}",
                            file="",
                            line=None,
                            severity=getattr(Severity, severity, Severity.ERROR),
                            category="metadata",
                            suggestion="Use YYYY-MM-DD format",
                        )
                    )

    # Check recommended fields
    recommended_fields = metadata_rules.get("recommended", {})
    for field, severity in recommended_fields.items():
        field_pattern = rf"{field}:\s*(.+)"
        match = re.search(field_pattern, content, re.MULTILINE | re.IGNORECASE)

        if not match:
            errors.append(
                ValidationError(
                    message=f"Missing recommended metadata field: {field}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.WARNING),
                    category="metadata",
                    suggestion=f"Consider adding field '{field}' for better documentation",
                )
            )

    return errors


def verify_security_requirements(content: str, template_type: str) -> List[ValidationError]:
    """Verify security-related documentation requirements."""
    errors = []

    # Get template-specific rules
    template_rules = VALIDATION_CONFIG.get("template_types", {}).get(template_type, {})
    security_rules = template_rules.get("security_requirements", {})

    # Check required security requirements
    required_reqs = security_rules.get("required", {})
    for req, severity in required_reqs.items():
        if not re.search(rf"{req}", content, re.MULTILINE | re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing required security requirement: {req}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.ERROR),
                    category="security",
                    suggestion=f"Add section '{req}' with appropriate content",
                )
            )

    # Check recommended security requirements
    recommended_reqs = security_rules.get("recommended", {})
    for req, severity in recommended_reqs.items():
        if not re.search(rf"{req}", content, re.MULTILINE | re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing recommended security requirement: {req}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.WARNING),
                    category="security",
                    suggestion=f"Consider adding section '{req}' for better security documentation",
                )
            )

    # Check for sensitive information patterns
    sensitive_patterns = [
        r'(?i)password\s*=\s*[\'"][^\'"]+[\'"]',
        r'(?i)secret\s*=\s*[\'"][^\'"]+[\'"]',
        r'(?i)key\s*=\s*[\'"][^\'"]+[\'"]',
        r'(?i)token\s*=\s*[\'"][^\'"]+[\'"]',
    ]

    for pattern in sensitive_patterns:
        if re.search(pattern, content):
            errors.append(
                ValidationError(
                    message=f"Potential sensitive information found: {pattern}",
                    file="",
                    line=None,
                    severity=Severity.ERROR,  # Always ERROR for sensitive info
                    category="security",
                    suggestion="Remove or encrypt sensitive information",
                )
            )

    return errors


def verify_formatting(content: str) -> List[ValidationError]:
    """Verify general formatting rules."""
    errors = []
    lines = content.split("\n")
    in_code_block = False

    for i, line in enumerate(lines, 1):
        # Check code block language specification
        if line.startswith("```"):
            in_code_block = not in_code_block
            if in_code_block and len(line) > 3:
                if not re.match(r"^```[a-zA-Z]+$", line):
                    errors.append(
                        ValidationError(
                            message=f"Invalid code block language specification: {line}",
                            file="",
                            line=i,
                            severity=Severity.ERROR,
                            category="formatting",
                        )
                    )

        # Check table formatting
        if "|" in line and not in_code_block:
            if not re.match(r"^\|.*\|$", line):
                errors.append(
                    ValidationError(
                        message=f"Invalid table formatting: {line}",
                        file="",
                        line=i,
                        severity=Severity.ERROR,
                        category="formatting",
                    )
                )

            # Check table alignment row
            if re.match(r"^\|[\s-:]+\|$", line):
                if not re.match(r"^\|[-:|\s]+\|$", line):
                    errors.append(
                        ValidationError(
                            message=f"Invalid table alignment row: {line}",
                            file="",
                            line=i,
                            severity=Severity.ERROR,
                            category="formatting",
                        )
                    )

        # Check relative links
        if re.search(r"\[.*\]\((?!http)[^)]+\)", line) and not in_code_block:
            link = re.search(r"\[.*\]\(([^)]+)\)", line).group(1)
            if not link.startswith(("../", "./", "/")):
                errors.append(
                    ValidationError(
                        message=f"Non-relative internal link: {link}",
                        file="",
                        line=i,
                        severity=Severity.WARNING,
                        category="formatting",
                        suggestion="Use relative links",
                    )
                )

    return errors


def verify_operational_readiness(content: str) -> List[ValidationError]:
    """Verify operational readiness documentation."""
    errors = []
    required_operational_sections = [
        "Monitoring",
        "Alerts",
        "Metrics",
        "Logging",
        "Backup",
        "Recovery",
        "Scaling",
    ]

    for section in required_operational_sections:
        if not re.search(rf"\b{section}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing operational section: {section}",
                    file="",
                    line=None,
                    severity=Severity.ERROR,
                    category="operational_readiness",
                    suggestion=f"Add section '{section}' with appropriate content",
                )
            )

    return errors


def verify_cloud_requirements(content: str, template_type: str) -> List[ValidationError]:
    """Verify cloud infrastructure specific requirements."""
    errors = []

    # Get template-specific rules
    template_rules = VALIDATION_CONFIG.get("template_types", {}).get(template_type, {})
    cloud_rules = template_rules.get("cloud_requirements", {})

    # Check required cloud requirements
    required = cloud_rules.get("required", {})

    # Check required services
    services = required.get("services", {})
    for service_type, severity in services.items():
        if not re.search(rf"\b{service_type}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing required cloud service type: {service_type}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.ERROR),
                    category="cloud_requirements",
                    suggestion=f"Add {service_type} service details",
                )
            )

    # Check required operations
    operations = required.get("operations", {})
    for op, severity in operations.items():
        if not re.search(rf"\b{op}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing cloud operations requirement: {op}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.ERROR),
                    category="cloud_requirements",
                    suggestion=f"Add {op} documentation",
                )
            )

    # Check required monitoring
    monitoring = required.get("monitoring", {})
    for monitor, severity in monitoring.items():
        if not re.search(rf"\b{monitor}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing cloud monitoring requirement: {monitor}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.ERROR),
                    category="cloud_requirements",
                    suggestion=f"Add {monitor} documentation",
                )
            )

    # Check recommended requirements
    recommended = cloud_rules.get("recommended", {})

    # Check recommended operations
    rec_operations = recommended.get("operations", {})
    for op, severity in rec_operations.items():
        if not re.search(rf"\b{op}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing recommended cloud operations: {op}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.WARNING),
                    category="cloud_requirements",
                    suggestion=f"Consider adding {op} documentation",
                )
            )

    # Check recommended monitoring
    rec_monitoring = recommended.get("monitoring", {})
    for monitor, severity in rec_monitoring.items():
        if not re.search(rf"\b{monitor}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing recommended cloud monitoring: {monitor}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.WARNING),
                    category="cloud_requirements",
                    suggestion=f"Consider adding {monitor} documentation",
                )
            )

    # Check recommended security
    rec_security = recommended.get("security", {})
    for sec, severity in rec_security.items():
        if not re.search(rf"\b{sec}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing recommended cloud security: {sec}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.WARNING),
                    category="cloud_requirements",
                    suggestion=f"Consider adding {sec} documentation",
                )
            )

    return errors


def verify_cost_requirements(content: str, template_type: str) -> List[ValidationError]:
    """Verify cost-related documentation requirements."""
    errors = []

    # Get template-specific rules
    template_rules = VALIDATION_CONFIG.get("template_types", {}).get(template_type, {})
    cost_rules = template_rules.get("cost_requirements", {})

    # Check required cost elements
    required = cost_rules.get("required", {})
    for element, severity in required.items():
        if not re.search(rf"\b{element}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing required cost element: {element}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.ERROR),
                    category="cost_requirements",
                    suggestion=f"Add {element} documentation",
                )
            )

    # Check recommended cost elements
    recommended = cost_rules.get("recommended", {})
    for element, severity in recommended.items():
        if not re.search(rf"\b{element}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing recommended cost element: {element}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.WARNING),
                    category="cost_requirements",
                    suggestion=f"Consider adding {element} documentation",
                )
            )

    # Check for cost breakdown table
    if "Cost Breakdown" in recommended and not re.search(
        r"\|\s*Cost Category\s*\|", content, re.IGNORECASE
    ):
        errors.append(
            ValidationError(
                message="Missing cost breakdown table",
                file="",
                line=None,
                severity=getattr(Severity, recommended.get("Cost Breakdown", "WARNING")),
                category="cost_requirements",
                suggestion="Add a markdown table with cost categories and estimates",
            )
        )

    return errors


def verify_infrastructure_requirements(content: str, template_type: str) -> List[ValidationError]:
    """Verify infrastructure-specific requirements."""
    errors = []

    # Get template-specific rules
    template_rules = VALIDATION_CONFIG.get("template_types", {}).get(template_type, {})
    infra_rules = template_rules.get("infrastructure_requirements", {})

    # Check required infrastructure elements
    required = infra_rules.get("required", {})
    for element, severity in required.items():
        if not re.search(rf"\b{element}\b", content, re.IGNORECASE):
            errors.append(
                ValidationError(
                    message=f"Missing required infrastructure element: {element}",
                    file="",
                    line=None,
                    severity=getattr(Severity, severity, Severity.ERROR),
                    category="infrastructure_requirements",
                    suggestion=f"Add {element} documentation",
                )
            )

    # Check recommended infrastructure elements
    recommended = infra_rules.get("recommended", {})
    for element, severity in recommended.items():
        if element == "Resource Specifications":
            # Handle resource specifications separately
            for spec_type, spec_severity in severity.items():
                pattern = rf"{spec_type}:\s*\d+[GgMmTt]?[Bb]?(ps)?"
                if not re.search(pattern, content, re.IGNORECASE):
                    errors.append(
                        ValidationError(
                            message=f"Missing recommended resource specification: {spec_type}",
                            file="",
                            line=None,
                            severity=getattr(Severity, spec_severity, Severity.WARNING),
                            category="infrastructure_requirements",
                            suggestion=f"Consider adding {spec_type} specification",
                        )
                    )
        else:
            # Handle regular recommended elements
            if not re.search(rf"\b{element}\b", content, re.IGNORECASE):
                errors.append(
                    ValidationError(
                        message=f"Missing recommended infrastructure element: {element}",
                        file="",
                        line=None,
                        severity=getattr(Severity, severity, Severity.WARNING),
                        category="infrastructure_requirements",
                        suggestion=f"Consider adding {element} documentation",
                    )
                )

    return errors


def get_modified_files() -> Set[str]:
    """Get list of modified markdown files from GitHub environment."""
    if "GITHUB_EVENT_PATH" not in os.environ:
        return set()

    try:
        with open(os.environ["GITHUB_EVENT_PATH"]) as f:
            import json

            event = json.load(f)

        if "pull_request" in event:
            files = event["pull_request"]["changed_files"]
            return {f for f in files if f.endswith(".md")}
    except Exception as e:
        logger.warning(f"Error reading GitHub event: {e}")

    return set()


def validate_file(file_path: str) -> List[ValidationError]:
    """Validate a single documentation file."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
    except Exception as e:
        return [
            ValidationError(
                message=f"Error reading file {file_path}: {e}",
                file=file_path,
                line=None,
                severity=Severity.ERROR,
                category="system",
                suggestion="Check file permissions and format",
            )
        ]

    template_type = get_template_type(content)
    if not template_type:
        return []  # Not a template-based document

    errors = []
    errors.extend(verify_section_hierarchy(content))
    errors.extend(verify_template_completeness(content, template_type))
    errors.extend(verify_metadata_fields(content, template_type))
    errors.extend(verify_formatting(content))
    errors.extend(verify_security_requirements(content, template_type))
    errors.extend(verify_operational_readiness(content))
    errors.extend(verify_cloud_requirements(content, template_type))
    errors.extend(verify_cost_requirements(content, template_type))
    errors.extend(verify_infrastructure_requirements(content, template_type))

    # Provider-specific validation
    for provider in CLOUD_PROVIDERS.keys():
        if re.search(rf"\b{provider}\b", content):
            errors.extend(verify_provider_requirements(content, provider))

    return errors


def generate_error_report(errors: List[ValidationError], output_format: str = "github") -> str:
    """Generate a detailed error report in the specified format."""
    if output_format == "github":
        return "\n".join(error.to_github_error() for error in errors)
    elif output_format == "json":
        return json.dumps([error.to_dict() for error in errors], indent=2)
    else:
        report = []
        categories = {}

        # Group errors by category
        for error in errors:
            if error.category not in categories:
                categories[error.category] = []
            categories[error.category].append(error)

        # Generate report
        for category, category_errors in categories.items():
            report.append(f"\n## {category.replace('_', ' ').title()}")
            for error in category_errors:
                report.append(f"\n### {error.severity.value.upper()}: {error.message}")
                if error.suggestion:
                    report.append(f"Suggestion: {error.suggestion}")
                if error.line:
                    report.append(f"Line: {error.line}")
                report.append("")

        return "\n".join(report)


def format_error(template_path: str, error_msg: str) -> str:
    """Format error message with template path."""
    return f"Error in template {template_path}: {error_msg}"


def format_warning(template_path: str, warning_msg: str) -> str:
    """Format warning message with template path."""
    return f"Warning for template {template_path}: {warning_msg}"


def main() -> Tuple[int, List[ValidationError]]:
    """Validate documentation templates with enhanced error reporting."""
    all_errors = []
    modified_files = get_modified_files()

    # Determine which files to check
    files_to_check = (
        modified_files
        if modified_files
        else [
            f
            for f in Path(".").rglob("*.md")
            if "node_modules" not in str(f) and ".git" not in str(f)
        ]
    )

    # Check each file
    for file_path in files_to_check:
        file_errors = validate_file(file_path)
        for error in file_errors:
            error.file = file_path
        all_errors.extend(file_errors)

    return len(all_errors), all_errors


if __name__ == "__main__":
    error_count, errors = main()

    # Generate reports in different formats
    print("\n=== GitHub Actions Format ===")
    print(generate_error_report(errors, "github"))

    print("\n=== Detailed Report ===")
    print(generate_error_report(errors, "detailed"))

    if error_count > 0:
        # Save detailed report to file
        report_path = Path("validation-report.json")
        with open(report_path, "w") as f:
            f.write(generate_error_report(errors, "json"))
        print(f"\nDetailed report saved to: {report_path}")
        sys.exit(1)

    print("\nValidation completed successfully!")
    sys.exit(0)
