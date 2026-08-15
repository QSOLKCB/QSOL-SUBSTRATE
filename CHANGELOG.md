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
- Phase 4 deterministic portable-adapter compiler at `tools/build_adapters.py`.
- Phase 4 adapter-bundle validator at `tools/validate_adapter_bundle.py`.
- Generic single-file, Grok chat, xAI Collections, Grok Build, Sider, Ollama, OpenAI-compatible, and Anthropic-compatible generated transports.
- Model-independent adapter manifest with exact snapshot version, source commit, substrate SHA-256, projection SHA-256, adapter identities, per-file hashes, and aggregate adapter-bundle SHA-256.
- Strict JSON Schema for generated portable-adapter manifests.
- Grok Build `AGENTS.md` plus repo-local `qsol-substrate` skill export.
- xAI retrieval document plus collection/upload metadata export.
- Ollama system-context and Modelfile-template export.
- OpenAI Responses-style and Anthropic Messages-style request templates with runtime model/task placeholders.
- Phase 4 adapter regression tests and GitHub Actions build/validation artifact upload.
- Human documentation for adapter provenance, generation, transport boundaries, and validation.
- Phase 5 deterministic tool-less capsule compiler at `tools/build_toolless.py`.
- Phase 5 fail-closed capsule validator at `tools/validate_toolless_capsule.py`.
- `MICRO`, `STANDARD`, and `FULL` self-contained public substrate profiles under generated `dist/toolless/` output.
- Model-independent `qsol-portable-token-v1` budgeting contract with deterministic NFKC/UTF-8 accounting.
- Priority-aware whole-record selection with source-reference, relationship-endpoint, and canonical-ID dependency closure.
- Tool-less cold-boot rules declaring no browsing/retrieval/filesystem/repository/tool access and a frozen snapshot freshness ceiling.
- Strategic repeated epistemic guards for the `MICRO` small-model profile.
- Project-tag-derived inline claim-boundary guards for satire, formalization/formal assurance, and archived AI-observation material.
- Strict JSON Schema for generated tool-less manifests with per-profile hashes, token counts, inclusion/omission counts, and aggregate bundle SHA-256.
- Canonical-object equality validation so re-hashed transformed facts still fail closed.
- Phase 5 regression tests and GitHub Actions build/validation artifact upload.
- Human documentation for tool-less profile semantics, token budgeting, serialization, provenance closure, claim boundaries, and reproducible identity.
- Phase 5 hardening that re-renders every expected capsule byte from canonical state, recomputes compact-profile selection and composition metadata, rejects symlinked/extra artifact files, and binds frozen identity to the canonical manifest.
- `YEAH-NAH/1` Australian pragmatic-humour probe added to the future Substrate Probe roadmap, with sarcasm, deadpan, understatement, banter, hostility, and uncertainty-calibration targets.

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
- Phase 4 adapters are generated projections, never canonical fact stores.
- Every Phase 4 knowledge-bearing adapter embeds one byte-identical canonical projection body and records its `projection_sha256`.
- Until formal release SemVer exists, adapter provenance uses `snapshot-YYYY-MM-DD` plus exact source commit and canonical substrate SHA-256.
- Runtime model IDs, API keys, collection IDs, and local model choices are transport configuration and are not canonical substrate facts.
- Adapter output may change formatting and delivery but may not enrich, reinterpret, promote, or otherwise redefine canonical substrate facts.
- Phase 5 capsules are generated frozen public context images, not new canonical truth stores.
- A tool-less capsule may omit records only at whole-record boundaries; omission remains unavailable, not false.
- Included records bring their public provenance and relationship dependencies with them rather than leaving dangling references to save context.
- `qsol-portable-token-v1` is a deterministic build budget and makes no claim of equality with any vendor/model tokenizer.
- The `FULL` profile must contain every canonical payload item represented by the compiler or the build fails closed.
- Tool-less currentness is bounded by the embedded snapshot date; without directly supplied newer evidence, unresolved post-snapshot state remains `UNKNOWN`.
- Claim-boundary lines are epistemic guards derived from explicit canonical project tags and are validated independently; they are not additional project facts.
- A Phase 5 capsule is valid only when its complete bytes equal the deterministic renderer output for the declared canonical substrate and source commit; recognized-record parsing alone is insufficient.
- In-repository capsule generation is restricted to `dist/toolless`; generated-artifact tooling may never replace canonical source, tooling, or contract directories.
- Capsule manifests are recomputed metadata, not trusted claims: profile selection, kind counts, identity, hashes, byte counts, token counts, and bundle membership must all resolve from canonical state.
- CI-derived artifact identity is stamped from the exact checked-out commit rather than from a different PR ref.
- Pragmatic humour classification is interpretive evidence: `SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED`, and `UNCERTAIN != SARCASTIC`.
