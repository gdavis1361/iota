#!/usr/bin/env python3
"""Verify documentation completeness, cross-references, and formatting."""

import logging
import re
import sys
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

REQUIRED_DOCS = {
    # Development docs
    "docs/contributing.md": "Contributing Guidelines",
    "docs/pre-commit.md": "Pre-commit Setup",
    "docs/development.md": "Development Setup",
    # Architecture docs
    "docs/adr/0001-configuration-management.md": "Configuration Management ADR",
    "docs/migration/001-module-consolidation.md": "Module Consolidation Guide",
    # Security docs
    "tests/scripts/SECURITY.md": "Security Guidelines",
    "docs/authentication.md": "Authentication Guide",
    "docs/authorization.md": "Authorization Guide",
    # Testing docs
    "docs/testing.md": "Testing Guide",
    "tests/performance/README.md": "Performance Testing",
    "tests/integration/README.md": "Integration Testing",
    # Operations docs
    "docs/operations/monitoring.md": "Monitoring Guide",
    "docs/operations/rate_limiter.md": "Rate Limiting Guide",
    "docs/operations/alerts.md": "Alerts Guide",
}


def check_doc_exists(doc_path: str) -> bool:
    """Check if a documentation file exists."""
    return Path(doc_path).exists()


def extract_doc_links(content: str) -> List[Tuple[str, int]]:
    """Extract markdown links and their line numbers from content.

    Returns:
        List of tuples containing (link, line_number)
    """
    links = []
    for line_num, line in enumerate(content.split("\n"), 1):
        start = 0
        while True:
            # Find next markdown link
            link_start = line.find("](", start)
            if link_start == -1:
                break

            link_end = line.find(")", link_start)
            if link_end == -1:
                break

            # Extract link URL
            link = line[link_start + 2 : link_end]
            if not link.startswith(("http://", "https://", "#")):
                links.append((link, line_num))

            start = link_end + 1

    return links


def verify_doc_references(doc_path: str) -> List[str]:
    """Verify all document references in a file exist and use relative paths."""
    errors = []
    try:
        content = Path(doc_path).read_text()
        links = extract_doc_links(content)

        for link, line_num in links:
            # Check for absolute paths
            if link.startswith("/"):
                errors.append(f"Absolute path in {doc_path} (line {line_num}): {link}")
                continue

            # Verify link exists
            full_path = str(Path(doc_path).parent / link)
            if not Path(full_path).exists():
                errors.append(f"Broken link in {doc_path} (line {line_num}): {link}")

    except Exception as e:
        errors.append(f"Error checking {doc_path}: {str(e)}")

    return errors


def verify_header_format(doc_path: str) -> List[str]:
    """Verify markdown header formatting follows style guide.

    Rules:
    1. Use ATX-style headers (# prefix)
    2. Single space after #
    3. No skipped levels
    4. Maximum depth of 4 levels
    5. First header must be level 1
    6. Only one level 1 header per document
    """
    errors = []
    try:
        content = Path(doc_path).read_text()
        lines = content.split("\n")
        current_level = 0
        h1_count = 0
        in_code_block = False

        for line_num, line in enumerate(lines, 1):
            # Skip code blocks
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # Check for headers
            if line.strip().startswith("#"):
                # Count # symbols at start
                level = len(re.match(r"^#+", line.strip()).group())

                # Check format rules
                if not re.match(r"^#{1,4} \w", line):
                    errors.append(
                        f"Invalid header format in {doc_path} (line {line_num}): "
                        f"Headers must have a single space after # and content after the space"
                    )

                # Check maximum depth
                if level > 4:
                    errors.append(
                        f"Header too deep in {doc_path} (line {line_num}): "
                        f"Maximum depth is 4, found depth {level}"
                    )

                # Check for skipped levels
                if current_level > 0 and level > current_level + 1:
                    errors.append(
                        f"Skipped header level in {doc_path} (line {line_num}): "
                        f"Went from level {current_level} to {level}"
                    )

                # Track h1 headers
                if level == 1:
                    h1_count += 1
                    if h1_count > 1:
                        errors.append(
                            f"Multiple h1 headers in {doc_path} (line {line_num}): "
                            f"Only one h1 header allowed per document"
                        )

                current_level = level

        # Check if document has an h1
        if h1_count == 0:
            errors.append(
                f"No h1 header found in {doc_path}: Document must start with a level 1 header"
            )

    except Exception as e:
        errors.append(f"Error checking headers in {doc_path}: {str(e)}")

    return errors


def check_links(content: str, doc_file: str) -> List[str]:
    """Check for broken links in a markdown file."""
    errors = []
    links = extract_doc_links(content)

    for link, line_num in links:
        full_path = str(Path(doc_file).parent / link)
        if not Path(full_path).exists():
            errors.append(f"Broken link in {doc_file} (line {line_num}): {link}")

    return errors


def check_code_blocks(content: str, doc_file: str) -> List[str]:
    """Check for code blocks in a markdown file."""
    errors = []
    lines = content.split("\n")
    in_code_block = False

    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            in_code_block = not in_code_block
            if in_code_block:
                # Check code block language
                if len(line) > 3:
                    language = line[3:].strip()
                    if language not in ["python", "bash", "json", "yaml"]:
                        errors.append(f"Unsupported code block language at line {i}: {language}")

    return errors


def verify_docs(docs_dir: Path) -> List[str]:
    """Verify documentation files."""
    errors = []
    try:
        for doc_file in docs_dir.rglob("*.md"):
            with open(doc_file) as f:
                content = f.read()

            # Check for broken links
            link_errors = check_links(content, doc_file)
            if link_errors:
                errors.extend(link_errors)

            # Check for code blocks
            code_errors = check_code_blocks(content, doc_file)
            if code_errors:
                errors.extend(code_errors)

        return errors
    except Exception as e:
        logger.error(f"Failed to verify docs: {e}")
        return [f"Error validating documentation: {str(e)}"]


def main() -> Tuple[int, List[str]]:
    """Verify documentation completeness and formatting."""
    errors = []

    # Check required docs exist
    for doc_path, doc_name in REQUIRED_DOCS.items():
        if not check_doc_exists(doc_path):
            errors.append(f"Missing required document: {doc_name} ({doc_path})")

    # Check cross-references and formatting in existing docs
    for doc_path in REQUIRED_DOCS:
        if check_doc_exists(doc_path):
            errors.extend(verify_doc_references(doc_path))
            errors.extend(verify_header_format(doc_path))

    return len(errors), errors


if __name__ == "__main__":
    error_count, error_list = main()
    if error_list:
        print("\nDocumentation Verification Errors:")
        for error in error_list:
            print(f"- {error}")
        sys.exit(error_count)
    else:
        print("\nAll documentation verified successfully!")
        sys.exit(0)
