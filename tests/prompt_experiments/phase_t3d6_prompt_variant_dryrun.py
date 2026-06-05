#!/usr/bin/env python3
"""Phase T3-D6.2: Lite Prompt Variant Dry-run Script

This script performs a dry-run validation of the Lite Prompt experiment variants.
It does NOT call LLM, does NOT start services, does NOT modify production files.

Purpose:
1. Validate all variant files exist
2. Count lines in each variant file
3. Verify Variant C is marked as recommended
4. Generate a JSON report of the validation results
"""

import json
import sys
from pathlib import Path


def get_variant_files() -> list[dict]:
    """Return list of variant configurations."""
    base_path = Path("docs/testing/prompt-experiments/lite-continuation")
    return [
        {
            "id": "baseline",
            "file": str(base_path / "baseline.md"),
            "name": "Baseline",
            "purpose": "当前生产 Prompt 对照组",
            "recommended": False,
        },
        {
            "id": "variant-a-length",
            "file": str(base_path / "variant-a-length.md"),
            "name": "Variant A",
            "purpose": "字数约束",
            "recommended": False,
        },
        {
            "id": "variant-b-length-action-chain",
            "file": str(base_path / "variant-b-length-action-chain.md"),
            "name": "Variant B",
            "purpose": "字数 + 行动链",
            "recommended": False,
        },
        {
            "id": "variant-c-action-conflict-hook",
            "file": str(base_path / "variant-c-action-conflict-hook.md"),
            "name": "Variant C",
            "purpose": "字数 + 行动链 + 冲突推进 + 结尾钩子",
            "recommended": True,  # Recommended to test first
        },
        {
            "id": "variant-d-full-constraints",
            "file": str(base_path / "variant-d-full-constraints.md"),
            "name": "Variant D",
            "purpose": "完整约束 + 禁止模板词 + 降低 AI 腔",
            "recommended": False,
        },
    ]


def validate_variant(variant: dict) -> dict:
    """Validate a single variant file."""
    file_path = Path(variant["file"])
    exists = file_path.exists()
    line_count = 0

    if exists:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        line_count = len(lines)

    return {
        "id": variant["id"],
        "name": variant["name"],
        "file": variant["file"],
        "purpose": variant["purpose"],
        "exists": exists,
        "line_count": line_count,
        "recommended": variant["recommended"],
        "valid": exists and line_count > 10,
    }


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("Phase T3-D6.2: Lite Prompt Variant Dry-run")
    print("=" * 60)
    print()

    variants = get_variant_files()
    results = []
    all_valid = True

    print("Validating variant files...")
    print()

    for variant in variants:
        result = validate_variant(variant)
        results.append(result)

        status = "OK" if result["valid"] else "FAIL"
        print(f"  [{status}] {result['name']}")
        print(f"        File: {result['file']}")
        print(f"        Exists: {result['exists']}")
        print(f"        Line count: {result['line_count']}")
        print(f"        Recommended: {result['recommended']}")
        print()

        if not result["valid"]:
            all_valid = False

    # Find recommended variant
    recommended_variant = next(
        (r for r in results if r["recommended"]), None
    )

    if recommended_variant is None:
        print("ERROR: No recommended variant found (Variant C should be recommended)")
        return 1

    # Build output JSON
    output = {
        "phase": "T3-D6.2",
        "mode": "dry_run",
        "llm_called": False,
        "production_prompt_modified": False,
        "variants": [
            {
                "id": r["id"],
                "file": r["file"],
                "exists": r["exists"],
                "line_count": r["line_count"],
                "recommended": r["recommended"],
                "purpose": r["purpose"],
            }
            for r in results
        ],
        "recommended_first_variant": recommended_variant["id"],
        "all_valid": all_valid,
        "next_step": "Phase T3-D6.3 or T3-D6.2-real-run",
    }

    # Write JSON output
    output_path = Path(
        "docs/testing/prompt-experiments/lite-continuation/t3d6-variant-dryrun-results.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  All variants valid: {all_valid}")
    print(f"  Recommended first variant: {recommended_variant['name']} ({recommended_variant['id']})")
    print(f"  Output JSON: {output_path}")
    print()
    print("JSON output:")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print()

    if not all_valid:
        print("RESULT: FAIL - Some variant files are missing or too short")
        return 1

    print("RESULT: PASS - All variant files validated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
