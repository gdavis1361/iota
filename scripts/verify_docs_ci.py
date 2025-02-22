#!/usr/bin/env python3
"""CI-specific documentation verification script.

This script extends verify_docs.py with CI-specific functionality:
1. Checks only modified files in a PR
2. Provides GitHub-compatible output formatting
3. Includes detailed error information for PR comments
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Set, Tuple

from verify_docs import REQUIRED_DOCS, check_doc_exists, verify_doc_references, verify_header_format

logger = logging.getLogger(__name__)


def get_modified_files() -> Set[str]:
    """Get list of modified markdown files from GitHub environment."""
    try:
        with open(os.getenv("GITHUB_EVENT_PATH", "")) as f:
            event = json.load(f)

        if "pull_request" in event:
            # For pull requests, check modified files
            files = event["pull_request"]["changed_files"]
            return {f for f in files if f.endswith(".md")}
    except json.JSONDecodeError as e:
        logger.error(f"Error reading GitHub event: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    return set()


def format_error(error: str) -> str:
    """Format error message for GitHub Actions output."""
    if ":" not in error:
        return f"::error::{error}"

    file_info, message = error.split(":", 1)
    if "line" in file_info.lower():
        # Extract file and line information
        try:
            file_path = file_info.split("in")[1].split("(")[0].strip()
            line_num = file_info.split("line")[1].split(")")[0].strip()
            return f"::error file={file_path},line={line_num}::{message.strip()}"
        except Exception as e:
            logger.error(f"Error parsing file info: {e}")

    return f"::error file={file_info.strip()}::{message.strip()}"


def main() -> Tuple[int, list[str]]:
    """Verify documentation in CI environment."""
    errors = []
    modified_files = get_modified_files()

    # Always check required docs exist
    for doc_path, doc_name in REQUIRED_DOCS.items():
        if not check_doc_exists(doc_path):
            errors.append(f"Missing required document: {doc_name} ({doc_path})")

    # Determine which files to check
    files_to_check = modified_files if modified_files else REQUIRED_DOCS.keys()

    # Check each file
    for doc_path in files_to_check:
        if Path(doc_path).exists() and doc_path.endswith(".md"):
            errors.extend(verify_doc_references(doc_path))
            errors.extend(verify_header_format(doc_path))

    # Format errors for GitHub Actions
    formatted_errors = [format_error(e) for e in errors]

    return len(formatted_errors), formatted_errors


if __name__ == "__main__":
    error_count, error_list = main()

    # Output errors in GitHub Actions format
    for error in error_list:
        print(error)

    # Set status
    if error_count > 0:
        print(f"\n{error_count} documentation errors found")
        sys.exit(error_count)
    else:
        print("\nAll documentation verified successfully!")
        sys.exit(0)
