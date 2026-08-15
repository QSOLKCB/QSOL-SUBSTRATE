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

### Design decisions

- Human prose and AI machine contracts are separate surfaces.
- Absence means unavailable, not false.
- Public export is explicit-allow only.
- Primary live evidence outranks cached substrate summaries.
- Model adapters transport context but do not redefine canonical facts.
