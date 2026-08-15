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

### Design decisions

- Human prose and AI machine contracts are separate surfaces.
- Absence means unavailable, not false.
- Public export is explicit-allow only.
- Primary live evidence outranks cached substrate summaries.
- Model adapters transport context but do not redefine canonical facts.
- Phase 1 registries are explicitly selective, not exhaustive.
- Missing graph edges are unknown, not evidence of no relationship.
- Source references resolve through a public provenance registry.
