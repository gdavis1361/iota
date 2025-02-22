#!/usr/bin/env python3
"""Validate code blocks in markdown files."""

import glob
import sys
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def find_markdown_files(root_dir: str = ".") -> List[str]:
    """Find all markdown files in the repository."""
    markdown_files = []
    for ext in ["md", "markdown"]:
        markdown_files.extend(glob.glob(f"{root_dir}/**/*.{ext}", recursive=True))
    return markdown_files


def extract_code_blocks(content: str) -> List[tuple]:
    """Extract code blocks from markdown content.

    Returns:
        List of tuples containing (language, code, line_number)
    """
    code_blocks = []
    lines = content.split("\n")
    in_code_block = False
    current_block = []
    current_lang = ""
    start_line = 0

    for i, line in enumerate(lines):
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                current_lang = line[3:].strip().lower()
                start_line = i + 1
                current_block = []
            else:
                if current_block and current_lang:
                    code_blocks.append((current_lang, "\n".join(current_block), start_line))
                in_code_block = False
                current_lang = ""
                current_block = []
        elif in_code_block:
            current_block.append(line)

    return code_blocks


def validate_python_code(code: str) -> Optional[str]:
    """Validate Python code syntax."""
    try:
        compile(code, "<string>", "exec")
        return None
    except SyntaxError as e:
        return f"Invalid Python syntax: {str(e)}"
    except Exception as e:
        return f"Error parsing Python code: {str(e)}"


VALIDATORS = {
    "python": validate_python_code,
    "py": validate_python_code,
}


def validate_file(file_path: str) -> List[dict]:
    """Validate all code blocks in a markdown file."""
    errors = []
    with open(file_path, "r") as f:
        content = f.read()

    code_blocks = extract_code_blocks(content)

    for lang, code, line_number in code_blocks:
        if lang in VALIDATORS:
            error = VALIDATORS[lang](code)
            if error:
                errors.append(
                    {
                        "file": file_path,
                        "line": line_number,
                        "language": lang,
                        "error": error,
                        "code": code,
                    }
                )

    return errors


def main():
    """Main entry point."""
    console.print(Panel("Starting code block validation...", style="bold blue"))

    root_dir = "."
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]

    files = find_markdown_files(root_dir)
    all_errors = []

    for file in files:
        errors = validate_file(file)
        all_errors.extend(errors)

    if all_errors:
        console.print("\n[red bold]Found code block errors:[/red bold]\n")
        for error in all_errors:
            console.print(f"[yellow]File:[/yellow] {error['file']}")
            console.print(f"[yellow]Line:[/yellow] {error['line']}")
            console.print(f"[yellow]Language:[/yellow] {error['language']}")
            console.print(f"[yellow]Error:[/yellow] {error['error']}\n")

            syntax = Syntax(
                error["code"],
                error["language"],
                theme="monokai",
                line_numbers=True,
                start_line=error["line"],
            )
            console.print(Panel(syntax, title="Code Block"))
            console.print("\n" + "-" * 80 + "\n")

        sys.exit(1)
    else:
        console.print("\n[green]✓ All code blocks are valid![/green]")
        sys.exit(0)


if __name__ == "__main__":
    main()
