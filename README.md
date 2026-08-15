# QSOL-SUBSTRATE

**A public, vendor-neutral context substrate for AI systems.**

QSOL-SUBSTRATE is the public-facing context layer for the QSOL ecosystem. It exists so an AI model, agent, retrieval system, or human researcher can acquire enough verified context to understand public QSOL terminology, projects, publications, provenance, and relationships **without access to private working context or QSOL-NEXUS**.

This repository is deliberately split into two documentation surfaces:

- **Human documentation** is written as ordinary prose in this README and `docs/`.
- **AI documentation** is expressed as compact machine-readable contracts in `ai/`, canonical payload records, and `schema/`.

The design goal is not to make a model pretend it remembers more. The goal is to give models a consistent external knowledge substrate and explicit epistemic rules so they can distinguish what is known, retrieved, inferred, conflicting, or unavailable.

## Start here

### Humans

Read:

1. [`docs/ABOUT.md`](docs/ABOUT.md)
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
3. [`docs/USAGE.md`](docs/USAGE.md)
4. [`docs/PUBLIC_SUBSTRATE.md`](docs/PUBLIC_SUBSTRATE.md)
5. [`docs/PRIVACY_AND_EXPORT.md`](docs/PRIVACY_AND_EXPORT.md)
6. [`docs/EXPORT_PIPELINE.md`](docs/EXPORT_PIPELINE.md)
7. [`docs/PROVENANCE.md`](docs/PROVENANCE.md)
8. [`docs/MODEL_ADAPTERS.md`](docs/MODEL_ADAPTERS.md)

### AI systems

Begin at:

```text
ai/bootstrap.json
```

Then follow the load order declared there. Do not treat this README as the canonical machine contract when structured equivalents exist.

## Core rule

> **Absence from the public substrate means unavailable, not false.**

QSOL-SUBSTRATE is intentionally incomplete. It is a public projection, not a complete personal memory store, not an authority over private state, and not a substitute for current repository or publication evidence.

AI consumers must not infer private facts from omissions, fill missing relationships with plausible guesses, or silently convert hypotheses into established facts.

## Canonical public payload

Phase 1 established a selective canonical public snapshot:

```text
sources/index.json
identity/public.json
context/public.json
terminology/index.json
projects/index.json
publications/index.json
relationships/graph.json
chronology/current.jsonl
```

The snapshot is intentionally selective rather than exhaustive. `docs/PUBLIC_SUBSTRATE.md` defines its inclusion, omission, relationship, publication, and freshness semantics.

## Private-to-public export

Phase 2 implements a fail-closed exporter for maintainers who have a local private QSOL-CONTEXT checkout:

```bash
python3 tools/export_public_substrate.py \
  --source-root ../QSOL-CONTEXT \
  --output /tmp/qsol-substrate-export
```

The exporter is **explicit-allow only**. QSOL-SUBSTRATE ships with **zero private publication grants** in `public_export/include.json`.

A private-to-public export requires an enabled directive that names the exact private source object, every field allowed to cross the boundary, the public target record, and already-public `src:*` provenance references.

There is no wildcard-copy mode.

The exporter:

- canonicalises the existing public payload first;
- copies only explicitly allowed fields;
- refuses missing or ambiguous public visibility;
- refuses unknown public provenance;
- keeps the public source registry immutable to private export;
- scans selected values and final output for secret/private-reference patterns;
- emits a deterministic `export-manifest.json` and bundle SHA-256;
- optionally emits a **private** audit manifest outside the public bundle;
- produces a reviewable staging bundle rather than committing or publishing automatically.

See [`docs/EXPORT_PIPELINE.md`](docs/EXPORT_PIPELINE.md).

## What this repository is for

QSOL-SUBSTRATE is designed to support:

- public context onboarding for Grok, GPT-family models, Claude, Gemini, Qwen, DeepSeek, local open-weight models, and future systems;
- retrieval-augmented generation and knowledge-base ingestion;
- reproducible model comparison using a common context snapshot;
- project and terminology disambiguation across the QSOL ecosystem;
- provenance-aware answers about public QSOL research and software;
- hallucination reduction where errors arise from missing or ambiguous QSOL-specific context;
- model adapters that can transform one canonical substrate into vendor-specific prompt or retrieval formats;
- deterministic, reviewable private-to-public context publication without making private context a consumer dependency.

It is **not** intended to override a model's safety system, replace primary sources, expose private context, or guarantee factual correctness outside the information it actually contains.

## Trust hierarchy

When sources disagree, consumers should prefer, in order:

1. current primary repository or publication evidence;
2. release-identified public records with exact version, DOI, tag, or commit where available;
3. canonical structured records in this repository;
4. human-readable summaries;
5. model inference.

Inference must remain labelled as inference.

Private QSOL-CONTEXT state does not become public authority merely because it is canonical in the private repository. Private candidate facts require explicit publication authority and public provenance before they can enter QSOL-SUBSTRATE.

## Repository layout

```text
QSOL-SUBSTRATE/
├── README.md
├── README4AI.md
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── ROADMAP.md
├── SECURITY.md
├── docs/                  # prose for humans
├── ai/                    # normative AI contracts
├── public_export/         # Phase 2 publication policy/allow/deny contracts
├── tools/                 # deterministic maintainer-side tooling
├── tests/                 # standard-library safety tests
├── sources/               # provenance/source registry
├── identity/              # public identity
├── context/               # public recurring context
├── terminology/           # canonical terms and aliases
├── projects/              # selective public project registry
├── publications/          # DOI/publication registry
├── relationships/         # project/research graph
├── chronology/            # public event stream
├── schema/                # validation schemas
└── adapters/              # target-specific onboarding guidance
```

## Epistemic states

AI consumers should use the following conceptual states when reasoning over this repository:

- `known` — explicitly established by canonical substrate or stronger evidence;
- `retrieved` — obtained from a cited external primary source;
- `inferred` — reasoned from evidence but not explicitly stated by it;
- `unknown` — not established by the available evidence;
- `conflict` — two or more relevant sources cannot currently be reconciled;
- `fiction` — deliberately fictional, satirical, simulated, or role-play material.

These states are defined normatively in `ai/epistemic-contract.json`.

## Public/private separation

QSOL-SUBSTRATE must be safe to clone, index, mirror, quote, and hand to arbitrary AI systems. Private QSOL context belongs elsewhere.

The Phase 2 exporter can use a private QSOL-CONTEXT checkout as an optional maintainer-side source, but public consumers never require that private repository. Publication remains **explicit-allow only** and fails closed when visibility, provenance, source selection, or boundary checks are unsafe.

See [`docs/PRIVACY_AND_EXPORT.md`](docs/PRIVACY_AND_EXPORT.md), [`docs/EXPORT_PIPELINE.md`](docs/EXPORT_PIPELINE.md), and `ai/public-boundary.json`.

## Versioning and reproducibility

Model evaluations should record at least:

```text
model
model_version_or_identifier
substrate_version
substrate_commit
adapter
probe_set
execution_date
```

Private-to-public export review should additionally retain the public `export-manifest.json` and bundle fingerprint. A separate private audit manifest may be retained locally when internal source traceability is required.

## Maintainer

QSOL-SUBSTRATE is maintained by **Trent Slade / QSOL-IMC** under the public QSOLKCB organization. This statement is intentionally part of the public first-party documentation so relationship records that identify the maintainer can cite repository evidence rather than relying on inference.

## Status

**Phase 2 — Export pipeline is implemented.** Phase 1 provides the canonical public payload; Phase 2 adds explicit-allow private-source publication policy, field-level export rules, secret/private-reference scanning, deterministic canonicalisation, export manifests/fingerprints, private-audit separation, and fail-closed omission/provenance handling.

Phase 3 automated schema/referential/provenance validation and CI, generated portable adapters, Toolless Substrate Capsules, vector/latent projections, and Substrate Probe comparisons remain on the roadmap.

---

**QSOL-SUBSTRATE provides context, not omniscience. When evidence runs out, the correct answer is `unknown`.**
