#!/usr/bin/env python3
"""Documentation auto-fix script.

This script automatically fixes common documentation issues:
1. Removes trailing whitespace
2. Fixes consecutive blank lines
3. Repairs common internal link patterns
4. Standardizes markdown formatting
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class DocFix:
    """Represents a documentation fix."""

    file: str
    line: int
    original: str
    fixed: str
    type: str  # 'format', 'link', 'content'


class DocFixer:
    """Documentation fixer."""

    def __init__(self, root_dir: Path):
        """Initialize fixer with project root directory."""
        self.root_dir = root_dir
        self.fixes: List[DocFix] = []

    def fix_all(self, dry_run: bool = True) -> bool:
        """Run all fixes."""
        logger.info("Starting documentation fixes...")

        try:
            # Fix formatting
            self.fix_formatting(dry_run)

            # Fix internal links
            self.fix_links(dry_run)

            # Fix markdown style
            self.fix_markdown_style(dry_run)

        except Exception as e:
            logger.error(f"Fixing failed: {str(e)}")
            return False

        # Report results
        self._report_results(dry_run)

        return True

    def fix_formatting(self, dry_run: bool) -> None:
        """Fix formatting issues."""
        logger.info("Fixing formatting...")

        for doc_file in self.root_dir.rglob("*.md"):
            content = doc_file.read_text()
            lines = content.splitlines()
            fixed_lines = []

            for i, line in enumerate(lines, 1):
                # Remove trailing whitespace
                fixed_line = line.rstrip()
                if fixed_line != line:
                    self.fixes.append(
                        DocFix(
                            file=str(doc_file),
                            line=i,
                            original=line,
                            fixed=fixed_line,
                            type="format",
                        )
                    )
                fixed_lines.append(fixed_line)

            # Fix consecutive blank lines
            new_lines = []
            prev_blank = False
            for line in fixed_lines:
                if not line.strip():
                    if not prev_blank:
                        new_lines.append(line)
                    prev_blank = True
                else:
                    new_lines.append(line)
                    prev_blank = False

            if not dry_run:
                doc_file.write_text("\n".join(new_lines) + "\n")

    def fix_internal_links(self, content: str, base_path: Path) -> str:
        """Fix relative links to point to the correct path."""

        def fix_link(match):
            link_text = match.group(1)
            link_path = match.group(2)

            if not link_path.startswith(("http://", "https://", "#", "/")):
                relative_path = base_path / link_path
                link_path = str(relative_path)

            return f"[{link_text}]({link_path})"

        return re.sub(r"\[(.*?)\]\((.*?)\)", fix_link, content)

    def fix_links(self, dry_run: bool) -> None:
        """Fix internal documentation links."""
        logger.info("Fixing internal links...")

        for doc_file in self.root_dir.rglob("*.md"):
            content = doc_file.read_text()
            fixed_content = self.fix_internal_links(content, doc_file.parent)

            if not dry_run and fixed_content != content:
                doc_file.write_text(fixed_content)

    def fix_markdown_style(self, dry_run: bool) -> None:
        """Fix markdown style issues."""
        logger.info("Fixing markdown style...")

        for doc_file in self.root_dir.rglob("*.md"):
            content = doc_file.read_text()
            lines = content.splitlines()
            fixed_lines = []

            for i, line in enumerate(lines, 1):
                fixed_line = line

                # Fix header spacing
                if line.startswith("#"):
                    fixed_line = re.sub(r"^(#+)(\w)", r"\1 \2", line)

                # Fix list item spacing
                if re.match(r"^[-*+]\w", line):
                    fixed_line = re.sub(r"^([-*+])(\w)", r"\1 \2", line)

                if fixed_line != line:
                    self.fixes.append(
                        DocFix(
                            file=str(doc_file),
                            line=i,
                            original=line,
                            fixed=fixed_line,
                            type="format",
                        )
                    )
                fixed_lines.append(fixed_line)

            if not dry_run:
                doc_file.write_text("\n".join(fixed_lines) + "\n")

    def _report_results(self, dry_run: bool) -> None:
        """Report fixing results."""
        if not self.fixes:
            print("[green]No fixes needed![/green]")
            return

        by_type = {}
        for fix in self.fixes:
            by_type.setdefault(fix.type, []).append(fix)

        print(f"\n{'DRY RUN - ' if dry_run else ''}Fixes made:")

        for fix_type, fixes in by_type.items():
            print(f"\n[blue]{fix_type.title()} Fixes:[/blue]")
            for fix in fixes:
                print(
                    f"{fix.file}:{fix.line}\n"
                    f"  [red]- {fix.original}[/red]\n"
                    f"  [green]+ {fix.fixed}[/green]"
                )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix documentation issues")
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=Path.cwd(),
        help="Root directory containing documentation files",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show fixes without making changes")
    args = parser.parse_args()

    fixer = DocFixer(args.root_dir)
    if not fixer.fix_all(args.dry_run):
        exit(1)


if __name__ == "__main__":
    main()
