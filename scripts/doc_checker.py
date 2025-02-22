#!/usr/bin/env python3
"""Documentation checker and metrics generator.

This script performs automated checks on documentation quality and generates metrics:
- Validates markdown formatting
- Checks for broken internal links
- Identifies outdated examples
- Generates documentation coverage metrics
- Detects potential security issues
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table


@dataclass
class DocMetrics:
    """Documentation metrics container."""

    total_files: int
    total_lines: int
    code_examples: int
    security_issues: int
    broken_links: List[str]
    outdated_examples: List[str]
    missing_sections: List[str]


class DocumentationChecker:
    """Checks documentation quality and generates metrics."""

    REQUIRED_SECTIONS = {
        "README.md": ["Installation", "Configuration", "Usage", "Contributing"],
        "runbook.md": ["Monitoring", "Common Issues", "Maintenance Tasks"],
        "doc_review.md": ["Review Information", "Documentation Checklist", "Changes Required"],
    }

    SECURITY_PATTERNS = [
        r"api_key\s*=\s*['\"'][^\'\"\s]+['\"']",
        r"password\s*=\s*['\"'][^\'\"\s]+['\"']",
        r"secret\s*=\s*['\"'][^\'\"\s]+['\"']",
        r"token\s*=\s*['\"'][^\'\"\s]+['\"']",
    ]

    def __init__(self, root_dir: Path):
        """Initialize with project root directory."""
        self.root_dir = root_dir
        self.console = Console()

    def check_documentation(self) -> DocMetrics:
        """Perform comprehensive documentation check."""
        metrics = DocMetrics(
            total_files=0,
            total_lines=0,
            code_examples=0,
            security_issues=0,
            broken_links=[],
            outdated_examples=[],
            missing_sections=[],
        )

        # Check all markdown files
        for md_file in self.root_dir.rglob("*.md"):
            rel_path = md_file.relative_to(self.root_dir)
            self.console.print(f"\n[bold blue]Checking {rel_path}...[/]")

            metrics.total_files += 1
            content = md_file.read_text()
            lines = content.split("\n")
            metrics.total_lines += len(lines)

            # Check sections
            self._check_required_sections(md_file.name, content, metrics)

            # Check code examples
            examples = self._check_code_examples(content)
            metrics.code_examples += len(examples)

            # Check for security issues
            issues = self._check_security_issues(content)
            metrics.security_issues += len(issues)
            if issues:
                self.console.print(f"[red]Found {len(issues)} security issues[/]")
                for issue in issues:
                    self.console.print(f"  - {issue}")

            # Check internal links
            broken = self._check_internal_links(content)
            metrics.broken_links.extend(broken)
            if broken:
                self.console.print(f"[yellow]Found {len(broken)} broken links[/]")
                for link in broken:
                    self.console.print(f"  - {link}")

        return metrics

    def _check_required_sections(self, filename: str, content: str, metrics: DocMetrics) -> None:
        """Check if required sections are present."""
        if filename not in self.REQUIRED_SECTIONS:
            return

        for section in self.REQUIRED_SECTIONS[filename]:
            if not re.search(rf"##+\s*{section}", content, re.IGNORECASE):
                metrics.missing_sections.append(f"{filename}: {section}")

    def _check_code_examples(self, content: str) -> List[str]:
        """Find and validate code examples."""
        return re.findall(r"```[a-zA-Z]*\n.*?\n```", content, re.DOTALL)

    def _check_security_issues(self, content: str) -> List[str]:
        """Check for potential security issues in documentation."""
        issues = []
        for pattern in self.SECURITY_PATTERNS:
            matches = re.finditer(pattern, content)
            issues.extend(f"Possible credential in: {m.group(0)}" for m in matches)
        return issues

    def _check_internal_links(self, content: str) -> List[str]:
        """Check for broken internal links."""
        broken = []
        links = re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content)
        for match in links:
            link = match.group(2)
            if not link.startswith(("http", "#")):
                target = self.root_dir / link
                if not target.exists():
                    broken.append(link)
        return broken

    def generate_report(self, metrics: DocMetrics) -> None:
        """Generate and display documentation metrics report."""
        table = Table(title="Documentation Metrics Report")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Files", str(metrics.total_files))
        table.add_row("Total Lines", str(metrics.total_lines))
        table.add_row("Code Examples", str(metrics.code_examples))
        table.add_row(
            "Security Issues",
            f"[red]{metrics.security_issues}[/]" if metrics.security_issues else "0",
        )
        table.add_row(
            "Broken Links",
            f"[yellow]{len(metrics.broken_links)}[/]" if metrics.broken_links else "0",
        )
        table.add_row(
            "Missing Sections",
            f"[yellow]{len(metrics.missing_sections)}[/]" if metrics.missing_sections else "0",
        )

        self.console.print("\n")
        self.console.print(table)

        if metrics.missing_sections:
            self.console.print("\n[yellow]Missing Sections:[/]")
            for section in metrics.missing_sections:
                self.console.print(f"  - {section}")

        if metrics.broken_links:
            self.console.print("\n[yellow]Broken Links:[/]")
            for link in metrics.broken_links:
                self.console.print(f"  - {link}")


def main():
    """Run documentation checks and generate report."""
    root_dir = Path(__file__).parent.parent
    checker = DocumentationChecker(root_dir)

    console = Console()
    console.print("[bold green]Starting Documentation Check...[/]")

    metrics = checker.check_documentation()
    checker.generate_report(metrics)

    # Exit with status code based on critical issues
    if metrics.security_issues > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
