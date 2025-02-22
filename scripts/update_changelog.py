#!/usr/bin/env python3
"""
Changelog update utility for IOTA documentation validation framework.
"""

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import git

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

from server.core.logging_config import setup_logger  # noqa: E402
from server.core.monitor import monitor  # noqa: E402

logger = setup_logger("iota.changelog")


def update_changelog(
    version: str,
    changes: Union[List[str], Dict[str, List[str]]],
    changelog_path: Optional[Path] = None,
) -> None:
    """
    Update CHANGELOG.md with new version entry.

    Args:
        version: Version string (e.g., "1.0.0")
        changes: List of changes or dictionary of change categories and their entries
        changelog_path: Optional path to changelog file. If None, uses default
    """
    start_time = time.time()
    had_error = False

    try:
        if changelog_path is None:
            changelog_path = Path(project_root) / "CHANGELOG.md"

        if not changelog_path.exists():
            changelog_path.write_text("# Changelog\n\n")

        content = changelog_path.read_text()

        # Create new version entry
        today = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"\n## [{version}] - {today}\n\n"

        # Handle both list and dict inputs
        if isinstance(changes, list):
            new_entry += "### Changes\n\n"
            for change in changes:
                new_entry += f"- {change}\n"
        else:
            for category, entries in changes.items():
                new_entry += f"### {category}\n\n"
                for entry in entries:
                    new_entry += f"- {entry}\n"
                new_entry += "\n"

        # Insert new entry after header
        if "# Changelog" in content:
            header_end = content.index("# Changelog") + len("# Changelog")
            content = content[:header_end] + new_entry + content[header_end:]
        else:
            content = "# Changelog\n" + new_entry + content

        changelog_path.write_text(content)
        logger.info(f"Updated changelog with version {version}")

    except Exception as e:
        had_error = True
        logger.error(f"Failed to update changelog: {e}")
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        monitor.record_changelog_update(duration_ms, had_error)


def categorize_changes(commit_messages: List[str]) -> Dict[str, List[str]]:
    """
    Categorize commit messages into change types.

    Args:
        commit_messages: List of commit messages

    Returns:
        Dictionary mapping categories to lists of changes
    """
    categories = {
        "Added": [],
        "Changed": [],
        "Deprecated": [],
        "Removed": [],
        "Fixed": [],
        "Security": [],
    }

    for msg in commit_messages:
        # Simple categorization based on first word
        first_word = msg.split()[0].lower()
        if "add" in first_word:
            categories["Added"].append(msg)
        elif "change" in first_word or "update" in first_word:
            categories["Changed"].append(msg)
        elif "deprecate" in first_word:
            categories["Deprecated"].append(msg)
        elif "remove" in first_word or "delete" in first_word:
            categories["Removed"].append(msg)
        elif "fix" in first_word:
            categories["Fixed"].append(msg)
        elif "security" in first_word:
            categories["Security"].append(msg)
        else:
            categories["Changed"].append(msg)

    return categories


def get_git_commits(from_ref: str, to_ref: str = "HEAD") -> List[str]:
    """Get Git commits between two refs."""
    try:
        cmd = ["git", "log", f"{from_ref}..{to_ref}", "--pretty=format:%s%n%b"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.split("\n")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get Git commits: {e}")
        return []


def parse_commit_message(message: str) -> Optional[Tuple[str, str, str]]:
    """Parse conventional commit message."""
    pattern = r"^(\w+)(?:\(([^)]+)\))?: (.+)$"
    match = re.match(pattern, message)
    if match:
        return match.groups()
    return None


def get_latest_tag() -> Optional[str]:
    """Get the latest git tag."""
    try:
        repo = git.Repo()
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
        return str(tags[-1]) if tags else None
    except Exception as e:
        print(f"Error getting latest tag: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Update CHANGELOG.md with new version entry")
    parser.add_argument("version", help="Version number (e.g., 1.0.0)")
    parser.add_argument(
        "--from-ref", help="Starting Git ref (default: previous tag)", default="HEAD^"
    )
    parser.add_argument("--to-ref", help="Ending Git ref (default: HEAD)", default="HEAD")

    args = parser.parse_args()

    try:
        commits = get_git_commits(args.from_ref, args.to_ref)
        changes = categorize_changes(commits)

        if changes:
            update_changelog(args.version, changes)
            logger.info("Changelog updated successfully")
        else:
            logger.warning("No changes found to add to changelog")
    except Exception as e:
        logger.error(f"Failed to update changelog: {e}")
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update CHANGELOG.md with new version entry")
    parser.add_argument("version", help="Version number (e.g., 1.0.0)")
    args = parser.parse_args()

    # Example changes - in practice, these would come from git log
    example_changes = {"Added": ["New feature X", "Support for Y"], "Fixed": ["Bug in Z"]}

    update_changelog(args.version, example_changes)
