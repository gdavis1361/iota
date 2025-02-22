#!/usr/bin/env python3
"""
Version bump utility for IOTA documentation validation framework.
Handles semantic version updates and changelog management.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Union

from server.core.config_schema import SchemaVersion
from server.core.logging_config import setup_logger
from server.core.monitor import monitor

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.append(project_root)

# Configure logging
logger = setup_logger("iota.version")

VALIDATION_RULES_PATH = Path(project_root) / "config" / "validation_rules.json"
CHANGELOG_PATH = Path(project_root) / "CHANGELOG.md"


class VersionType(str, Enum):
    """Type of version bump."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


def parse_version(version_str: str) -> SchemaVersion:
    """Parse version string into SchemaVersion object."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
    if not match:
        raise ValueError(f"Invalid version string: {version_str}")

    major, minor, patch = map(int, match.groups())
    if major < 0 or minor < 0 or patch < 0:
        raise ValueError("Version numbers cannot be negative")

    return SchemaVersion(major=major, minor=minor, patch=patch)


def load_current_version() -> SchemaVersion:
    """Load the current version from validation_rules.json."""
    try:
        with open(VALIDATION_RULES_PATH) as f:
            config = json.load(f)
        version_str = config.get("version", "0.0.0")
        return SchemaVersion.from_str(version_str)
    except FileNotFoundError:
        logger.error("validation_rules.json not found")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in validation_rules.json")
        sys.exit(1)
    except Exception:
        logger.error("Failed to load current version")
        raise


def bump_version(current: Union[str, SchemaVersion], bump_type: str) -> str:
    """
    Bump version according to semantic versioning rules.

    Args:
        current: Current version (string or SchemaVersion)
        bump_type: Type of version bump (major, minor, or patch)

    Returns:
        New version string
    """
    start_time = time.time()
    had_error = False

    try:
        if isinstance(current, str):
            current = parse_version(current)

        bump_type = bump_type.lower()
        if bump_type == "major":
            new_version = SchemaVersion(major=current.major + 1, minor=0, patch=0)
        elif bump_type == "minor":
            new_version = SchemaVersion(major=current.major, minor=current.minor + 1, patch=0)
        elif bump_type == "patch":
            new_version = SchemaVersion(
                major=current.major, minor=current.minor, patch=current.patch + 1
            )
        else:
            had_error = True
            raise ValueError(f"Invalid bump type: {bump_type}")

        return str(new_version)
    except Exception:
        had_error = True
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        monitor.record_version_bump(duration_ms, had_error)


def update_validation_rules(new_version: SchemaVersion) -> None:
    """Update the version in validation_rules.json."""
    try:
        with open(VALIDATION_RULES_PATH) as f:
            config = json.load(f)

        config["version"] = str(new_version)

        with open(VALIDATION_RULES_PATH, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")  # Add newline at EOF

        logger.info(f"Updated validation_rules.json to version {new_version}")
    except Exception:
        logger.error("Failed to update validation rules")
        raise


def update_changelog(new_version: SchemaVersion, changes: str) -> None:
    """Update CHANGELOG.md with new version entry."""
    now = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"\n## [{str(new_version)}] - {now}\n\n{changes}\n"
    try:
        with open(CHANGELOG_PATH, "r") as f:
            content = f.read()
        header_end = content.find("\n## ")
        if header_end == -1:
            header_end = len(content)
        content = content[:header_end] + new_entry + content[header_end:]
        with open(CHANGELOG_PATH, "w") as f:
            f.write(content)
    except Exception:
        logger.error("Failed to update changelog")
        raise


def main():
    parser = argparse.ArgumentParser(description="Bump version of the validation framework")
    parser.add_argument(
        "bump_type", choices=["major", "minor", "patch"], help="Type of version bump to perform"
    )
    parser.add_argument("--changes", help="Changes to add to the changelog", required=True)

    args = parser.parse_args()

    try:
        current_version = load_current_version()
        new_version = bump_version(current_version, args.bump_type)

        logger.info(f"Bumping version: {current_version} -> {new_version}")

        update_validation_rules(parse_version(new_version))
        update_changelog(parse_version(new_version), args.changes)

        logger.info("Version bump completed successfully")
    except Exception:
        logger.error("Version bump failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
