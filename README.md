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
7. [`docs/VALIDATION.md`](docs/VALIDATION.md)
8. [`docs/ADAPTERS.md`](docs/ADAPTERS.md)
9. [`docs/TOOLLESS.md`](docs/TOOLLESS.md)
10. [`docs/VECTOR_AND_LATENT.md`](docs/VECTOR_AND_LATENT.md)
11. [`docs/SUBSTRATE_PROBE.md`](docs/SUBSTRATE_PROBE.md)
12. [`docs/PROVENANCE.md`](docs/PROVENANCE.md)
13. [`docs/MODEL_ADAPTERS.md`](docs/MODEL_ADAPTERS.md)

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

A private-to-public export requires an enabled directive that names the exact private source object, every field allowed to cross the boundary, the public target record, and already-public `src:*` provenance references. There is no wildcard-copy mode.

See [`docs/EXPORT_PIPELINE.md`](docs/EXPORT_PIPELINE.md).

## Validation and fingerprinting

Phase 3 validates the frozen public snapshot before it is treated as coherent substrate state:

```bash
python tools/validate_substrate.py --json-report validation-report.json
python tools/fingerprint_substrate.py --output substrate-fingerprint.json
```

Validation covers schemas, canonical IDs, provenance, aliases, DOI uniqueness, relationships, chronology, release identity, public-boundary invariants, secret/private-reference leakage, and deterministic SHA-256 substrate identity.

See [`docs/VALIDATION.md`](docs/VALIDATION.md).

## Portable model adapters

Phase 4 deterministically compiles the same canonical public substrate into eight disposable transport bundles:

```bash
python tools/build_adapters.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/adapters

python tools/validate_adapter_bundle.py --bundle dist/adapters
```

Generated transports cover generic single-file context, Grok chat, xAI Collections, Grok Build, Sider, Ollama, OpenAI-compatible Responses context, and Anthropic-compatible Messages context.

Every adapter records the substrate snapshot version, exact source commit, canonical substrate SHA-256, canonical projection SHA-256, adapter identity, per-file hashes, and aggregate adapter-bundle fingerprint.

Adapters may change formatting and delivery. **They may not redefine canonical substrate facts.** Runtime model IDs, API keys, collection IDs, and local model choices are not substrate facts.

See [`docs/ADAPTERS.md`](docs/ADAPTERS.md).

## Tool-less Substrate Capsules

Phase 5 generates deterministic, self-contained public context images for models that have no browser, retrieval layer, filesystem, repository access, or external tools:

```bash
python tools/build_toolless.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/toolless

python tools/validate_toolless_capsule.py --bundle dist/toolless
```

Generated profiles are:

```text
MICRO     8,192 qsol-portable-token-v1 budget
STANDARD 24,576 qsol-portable-token-v1 budget
FULL    131,072 qsol-portable-token-v1 budget
```

`qsol-portable-token-v1` is a deterministic model-independent **build budgeting contract**, not a claim about any vendor/model tokenizer.

The compiler admits only whole canonical items and closes public provenance, relationship endpoints, and other resolvable canonical-ID dependencies. Smaller profiles therefore cannot save context by creating dangling facts. `FULL` must contain the complete canonical payload projection or the build fails closed.

Each capsule declares that tools are unavailable, embeds the snapshot date/version/source commit/substrate SHA-256, and enforces the cold-boot guards:

```text
UNKNOWN != FALSE
INFERENCE != FACT
SATIRE != BIOGRAPHY
FORMALIZATION != PHYSICAL_TRUTH
```

`MICRO` deliberately repeats these guards near the end of the artifact for small-model robustness. High-risk project records also receive validated inline epistemic boundary guards derived from explicit canonical tags.

Capsules may compress by omission. **They may not transform canonical facts, invent missing facts, or claim freshness beyond the embedded snapshot.** Validation recompiles the expected capsule and requires exact deterministic equality.

See [`docs/TOOLLESS.md`](docs/TOOLLESS.md).

## Vector and latent substrate projections

Phase 6 adds two further derived projection families without changing the canonical public payload.

### Deterministic vector substrate

```bash
python tools/build_vectors.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/vectors

python tools/validate_vector_bundle.py --bundle dist/vectors
```

Generated vector output:

```text
dist/vectors/
├── records.jsonl
├── embeddings.f16
├── index.json
├── retrieval-report.json
└── manifest.json
```

`qsol-record-chunk-v1` uses one canonical item per deterministic retrieval chunk. `qsol-hash-embed-v1` produces a dependency-free 256-dimensional float16 reference embedding so CI can reproduce the complete index without network access or a vendor embedding service.

Canonical IDs, source paths, payload hashes, `source_refs`, epistemic state, visibility, and canonical payload objects remain outside embedding coordinates. Retrieval validates the vector bundle before use and closes selected results over public provenance and relationship endpoints before context is delivered.

The included reference report compares provenance-closed vector-selected context size with fixed MICRO/STANDARD/FULL budgets. It is a retrieval-size experiment, **not** a downstream answer-quality claim.

### Model-specific latent/prefix experiments

```bash
python tools/build_projections.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/projections

python tools/validate_projection_bundle.py --bundle dist/projections
```

Phase 6 defines reproducible experiment recipes for soft prompts/prefix tuning, prompt-tuned virtual tokens, LoRA epistemic adapters, prefilled KV caches, reusable prefix states, and hybrid epistemic-prefix + factual-text delivery.

Generic CI intentionally does **not** claim that model-specific weights were trained or that a universal KV cache exists. Real model-specific artifacts must bind to an exact compatibility identity covering model revision, architecture, tokenizer identity/hash, dimensions, attention layout, KV-layout version, tensor/KV precision, and quantization identity. A mismatch invalidates the projection.

The deterministic epistemic-prefix artifact carries stable interpretation rules while mutable factual material remains textual or retrieval-selected. It also freezes the YEAH-NAH/1 textual/prefix/hybrid delivery matrix for Phase 7 model-behavior measurement.

See [`docs/VECTOR_AND_LATENT.md`](docs/VECTOR_AND_LATENT.md).

## Substrate Probe and YEAH-NAH/1

Phase 7 makes the delivery experiments measurable. It defines a deterministic 48-case evaluation protocol rather than claiming that a successful build means a model improved:

```text
24 substrate epistemic/factual probes
24 YEAH-NAH/1 pragmatic probes
```

Build and validate it with:

```bash
python tools/build_probes.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/probes

python tools/validate_probe_bundle.py --bundle dist/probes
```

The protocol compares the same model under eight conditions:

```text
NAKED
MICRO
STANDARD
FULL
VECTOR
LATENT-PREFIX
HYBRID
TOOL-ENABLED
```

Real model runners emit a strict `qsol-probe-model-run` envelope containing raw output plus structured epistemic/pragmatic fields. The deterministic scorer produces schema-validated report cards and the comparison engine computes uplift against the **same model's naked baseline** while refusing mismatched substrate/probe identities.

Phase 7 measures factual accuracy, unsupported assertions, `UNKNOWN` precision/recall, alias resolution, provenance fidelity, contradiction handling, claim-boundary preservation, token efficiency, substrate uplift, and hallucination reduction.

`YEAH-NAH/1` adds sarcasm precision/recall, literal-meaning error, banter misclassification, hostility false positives, high-severity understatement preservation, confidence calibration, and cultural-context uplift. Its core guards include:

```text
SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED
UNCERTAIN != SARCASTIC
BANTER != HOSTILITY
UNDERSTATEMENT != LOW_SEVERITY
CONTEXT > TOKEN_POLARITY
```

CI runs a perfect-answer **scoring oracle only to validate the scorer**. The oracle is marked non-empirical and is mechanically forbidden from entering empirical comparison tables. A real model result requires an explicit model run.

See [`docs/SUBSTRATE_PROBE.md`](docs/SUBSTRATE_PROBE.md).

## What this repository is for

QSOL-SUBSTRATE is designed to support public context onboarding, retrieval-augmented generation, reproducible model comparison, QSOL entity disambiguation, provenance-aware answers, hallucination reduction, disposable model transports, tool-less inference, deterministic vector retrieval, model-specific projection experiments, and deterministic model-behaviour evaluation.

It is **not** intended to override a model's safety system, replace primary sources, expose private context, fabricate model benchmarks, or guarantee factual correctness outside the information it actually contains.

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
├── probe/                 # deterministic Phase 7 probe source cases
├── tools/                 # export, integrity, adapter, capsule, vector, projection, probe tooling
├── tests/                 # adversarial/regression suites
├── sources/               # provenance/source registry
├── identity/              # public identity
├── context/               # public recurring context
├── terminology/           # canonical terms and aliases
├── projects/              # selective public project registry
├── publications/          # DOI/publication registry
├── relationships/         # project/research graph
├── chronology/            # public event stream
├── schema/                # validation schemas
└── adapters/              # target-specific adapter guidance
```

Generated derived/evaluation artifacts live under `dist/adapters/`, `dist/toolless/`, `dist/vectors/`, `dist/projections/`, and `dist/probes/` during builds and CI. None is an additional canonical record store.

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
provider_or_runtime
substrate_version
substrate_commit
substrate_sha256
probe_bundle_sha256
comparison_condition
derived_artifact_kind
adapter_identity_or_capsule_profile_or_projection_identity
derived_artifact_sha256
input_output_token_usage
execution_date
```

Until formal release SemVer is introduced, derived artifacts use `snapshot-YYYY-MM-DD` as the explicit substrate snapshot version and always pair it with the full source commit and canonical substrate SHA-256.

## Maintainer

QSOL-SUBSTRATE is maintained by **Trent Slade / QSOL-IMC** under the public QSOLKCB organization. This statement is intentionally part of the public first-party documentation so relationship records that identify the maintainer can cite repository evidence rather than relying on inference.

## Status

**Phases 0–7 are implemented.** The repository now provides the documentation/machine contract, canonical public payload, fail-closed private export pipeline, cross-file validation and CI, deterministic substrate fingerprint, eight generated portable model adapters, deterministic MICRO/STANDARD/FULL tool-less context capsules, provenance-aware vector retrieval, reproducible model-specific latent/prefix experiment contracts, and a deterministic 48-case model-behaviour probe/report-card protocol including YEAH-NAH/1.

Formal release discipline remains on the roadmap. Real empirical model report cards are generated by explicit Phase 7 model runs; generic CI validates the protocol and scorer but does not fabricate model benchmarks.

---

**QSOL-SUBSTRATE provides context, not omniscience. When evidence runs out, the correct answer is `unknown`.**