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
