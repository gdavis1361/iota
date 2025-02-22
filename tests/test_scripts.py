"""Tests for IOTA automation scripts."""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pytest

from server.core.config_schema import SchemaVersion


# Test fixtures
@pytest.fixture
def temp_git_dir(tmp_path):
    """Create a temporary Git directory structure."""
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    # Create git-hooks directory with pre-commit hook
    script_hooks_dir = tmp_path / "scripts" / "git-hooks"
    script_hooks_dir.mkdir(parents=True)

    # Create pre-commit hook
    pre_commit = script_hooks_dir / "pre-commit"
    pre_commit.write_text(
        """#!/bin/bash
echo "Running pre-commit hook..."
exit 0
"""
    )
    pre_commit.chmod(0o755)

    return tmp_path


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary validation rules config."""
    config = {
        "version": "1.0.0",
        "template_types": {
            "runbook": {
                "metadata_fields": {
                    "required": ["purpose", "owner"],
                    "recommended": ["cost_center"],
                }
            }
        },
    }
    config_file = tmp_path / "validation_rules.json"
    with open(config_file, "w") as f:
        json.dump(config, f)
    return config_file


@pytest.fixture
def temp_changelog(tmp_path):
    """Create a temporary changelog file."""
    content = """# Changelog

## [1.0.0] - 2025-02-21

### Added
- Initial release
"""
    changelog_file = tmp_path / "CHANGELOG.md"
    with open(changelog_file, "w") as f:
        f.write(content)
    return changelog_file


def test_git_hook_installation(temp_git_dir):
    """Test Git hook installation."""
    # Copy hook installation script to temp dir
    script_path = Path(__file__).parent.parent / "scripts" / "install_git_hooks.sh"
    temp_script = temp_git_dir / "install_git_hooks.sh"
    shutil.copy(script_path, temp_script)
    temp_script.chmod(0o755)  # Make executable

    # Run installation
    result = subprocess.run(
        ["./install_git_hooks.sh"], cwd=temp_git_dir, capture_output=True, text=True
    )

    # Verify installation
    hook_path = temp_git_dir / ".git" / "hooks" / "pre-commit"
    assert hook_path.exists(), "Pre-commit hook should be installed"
    assert os.access(hook_path, os.X_OK), "Hook should be executable"
    assert "Git hooks installed successfully" in result.stdout


def test_version_bump(temp_config):
    """Test version bump utility."""
    from scripts.bump_version import SchemaVersion, bump_version

    # Test patch bump
    current = SchemaVersion(major=1, minor=0, patch=0)
    new_version = bump_version(current, "patch")
    assert str(new_version) == "1.0.1"

    # Test minor bump
    new_version = bump_version(current, "minor")
    assert str(new_version) == "1.1.0"

    # Test major bump
    new_version = bump_version(current, "major")
    assert str(new_version) == "2.0.0"


def test_changelog_generation(temp_changelog):
    """Test changelog generation."""
    from scripts.update_changelog import categorize_changes, update_changelog

    changes = {"Added": ["New feature X", "Support for Y"], "Fixed": ["Bug in Z"]}

    # Update changelog
    update_changelog("1.1.0", changes, changelog_path=temp_changelog)

    # Verify update
    with open(temp_changelog) as f:
        content = f.read()

    assert "[1.1.0]" in content
    assert "New feature X" in content
    assert "Bug in Z" in content


def test_error_scenarios(temp_git_dir):
    """Test various error scenarios and edge cases."""
    # Test invalid version string
    with pytest.raises(ValueError) as exc_info:
        from scripts.bump_version import parse_version

        parse_version("invalid_version")
    assert "invalid version" in str(exc_info.value).lower()

    # Test missing git hooks directory
    script_path = Path(__file__).parent.parent / "scripts" / "install_git_hooks.sh"
    temp_script = temp_git_dir / "install_git_hooks.sh"
    shutil.copy(script_path, temp_script)
    temp_script.chmod(0o755)

    # Create an empty directory without .git
    empty_dir = temp_git_dir / "empty"
    empty_dir.mkdir()

    result = subprocess.run(
        ["../install_git_hooks.sh"], cwd=empty_dir, capture_output=True, text=True
    )
    assert result.returncode != 0, "Should fail when .git directory is missing"
    assert "not found" in result.stdout.lower()


def test_integration_workflow(temp_git_dir):
    """Test the entire workflow integration."""
    # Set up git repo
    subprocess.run(["git", "init"], cwd=temp_git_dir)

    # Install hooks
    script_path = Path(__file__).parent.parent / "scripts" / "install_git_hooks.sh"
    temp_script = temp_git_dir / "install_git_hooks.sh"
    shutil.copy(script_path, temp_script)
    temp_script.chmod(0o755)

    result = subprocess.run(
        ["./install_git_hooks.sh"], cwd=temp_git_dir, capture_output=True, text=True
    )
    assert result.returncode == 0, "Hook installation should succeed"

    # Verify hook installation
    hook_path = temp_git_dir / ".git" / "hooks" / "pre-commit"
    assert hook_path.exists(), "Pre-commit hook should be installed"
    assert os.access(hook_path, os.X_OK), "Hook should be executable"

    # Test version bump
    from scripts.bump_version import bump_version

    old_version = "1.0.0"
    new_version = bump_version(old_version, "minor")
    assert new_version == "1.1.0"

    # Test changelog generation
    from scripts.update_changelog import update_changelog

    changelog_path = temp_git_dir / "CHANGELOG.md"
    changes = ["Added new feature", "Fixed bug"]
    update_changelog(new_version, changes=changes, changelog_path=changelog_path)
    assert changelog_path.exists()
    content = changelog_path.read_text()
    assert new_version in content
    assert "Added new feature" in content


def test_version_compatibility():
    """Test version compatibility checks."""
    from scripts.bump_version import SchemaVersion

    v1_0_0 = SchemaVersion(major=1, minor=0, patch=0)
    v1_1_0 = SchemaVersion(major=1, minor=1, patch=0)
    v2_0_0 = SchemaVersion(major=2, minor=0, patch=0)

    assert v1_1_0.is_compatible_with(v1_0_0)
    assert not v2_0_0.is_compatible_with(v1_0_0)
    assert not v1_0_0.is_compatible_with(v2_0_0)
