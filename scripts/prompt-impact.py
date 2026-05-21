#!/usr/bin/env python3
"""prompt-impact.py — Find which pipeline YAML files reference a given prompt file.

Usage:
    python scripts/prompt-impact.py prompts/blocks/writing-rules.md
    python scripts/prompt-impact.py prompts/pipeline/generate/draft.md

Scans prompts/ for .yml/.yaml/.md/.jinja/.txt files and searches for
references to the target file via:
  - {% include "..." %} patterns
  - @{...} patterns
  - Relative path references (e.g. blocks/xxx.md)
"""

import os
import re
import sys
from pathlib import Path


def find_project_root() -> Path:
    """Walk up from this script to find the project root (contains AGENTS.md)."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "AGENTS.md").exists():
            return current
        current = current.parent
    # Fallback: assume script is in scripts/ under project root
    return Path(__file__).resolve().parent.parent


def normalize_path(p: str) -> str:
    """Normalize a path to use forward slashes and be relative to prompts/."""
    return p.replace("\\", "/").strip("/")


def find_references(target_rel_path: str, prompts_dir: Path) -> list[str]:
    """Find all files in prompts/ that reference the target file."""
    target_normalized = normalize_path(target_rel_path)
    target_basename = Path(target_normalized).name

    # Build search patterns
    # 1. The full relative path (e.g. blocks/writing-rules.md)
    # 2. Just the filename for short references
    # 3. Jinja include patterns
    search_terms = [
        target_normalized,                    # blocks/writing-rules.md
        target_basename,                      # writing-rules.md
    ]

    # Also extract the stem for pattern matching (e.g. writing-rules)
    target_stem = Path(target_normalized).stem
    if target_stem and target_stem != target_basename:
        search_terms.append(target_stem)      # writing-rules

    referencing_files = []
    extensions = {".yml", ".yaml", ".md", ".jinja", ".j2", ".txt"}

    for root, _dirs, files in os.walk(prompts_dir):
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix not in extensions:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            rel_path = str(fpath.relative_to(prompts_dir))
            rel_path = normalize_path(rel_path)

            # Skip self-reference
            if rel_path == target_normalized:
                continue

            found = False

            # Check Jinja {% include "..." %} patterns
            include_matches = re.findall(r'\{%[-\s]*include\s+["\']([^"\']+)["\']', content)
            for inc in include_matches:
                inc_norm = normalize_path(inc)
                if inc_norm == target_normalized or inc_norm.endswith("/" + target_normalized):
                    found = True
                    break

            if found:
                referencing_files.append(rel_path)
                continue

            # Check @{...} patterns
            at_matches = re.findall(r'@\{([^}]+)\}', content)
            for at_ref in at_matches:
                at_norm = normalize_path(at_ref)
                if at_norm == target_normalized or at_norm.endswith("/" + target_normalized):
                    found = True
                    break

            if found:
                referencing_files.append(rel_path)
                continue

            # Check direct path references in content
            for term in search_terms:
                # Match as a word boundary reference (not substring of another word)
                # For paths like blocks/writing-rules.md
                if "/" in term:
                    if term in content:
                        found = True
                        break
                else:
                    # For bare filenames, check it appears as a reference
                    # (not just a substring of another word)
                    pattern = re.compile(r'(?<![a-zA-Z0-9_/-])' + re.escape(term) + r'(?![a-zA-Z0-9_])')
                    if pattern.search(content):
                        found = True
                        break

            if found:
                referencing_files.append(rel_path)

    return sorted(set(referencing_files))


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/prompt-impact.py <prompt-file>")
        print("Example: python scripts/prompt-impact.py prompts/blocks/writing-rules.md")
        sys.exit(1)

    target = sys.argv[1]
    project_root = find_project_root()
    prompts_dir = project_root / "prompts"

    if not prompts_dir.exists():
        print(f"Error: prompts/ directory not found at {prompts_dir}")
        sys.exit(1)

    # Resolve target relative to project root
    target_path = Path(target)
    if not target_path.is_absolute():
        target_abs = project_root / target_path
    else:
        target_abs = target_path

    if not target_abs.exists():
        print(f"Warning: target file does not exist: {target_abs}")
        # Continue anyway — the file might be about to be created

    # Get path relative to prompts/
    try:
        target_rel = str(target_abs.relative_to(prompts_dir))
    except ValueError:
        # If the target is not under prompts/, use as-is
        target_rel = str(target_path)

    print(f"Analyzing: {target_rel}")
    print()

    refs = find_references(target_rel, prompts_dir)

    if refs:
        print("This prompt file may affect:")
        for ref in refs:
            print(f"  - prompts/{ref}")
    else:
        print("No direct references found.")


if __name__ == "__main__":
    main()
