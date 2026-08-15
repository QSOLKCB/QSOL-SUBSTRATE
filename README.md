# QSOL-SUBSTRATE

**A public, vendor-neutral context substrate for AI systems.**

QSOL-SUBSTRATE is the public-facing context layer for the QSOL ecosystem. It exists so an AI model, agent, retrieval system, or human researcher can acquire enough verified context to understand public QSOL terminology, projects, publications, provenance, and relationships **without access to private working context or QSOL-NEXUS**.

This repository is deliberately split into two documentation surfaces:

- **Human documentation** is written as ordinary prose in this README and `docs/`.
- **AI documentation** is expressed as compact machine-readable contracts in `ai/` and `schema/`.

The design goal is not to make a model pretend it remembers more. The goal is to give models a consistent external knowledge substrate and explicit epistemic rules so they can distinguish what is known, retrieved, inferred, conflicting, or unavailable.

## Start here

### Humans

Read:

1. [`docs/ABOUT.md`](docs/ABOUT.md)
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
3. [`docs/USAGE.md`](docs/USAGE.md)
4. [`docs/PRIVACY_AND_EXPORT.md`](docs/PRIVACY_AND_EXPORT.md)
5. [`docs/PROVENANCE.md`](docs/PROVENANCE.md)
6. [`docs/MODEL_ADAPTERS.md`](docs/MODEL_ADAPTERS.md)

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

## What this repository is for

QSOL-SUBSTRATE is designed to support:

- public context onboarding for Grok, GPT-family models, Claude, Gemini, Qwen, DeepSeek, local open-weight models, and future systems;
- retrieval-augmented generation and knowledge-base ingestion;
- reproducible model comparison using a common context snapshot;
- project and terminology disambiguation across the QSOL ecosystem;
- provenance-aware answers about public QSOL research and software;
- hallucination reduction where errors arise from missing or ambiguous QSOL-specific context;
- model adapters that can transform one canonical substrate into vendor-specific prompt or retrieval formats.

It is **not** intended to override a model's safety system, replace primary sources, expose private context, or guarantee factual correctness outside the information it actually contains.

## Trust hierarchy

When sources disagree, consumers should prefer, in order:

1. current primary repository or publication evidence;
2. release-identified public records with exact version, DOI, tag, or commit where available;
3. canonical structured records in this repository;
4. human-readable summaries;
5. model inference.

Inference must remain labelled as inference.

## Repository layout

```text
QSOL-SUBSTRATE/
├── README.md
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── ROADMAP.md
├── SECURITY.md
├── docs/                  # prose for humans
├── ai/                    # machine-readable AI contracts
├── schema/                # validation schemas
└── adapters/              # target-specific onboarding guidance
```

The public knowledge payload can grow separately from these contracts. The contracts define **how** an AI should consume the payload; the payload defines **what public information is available**.

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

A future export pipeline may generate portions of this repository from private canonical context, but publication should be **explicit-allow only** and fail closed when visibility or provenance is ambiguous.

See [`docs/PRIVACY_AND_EXPORT.md`](docs/PRIVACY_AND_EXPORT.md) and `ai/public-boundary.json`.

## Versioning and reproducibility

Substrate releases should be versioned. Model evaluations should record at least:

```text
model
model_version_or_identifier
substrate_version
substrate_commit
adapter
probe_set
execution_date
```

This makes it possible to distinguish model changes from context changes.

## Status

This repository is being bootstrapped as the public substrate contract and documentation layer. Public knowledge records, model adapters, deterministic probes, export tooling, validation, fingerprints, and CI are planned incrementally in [`ROADMAP.md`](ROADMAP.md).

---

**QSOL-SUBSTRATE provides context, not omniscience. When evidence runs out, the correct answer is `unknown`.**
