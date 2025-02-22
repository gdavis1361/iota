"""Validation handler for IOTA templates and configurations."""

from pathlib import Path
from typing import Dict, List, Optional, Union

from .config_schema import SchemaVersion, ValidationRulesSchema, ValidationSeverity
from .logging_config import LogLevel, setup_logger

logger = setup_logger("iota.validation")


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid: bool = True

    def add_error(self, message: str) -> None:
        """Add an error message and mark validation as failed."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def __str__(self) -> str:
        """Format validation results as string."""
        parts = []
        if self.errors:
            parts.append("Errors:")
            parts.extend(f"  - {error}" for error in self.errors)
        if self.warnings:
            parts.append("Warnings:")
            parts.extend(f"  - {warning}" for warning in self.warnings)
        if not parts:
            parts.append("Validation passed with no issues.")
        return "\n".join(parts)


class ValidationHandler:
    """Handles validation of templates and configurations."""

    def __init__(self, rules_file: Union[str, Path]):
        """
        Initialize validation handler with rules file.

        Args:
            rules_file: Path to validation rules JSON file
        """
        self.rules_file = Path(rules_file)
        self.rules = self._load_rules()
        logger.info(f"Loaded validation rules version {self.rules.version}")

    def _load_rules(self) -> ValidationRulesSchema:
        """Load and parse validation rules from file."""
        try:
            with open(self.rules_file) as f:
                data = json.load(f)
            return ValidationRulesSchema(**data)
        except Exception as e:
            logger.error(f"Failed to load validation rules: {e}")
            raise

    def validate_template(
        self, template_type: str, content: Dict, version: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate a template against the rules.

        Args:
            template_type: Type of template (e.g., 'runbook')
            content: Template content as dictionary
            version: Optional version to validate against

        Returns:
            ValidationResult containing any errors or warnings
        """
        result = ValidationResult()

        # Version compatibility check
        if version:
            template_version = SchemaVersion.from_str(version)
            rules_version = SchemaVersion.from_str(str(self.rules.version))
            if not template_version.is_compatible_with(rules_version):
                result.add_error(
                    f"Template version {version} is not compatible with "
                    f"rules version {self.rules.version}"
                )
                return result

        # Get rules for template type
        type_rules = self.rules.template_types.get(template_type)
        if not type_rules:
            result.add_error(f"Unknown template type: {template_type}")
            return result

        # Check required fields
        for field in type_rules.metadata_fields.required:
            if field not in content:
                result.add_error(f"Missing required field: {field}")
            elif not content[field]:
                result.add_error(f"Required field '{field}' is empty")

        # Check recommended fields
        for field in type_rules.metadata_fields.recommended:
            if field not in content:
                result.add_warning(f"Missing recommended field: {field}")
            elif not content[field]:
                result.add_warning(f"Recommended field '{field}' is empty")

        return result

    def validate_config(self, config: Dict) -> ValidationResult:
        """
        Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate

        Returns:
            ValidationResult containing any errors or warnings
        """
        result = ValidationResult()

        try:
            ValidationRulesSchema(**config)
        except Exception as e:
            result.add_error(f"Configuration validation failed: {e}")

        return result
