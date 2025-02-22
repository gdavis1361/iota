#!/usr/bin/env python3
"""Verify spelling in documentation files."""

import logging
import os
import re
import subprocess
import sys
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)


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
        print(f"::warning::Error reading GitHub event: {e}")

    return set()


def run_codespell(files: Set[str] = None) -> List[str]:
    """Run codespell and capture results."""
    cmd = [
        "codespell",
        "--check-hidden",
        "--ignore-words=.codespell-ignore",
        "--exclude-file=.gitignore",
        "--quiet-level=2",
        "--context=2",
    ]

    if files:
        cmd.extend(files)
    else:
        cmd.extend(["--skip=.git,node_modules,build,dist", "."])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode > 0:
            return parse_codespell_output(result.stderr)
    except Exception as e:
        return [f"Error running codespell: {e}"]

    return []


def parse_codespell_output(output: str) -> List[str]:
    """Parse and format codespell output for GitHub Actions."""
    errors = []

    for line in output.splitlines():
        if not line or line.startswith("Using"):
            continue

        try:
            # Parse codespell output format
            file_info, error_info = line.split(":", 1)
            context_match = re.search(r"Context: \"(.+?)\"", error_info)
            suggestion_match = re.search(r"=>\s*(.+?)$", error_info)

            if context_match and suggestion_match:
                context = context_match.group(1)
                suggestion = suggestion_match.group(1)

                # Format for GitHub Actions
                error_msg = (
                    f"::error file={file_info}::"
                    f"Spelling error in context: '{context}'. "
                    f"Suggestion: {suggestion}"
                )
                errors.append(error_msg)
        except Exception:
            errors.append(f"::error::{line}")

    return errors


def main() -> Tuple[int, List[str]]:
    """Run spell check verification."""
    modified_files = get_modified_files()
    errors = run_codespell(modified_files if modified_files else None)

    return len(errors), errors


if __name__ == "__main__":
    error_count, error_list = main()

    # Output errors
    for error in error_list:
        print(error)

    if error_count > 0:
        print(f"\n{error_count} spelling errors found")
        sys.exit(error_count)
    else:
        print("\nSpell check passed successfully!")
        sys.exit(0)
