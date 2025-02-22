#!/usr/bin/env python3
"""Validate documentation files."""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import markdown
from rich.console import Console
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
console = Console()


class ValidationError:
    """Represents a documentation validation error."""

    def __init__(self, file: str, line: int, message: str, severity: str):
        """Initialize validation error."""
        self.file = file
        self.line = line
        self.message = message
        self.severity = severity  # 'error' or 'warning'


class DocValidator:
    """Documentation validator."""

    def __init__(self, root_dir: Path):
        """Initialize validator with project root directory."""
        self.root_dir = root_dir
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        logger.info("Starting documentation validation...")

        # Track validation status
        is_valid = True

        try:
            # Check markdown syntax
            if not self.validate_markdown():
                is_valid = False

            # Check internal links
            if not self.validate_internal_links():
                is_valid = False

            # Check code examples
            if not self.validate_code_examples():
                is_valid = False

            # Check cross-references
            if not self.validate_cross_references():
                is_valid = False

            # Check formatting consistency
            if not self.validate_formatting():
                is_valid = False

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return False

        # Report results
        self._report_results()

        return is_valid

    def validate_markdown(self) -> bool:
        """Validate markdown syntax in all documentation files."""
        logger.info("Validating markdown syntax...")

        valid = True
        for doc_file in self.root_dir.rglob("*.md"):
            try:
                content = doc_file.read_text()
                markdown.markdown(content)
            except Exception as e:
                self.errors.append(
                    ValidationError(
                        file=str(doc_file),
                        line=self._get_error_line(str(e)),
                        message=f"Invalid markdown: {str(e)}",
                        severity="error",
                    )
                )
                valid = False

        return valid

    def validate_internal_links(self) -> bool:
        """Validate internal documentation links."""
        logger.info("Validating internal links...")

        valid = True
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        for doc_file in self.root_dir.rglob("*.md"):
            content = doc_file.read_text()
            for line_num, line in enumerate(content.splitlines(), 1):
                for match in link_pattern.finditer(line):
                    link_text, link_target = match.groups()

                    # Skip external links
                    if link_target.startswith(("http://", "https://")):
                        continue

                    # Validate internal link
                    target_path = doc_file.parent / link_target
                    if not target_path.exists():
                        self.errors.append(
                            ValidationError(
                                file=str(doc_file),
                                line=line_num,
                                message=f"Broken internal link: {link_target}",
                                severity="error",
                            )
                        )
                        valid = False

        return valid

    def validate_code_examples(self) -> bool:
        """Validate code examples in documentation."""
        logger.info("Validating code examples...")

        valid = True
        code_block_pattern = re.compile(r"```(\w+)?\n(.*?)\n```", re.DOTALL)

        for doc_file in self.root_dir.rglob("*.md"):
            content = doc_file.read_text()
            for match in code_block_pattern.finditer(content):
                lang, code = match.groups()
                if lang in ("python", "py"):
                    try:
                        compile(code, "<string>", "exec")
                    except SyntaxError as e:
                        self.errors.append(
                            ValidationError(
                                file=str(doc_file),
                                line=self._get_code_block_line(content, match.start()),
                                message=f"Invalid Python syntax: {str(e)}",
                                severity="error",
                            )
                        )
                        valid = False

        return valid

    def validate_cross_references(self) -> bool:
        """Validate cross-references between documentation files."""
        logger.info("Validating cross-references...")

        valid = True
        ref_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")

        # Build reference map
        references: Dict[str, Set[str]] = {}
        for doc_file in self.root_dir.rglob("*.md"):
            content = doc_file.read_text()
            references[str(doc_file)] = set()

            for match in ref_pattern.finditer(content):
                ref_file = match.group(2)
                if not ref_file.startswith(("http://", "https://")):
                    references[str(doc_file)].add(ref_file)

        # Validate references
        for source_file, refs in references.items():
            for ref in refs:
                ref_path = Path(source_file).parent / ref
                if not ref_path.exists():
                    self.errors.append(
                        ValidationError(
                            file=source_file,
                            line=0,  # Would need more complex parsing for exact line
                            message=f"Missing cross-reference: {ref}",
                            severity="error",
                        )
                    )
                    valid = False

        return valid

    def validate_formatting(self) -> bool:
        """Validate consistent formatting."""
        logger.info("Validating formatting consistency...")

        valid = True

        # Common formatting issues
        trailing_space_pattern = re.compile(r"[ \t]+$")
        multiple_blank_lines_pattern = re.compile(r"\n{3,}")

        for doc_file in self.root_dir.rglob("*.md"):
            content = doc_file.read_text()

            # Check for trailing whitespace
            for line_num, line in enumerate(content.splitlines(), 1):
                if trailing_space_pattern.search(line):
                    self.warnings.append(
                        ValidationError(
                            file=str(doc_file),
                            line=line_num,
                            message="Line contains trailing whitespace",
                            severity="warning",
                        )
                    )

            # Check for multiple blank lines
            if multiple_blank_lines_pattern.search(content):
                self.warnings.append(
                    ValidationError(
                        file=str(doc_file),
                        line=0,
                        message="File contains multiple consecutive blank lines",
                        severity="warning",
                    )
                )

        return valid

    def _get_error_line(self, error_msg: str) -> int:
        """Extract line number from error message."""
        # Implementation depends on error message format
        return 0

    def _get_code_block_line(self, content: str, pos: int) -> int:
        """Get line number for a position in the content."""
        return content[:pos].count("\n") + 1

    def _report_results(self) -> None:
        """Report validation results."""
        if not self.errors and not self.warnings:
            console.print("[green]Documentation validation passed![/green]")
            return

        if self.errors:
            console.print("\n[red]Errors:[/red]")
            for error in self.errors:
                console.print(f"[red]ERROR[/red] {error.file}:{error.line} - {error.message}")

        if self.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in self.warnings:
                console.print(
                    f"[yellow]WARNING[/yellow] {warning.file}:{warning.line} - {warning.message}"
                )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate documentation files")
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=Path.cwd(),
        help="Root directory containing documentation files",
    )
    args = parser.parse_args()

    validator = DocValidator(args.root_dir)
    if not validator.validate_all():
        sys.exit(1)


if __name__ == "__main__":
    main()
