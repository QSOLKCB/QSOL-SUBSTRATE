# Phase 3 Validation and CI

QSOL-SUBSTRATE Phase 3 turns the canonical public substrate into a fail-closed integrity domain.

The validator does not ask whether the JSON merely parses. It asks whether the public substrate is internally resolvable as one coherent snapshot.

## Commands

```bash
python -m pip install -r requirements-validation.txt
python -m unittest discover -s tests -v
python tools/validate_substrate.py
python tools/fingerprint_substrate.py --output substrate-fingerprint.json
```

`validate_substrate.py` exits non-zero whenever a required invariant cannot be resolved safely. Use `--json-report <path>` to preserve a machine-readable report.

## Validation layers

### JSON Schema

Phase 3 checks every registered Draft 2020-12 schema for schema validity, validates the Phase 2 export policy/allowlist/deny-policy documents against their registered schemas, and validates every canonical public record against `schema/substrate.schema.json` with format checking enabled.

Schema validation is necessary but not sufficient. Cross-file semantics are enforced separately.

### Canonical identity and referential integrity

Canonical record IDs must be globally unique and use the prefix appropriate to their record type. At least one public identity record must exist. The validator fails closed on duplicate or unresolved canonical IDs.

The canonical payload file set is explicit. Unknown or missing payload roots fail until the validator is deliberately extended, preventing a new canonical file from silently bypassing integrity checks.

### Provenance

Every non-source public record requires resolvable public `source_refs`, except substrate-defined `research_topic` taxonomy nodes. Those topic nodes must participate in at least one sourced relationship edge.

Source records are checked against the provenance classes declared by `ai/ontology.json`. Commit-pinned sources require a 40-character commit and a snapshot URL containing that exact commit. Release records must use `release_tag_commit` snapshots with a tag and GitHub release ID.

Private provenance never satisfies public provenance.

### Alias collisions

The terminology namespace is case-folded and whitespace-normalized. A canonical term name or alias may not resolve to two different term IDs.

This is deliberately scoped to `terminology/index.json`: identical human labels may legitimately appear in different ontological namespaces elsewhere in the substrate.

### DOI and publication identity

Publication DOIs must be syntactically DOI-shaped and unique after normalization.

Every publication repository must resolve to a canonical project. Every publication must have exactly one `publishes` relationship, and the publishing project's repository must match the publication repository.

When a publication cites release evidence, its version must resolve to the corresponding `v<version>` release tag. If it declares a commit, that commit must match cited release evidence.

### Relationship graph

Every relationship source and target must resolve to a non-relationship canonical record. Relationship predicates must exist in `ai/ontology.json`.

Dangling graph endpoints are validation failures, not implicit unknown nodes.

### Chronology and release identity

Chronology records must contain timezone-aware ISO timestamps in nondecreasing order.

Events that declare a release tag must resolve their repository to a canonical project and cite at least one public release record with the same tag and repository. Event DOIs, when present, must resolve to a publication in the same repository.

### Public boundary

The validator reasserts the Phase 2 publication boundary:

```text
repository visibility = public
publication model = explicit_allow_only
absence = unavailable_not_false
private source access required = false
sources/index.json = immutable to private export
allowlist default = deny
```

Any drift in those invariants fails CI.

### Secret and private-reference scanning

The Phase 2 deny policy is reused as the public validation scanner. Canonical payload, normative AI machine files, and the publication allowlist are scanned for forbidden field names, credential patterns, and configured private references. JSON object keys are scanned as well as values.

`public_export/exclude.json` is not scanned against itself because it intentionally contains the patterns being detected.

## SHA-256 substrate fingerprint

`fingerprint_substrate.py` computes a semantic fingerprint over the canonical public payload only.

Each payload file is parsed and re-serialized using the Phase 2 canonicalization rules. A SHA-256 and byte length are calculated for each canonical representation. The final substrate SHA-256 is calculated over the lexicographically ordered path/hash/length table.

This means formatting-only changes do not alter the semantic substrate fingerprint, while changes to canonical public data do.

The fingerprint deliberately excludes README text, tests, tools, CI, and adapters. Those artifacts can change without claiming that the public knowledge snapshot changed.

## CI

`.github/workflows/validate-substrate.yml` runs on pushes and pull requests targeting `main`.

The workflow:

1. installs the pinned validation dependency;
2. runs the complete regression suite, including the Phase 2 exporter tests;
3. runs fail-closed substrate validation;
4. generates the SHA-256 substrate fingerprint;
5. publishes the fingerprint in the Actions summary;
6. uploads the JSON validation report and fingerprint as build artifacts.

Phase 3 does not query live GitHub or Zenodo during validation. Live evidence may change independently of a frozen substrate snapshot; deterministic internal integrity and external freshness are separate questions.

## Failure rule

If canonical identity, provenance, visibility, relationships, chronology, publication/release identity, or public-boundary state cannot be resolved safely, the correct CI result is failure.

```text
VALIDATION REFUSED
```

No warning-only mode is provided for canonical integrity failures.
