# Changelog

All notable changes to QSOL-SUBSTRATE should be recorded here.

The project intends to use semantic versioning once formal releases begin.

## Unreleased

### Added

- Human-facing repository README.
- Human documentation for purpose, architecture, usage, privacy/export boundaries, provenance, and model adapters.
- `AGENTS.md` repository instructions for coding and AI agents.
- Contribution and security guidance.
- Public substrate roadmap.
- Machine-readable bootstrap, manifest, ontology, epistemic contract, retrieval policy, consumer contract, and public-boundary policy.
- Initial JSON Schema for substrate records.
- Initial generic, Grok, Sider, and Ollama adapter guidance.
- Phase 1 public source/provenance registry.
- Phase 1 public identity and recurring-context records.
- Canonical QSOL terminology and context-scoped alias registry.
- Selective active-public project registry.
- Selective verified publication/DOI registry.
- Public project/research/publication relationship graph.
- Materially relevant public chronology in JSONL.
- Human documentation for canonical public payload semantics.
- Phase 2 explicit-allow export policy under `public_export/`.
- Fail-closed private-to-public exporter at `tools/export_public_substrate.py`.
- Field-level public visibility grants with zero grants enabled by default.
- Secret, forbidden-field, source-path, and private-reference scanning.
- Deterministic `qsol-canonical-json-v1` and `qsol-canonical-jsonl-v1` export canonicalisation.
- Public export manifests with per-file SHA-256 and deterministic bundle fingerprint.
- Optional private audit manifest separated from public output.
- Standard-library Phase 2 exporter safety tests.
- Human documentation for the implemented export pipeline and review discipline.
- Phase 3 fail-closed repository integrity validator and machine-readable validation report.
- Phase 3 deterministic SHA-256 fingerprint over the canonical public payload.
- Cross-file validation for provenance, canonical IDs, aliases, DOI uniqueness, relationship endpoints, chronology, project/publication/release identity, and public-boundary invariants.
- Secret/private-reference scanning across canonical payloads and normative public machine contracts.
- Strict bootstrap JSON Schemas for `ai/manifest.json` and `ai/public-boundary.json`.
- Validation/fingerprint JSON Schemas and GitHub Actions enforcement.
- Adversarial Phase 3 integrity regression tests.

### Design decisions

- Human prose and AI machine contracts are separate surfaces.
- Absence means unavailable, not false.
- Public export is explicit-allow only.
- Primary live evidence outranks cached substrate summaries.
- Model adapters transport context but do not redefine canonical facts.
- Phase 1 registries are explicitly selective, not exhaustive.
- Missing graph edges are unknown, not evidence of no relationship.
- Source references resolve through a public provenance registry.
- Private export defaults to zero publication grants.
- Private records are never wildcard-copied; every exported field requires explicit public visibility.
- Private provenance is not copied into public records; generated records require already-public `src:*` provenance.
- `sources/index.json` is immutable to the private exporter.
- Secret detection fails export even when the selected field would otherwise be redacted.
- Public export manifests contain public-output fingerprints, not private source paths or hashes.
- Generated export bundles are staging artifacts requiring human review, not self-authorising publication.
- Phase 3 validation is network-independent and validates frozen-snapshot integrity rather than live-source freshness.
- Canonical collection boundaries define which record types may appear in each registry, graph collection, and chronology stream.
- Release identity must bind repository, tag, and commit to one trusted cited release source; independent partial matches are insufficient.
- Release evidence must originate from the declared primary GitHub repository path, not merely contain a repository-like substring.
- Validation findings must not echo detected secret-bearing object keys into logs or machine-readable reports.
- Secret/private-reference detector classes are fail-closed configuration and may not be disabled by empty arrays.
- The substrate fingerprint covers canonical public payload semantics, not documentation, tests, or tooling.
