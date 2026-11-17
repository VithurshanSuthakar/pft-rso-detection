"""Reject tracked data, images, binaries and local secrets before publication.

Run after staging files: python tools/check_repository.py
This checks Git's index as well as suffixes, so it catches forcibly staged data.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import subprocess
import sys


ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".toml", ".json", ".yml", ".yaml", ".cff", ".bib"}
ALLOWED_NAMES = {".gitignore", ".gitattributes", ".editorconfig", "LICENSE", "NOTICE"}
BLOCKED_PARTS = {"input", "data", "output", "outputs", "results", ".idea", ".venv", "__pycache__"}


def audit() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode("utf-8").split("\0")
    errors = []
    for name in filter(None, names):
        path = PurePosixPath(name)
        if any(part.casefold() in BLOCKED_PARTS for part in path.parts):
            errors.append(f"Local data/output path is staged: {name}")
        if path.name not in ALLOWED_NAMES and path.suffix.lower() not in ALLOWED_SUFFIXES:
            errors.append(f"Non-source file is staged: {name}")
        if path.name == ".env" or path.name.startswith(".env."):
            errors.append(f"Environment file is staged: {name}")
        content = subprocess.check_output(["git", "show", f":{name}"], cwd=root)
        if len(content) > 1_000_000:
            errors.append(f"Unexpectedly large source file: {name}")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"Binary content is staged: {name}")
        if b"\0" in content:
            errors.append(f"NUL bytes in staged source: {name}")
    return errors


if __name__ == "__main__":
    try:
        errors = audit()
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Repository check failed: {error}", file=sys.stderr)
        raise SystemExit(2)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print("Tracked files contain source/documentation only; no image or dataset files found.")

