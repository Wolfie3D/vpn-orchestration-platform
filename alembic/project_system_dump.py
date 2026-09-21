#!/usr/bin/env python3
"""Write one text file containing a readable snapshot of a project tree.

Includes dotfiles and text-based secret/configuration files (for example .env).
Keep the generated report private.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


SKIPPED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".next",
    ".cache",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".idea",
    ".vscode",
}


def read_text(path: Path) -> str | None:
    """Return text content, or None for binary/unreadable files."""
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if b"\0" in data:
        return None

    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return None


def write_dump(root: Path, destination: Path) -> tuple[int, int]:
    root = root.resolve()
    destination = destination.resolve()
    included = skipped = 0

    with destination.open("w", encoding="utf-8", newline="\n") as report:
        report.write(f"PROJECT SYSTEM DUMP\nRoot: {root}\n\n")
        report.write("Excluded directories: " + ", ".join(sorted(SKIPPED_DIRECTORIES)) + "\n")
        report.write("Binary/unreadable files are listed but their bytes are not included.\n\n")

        for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            dir_path = Path(directory)
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in SKIPPED_DIRECTORIES and not (dir_path / name).is_symlink()
            )

            for filename in sorted(filenames):
                path = dir_path / filename
                if path.resolve() == destination:
                    continue
                relative = path.relative_to(root).as_posix()
                report.write("=" * 88 + "\n")
                report.write(f"FILE: {relative}\n")
                report.write("=" * 88 + "\n")

                if path.is_symlink():
                    report.write("[Skipped symbolic link]\n\n")
                    skipped += 1
                    continue

                content = read_text(path)
                if content is None:
                    report.write("[Skipped binary or unreadable file]\n\n")
                    skipped += 1
                    continue

                report.write(content)
                if content and not content.endswith("\n"):
                    report.write("\n")
                report.write("\n")
                included += 1

    return included, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a single readable project dump.")
    parser.add_argument("root", nargs="?", default=".", help="Project root (default: current directory)")
    parser.add_argument(
        "--output",
        default="system_dump.txt",
        help="Report path, relative to the current directory unless absolute",
    )
    args = parser.parse_args()

    root = Path(args.root)
    output = Path(args.output)
    included, skipped = write_dump(root, output)
    print(f"Created {output.resolve()} ({included} text files included; {skipped} files skipped).")


if __name__ == "__main__":
    main()
