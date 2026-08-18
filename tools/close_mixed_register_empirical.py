#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from mixed_register_empirical_closure import EmpiricalClosureError, build_closure, render_markdown
from substrate_integrity import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "schema/mixed-register-empirical-closure.schema.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Close the two Phase 9 empirical MIXED-REGISTER/1 questions from a completed cold-consumer run."
    )
    parser.add_argument("--empirical-dir", type=Path, default=Path("dist/empirical/mixed-register"))
    parser.add_argument("--output", type=Path, default=Path("dist/empirical/mixed-register/closure.json"))
    parser.add_argument("--markdown", type=Path, default=Path("dist/empirical/mixed-register/closure.md"))
    args = parser.parse_args()

    empirical_dir = args.empirical_dir if args.empirical_dir.is_absolute() else ROOT / args.empirical_dir
    output = args.output if args.output.is_absolute() else ROOT / args.output
    markdown = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown

    try:
        closure = build_closure(ROOT, empirical_dir)
        schema = json.loads((ROOT / SCHEMA).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(closure))
        if errors:
            pointer = "/".join(str(part) for part in errors[0].absolute_path) or "$"
            raise EmpiricalClosureError(f"closure schema violation at {pointer}: {errors[0].message}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_bytes(closure))
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(closure), encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, EmpiricalClosureError) as exc:
        print(f"EMPIRICAL CLOSURE REFUSED: {exc}")
        return 1

    print(f"guard_effect_conclusion={closure['guard_effect_conclusion']}")
    print(f"local_guards_improved_in_any_condition={str(closure['local_guards_improved_in_any_condition']).lower()}")
    print(f"cold_consumer_classification_demonstrated={str(closure['cold_consumer_classification_demonstrated']).lower()}")
    print("strict_passing_guarded_conditions=" + ",".join(closure["strict_passing_guarded_conditions"]))
    print(f"output={output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
