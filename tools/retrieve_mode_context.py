from __future__ import annotations

import argparse
from pathlib import Path

from mode_core import ModeError, validate_mode_bundle
from vector_core import (
    VectorError,
    _context_closure,
    _load_json,
    _read_records,
    render_retrieved_context,
    retrieve,
    validate_vector_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def _safe_context_output(path: Path) -> Path:
    if path.exists() and path.is_symlink():
        raise ModeError("refusing to write mode-aware retrieved context through a symlink")
    resolved = path.resolve()
    root = ROOT.resolve()
    retrieved_root = (root / "dist" / "retrieved").resolve()
    if resolved == root or resolved in root.parents:
        raise ModeError("retrieved-context output may not replace or contain repository root")
    if root in resolved.parents and retrieved_root not in resolved.parents:
        raise ModeError("in-repository mode-aware retrieved-context output is restricted to dist/retrieved/")
    if resolved.exists() and not resolved.is_file():
        raise ModeError("retrieved-context output must be a regular file path")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve vector-selected QSOL context with QSOL-MODE-POLICY/1 prepended")
    parser.add_argument("query")
    parser.add_argument("--vector-bundle", type=Path, default=Path("dist/vectors"))
    parser.add_argument("--mode-bundle", type=Path, default=Path("dist/modes"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        vector_findings = validate_vector_bundle(ROOT, args.vector_bundle)
        mode_findings = validate_mode_bundle(ROOT, args.mode_bundle)
        if vector_findings:
            raise VectorError(f"vector bundle invalid: {vector_findings[0].code}")
        if mode_findings:
            raise ModeError(f"mode bundle invalid: {mode_findings[0].code}")
        vector_manifest = _load_json(args.vector_bundle / "manifest.json")
        mode_manifest = _load_json(args.mode_bundle / "manifest.json")
        if vector_manifest["substrate"]["source_commit"] != mode_manifest["substrate"]["source_commit"]:
            raise ModeError("vector and mode bundles have different source commits")
        if vector_manifest["substrate"]["substrate_sha256"] != mode_manifest["substrate"]["substrate_sha256"]:
            raise ModeError("vector and mode bundles have different canonical substrate fingerprints")
        rows = _read_records(args.vector_bundle / "records.jsonl")
        embeddings = (args.vector_bundle / "embeddings.f16").read_bytes()
        primary = retrieve(rows, embeddings, args.query, top_k=args.top_k)
        primary_ids = [row["canonical_id"] for row in primary]
        closed_ids = _context_closure(primary_ids, rows)
        context = render_retrieved_context(rows, closed_ids, vector_manifest["substrate"])
        prefix = (args.mode_bundle / "delivery-contract.txt").read_text(encoding="utf-8")
        text = prefix.rstrip() + "\nVECTOR_DELIVERY=MODE_BOUND\n\n" + context
        if args.output:
            output = _safe_context_output(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
    except (OSError, UnicodeDecodeError, VectorError, ModeError, KeyError) as exc:
        print(f"MODE VECTOR RETRIEVAL REFUSED: {exc}")
        return 1
    print("# primary=" + ",".join(primary_ids))
    print("# closure=" + ",".join(closed_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
