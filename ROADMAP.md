# QSOL-SUBSTRATE Roadmap

## Phase 0 — Documentation contract

- [x] Human-facing README and conceptual documentation.
- [x] Machine bootstrap and epistemic contracts.
- [x] Public/private boundary contract.
- [x] Initial JSON schema.
- [x] Agent guidance.
- [x] Generic, Grok, Sider, and Ollama adapter documentation.

## Phase 1 — Canonical public substrate

- [x] Add public identity/context records.
- [x] Add canonical QSOL terminology and aliases.
- [x] Add active public project registry.
- [x] Add publication and DOI registry.
- [x] Add project/research relationship graph.
- [x] Add chronology for materially relevant public events.

Phase 1 establishes the canonical public knowledge layer. The registry is
selective rather than exhaustive: absence from the substrate means unavailable,
not false.

## Phase 2 — Export pipeline

- [ ] Define explicit-allow export policy from private QSOL-CONTEXT.
- [ ] Add field-level visibility rules.
- [ ] Add redaction and secret scanning.
- [ ] Add deterministic canonicalisation.
- [ ] Add export manifest and fingerprint.
- [ ] Fail closed on unknown visibility or provenance.
- [ ] Preserve public/private omission semantics during export.
- [ ] Guarantee that generated public records contain no private source references.

The export pipeline must treat publication as an explicit act. Private context
must never become public merely because a field was not explicitly marked
private.

## Phase 3 — Validation and CI

- [ ] JSON Schema validation.
- [ ] Referential-integrity validation.
- [ ] Provenance validation.
- [ ] Alias collision checks.
- [ ] DOI uniqueness checks.
- [ ] Relationship endpoint validation.
- [ ] Chronology ordering validation.
- [ ] Public-boundary checks.
- [ ] Secret/private-reference scanning.
- [ ] SHA-256 substrate fingerprint.
- [ ] GitHub Actions validation workflow.

Validation should fail closed when canonical identity, provenance, visibility,
relationships, or release identity cannot be resolved safely.

## Phase 4 — Portable model adapters

- [ ] Generic single-file substrate bundle.
- [ ] Grok chat bootstrap.
- [ ] xAI retrieval export.
- [ ] Grok Build project rules/skill export.
- [ ] Sider prompt/knowledge-base bundle.
- [ ] Ollama Modelfile/system-context bundle.
- [ ] OpenAI-compatible API bundle.
- [ ] Anthropic-compatible context bundle.
- [ ] Model-independent adapter manifest.
- [ ] Record exact substrate version, commit, and adapter identity for reproducible runs.

Adapters are disposable transport layers. They may change formatting and
delivery, but must never redefine canonical substrate facts.

## Phase 5 — Toolless Substrate Capsule

Create a deterministic, self-contained substrate representation for AI systems
that have no browsing, retrieval, file-system, repository, or external tool
access.

### Profiles

- [ ] `MICRO` tool-less profile for small-context and 4B–8B class models.
- [ ] `STANDARD` tool-less profile for general-purpose local and hosted models.
- [ ] `FULL` tool-less profile for large-context models.
- [ ] Deterministic token-budgeted compilation.
- [ ] Priority-aware truncation that preserves epistemic rules before optional detail.
- [ ] Strategic semantic redundancy for small models.
- [ ] Inline critical claim boundaries with high-risk project records.

### Toolless cold boot

- [ ] Add a compact cold-boot header declaring that the model has no tools.
- [ ] Declare substrate snapshot date prominently.
- [ ] Declare substrate version and SHA-256 fingerprint.
- [ ] Require `UNKNOWN != FALSE`.
- [ ] Require `INFERENCE != FACT`.
- [ ] Require `SATIRE != BIOGRAPHY`.
- [ ] Require `FORMALIZATION != PHYSICAL_TRUTH`.
- [ ] Require models not to claim freshness beyond the substrate snapshot.
- [ ] Require models to state snapshot limitations when current state cannot be verified.

Example invariant:

```text
IF_CURRENT_STATE_REQUIRED
AND_TOOLS_UNAVAILABLE
THEN:
    use snapshot only if sufficient;
    state snapshot date;
    do not claim currentness beyond snapshot;
    return UNKNOWN for unresolved post-snapshot state.
````

### Toolless serialization

* [ ] Define a compact LLM-oriented substrate serialization.
* [ ] Preserve canonical IDs and aliases.
* [ ] Inline important relationships where this improves local comprehension.
* [ ] Preserve publication and DOI identity.
* [ ] Preserve provenance class and epistemic state.
* [ ] Preserve chronology without requiring external lookup.
* [ ] Avoid deeply nested structures where they waste context.
* [ ] Generate all tool-less artifacts from the canonical substrate rather than maintaining duplicate facts manually.

Proposed output:

```text
dist/toolless/
├── QSOL-SUBSTRATE-MICRO.txt
├── QSOL-SUBSTRATE-STANDARD.txt
├── QSOL-SUBSTRATE-FULL.txt
└── manifest.json
```

The tool-less representation should behave as a frozen public context image:
one artifact in, no external tools required.

## Phase 6 — Vector and Latent Substrate Projection

Explore whether the same canonical substrate can be projected into more compact
machine representations without modifying the underlying canonical knowledge.

The canonical substrate remains vendor- and model-independent. Vector indexes,
prefix states, caches, and learned adapters are disposable model-specific
projections.

### Vector substrate

* [ ] Define deterministic record chunking.
* [ ] Generate embeddings for canonical substrate records.
* [ ] Preserve canonical record IDs alongside every vector.
* [ ] Preserve provenance and epistemic metadata outside the embedding itself.
* [ ] Add deterministic nearest-neighbour retrieval experiments.
* [ ] Compare vector-selected context against fixed textual profiles.
* [ ] Evaluate whether semantic retrieval can reduce prompt size without losing provenance.

Proposed output:

```text
dist/vectors/
├── records.jsonl
├── embeddings.f16
├── index.json
└── manifest.json
```

Embedding vectors are retrieval indexes, not canonical truth.

Raw embedding coordinates must never be treated as meaningful context by an LLM
without an explicit retrieval or projection mechanism.

### Latent / prefix substrate

Investigate model-specific substrate initialization mechanisms including:

* [ ] Soft prompt / prefix tuning.
* [ ] Prompt-tuned virtual tokens.
* [ ] Model-specific adapter or LoRA experiments.
* [ ] Prefilled attention/KV-cache substrate images.
* [ ] Reusable model-specific prefix states.
* [ ] Epistemic-prefix plus factual-text hybrid mode.
* [ ] Deterministic regeneration from a declared substrate release.
* [ ] Model/version compatibility manifests.
* [ ] Explicit invalidation when model architecture or tokenizer changes.

Conceptual architecture:

```text
QSOL-SUBSTRATE
      |
      v
canonical public records
      |
      +--------------------+
      |                    |
      v                    v
 textual capsule      model-specific projection
      |                    |
      v                    v
 factual context      latent/prefix/KV state
      \                    /
       \                  /
        +------ model ----+
```

A model-specific latent projection must never replace the canonical public
substrate or become an independent source of truth.

### Hybrid epistemic projection

Investigate whether model-specific latent state is more useful for carrying
stable interpretation rules than mutable factual information.

Candidate split:

```text
LATENT EPISTEMIC SUBSTRATE
    UNKNOWN != FALSE
    SATIRE != BIOGRAPHY
    REPLAY != EMPIRICAL VALIDATION
    FORMALIZATION != PHYSICAL TRUTH
    PRESERVE PROVENANCE
    RESOLVE CANONICAL IDS

            +

TEXTUAL FACTUAL SUBSTRATE
    identity
    projects
    publications
    chronology
    relationships

            +

USER TASK
```

This architecture keeps frequently changing public facts inspectable and textual
while testing whether stable epistemic behaviour can be efficiently projected
into temporary inference state.

## Phase 7 — Substrate Probe

Build a deterministic evaluation suite for measuring whether substrate delivery
actually improves model behaviour.

* [ ] Deterministic question set.
* [ ] Exact-known-fact tests.
* [ ] `unknown`-answer tests.
* [ ] Unsupported-assertion tests.
* [ ] Provenance preservation tests.
* [ ] Entity/alias disambiguation tests.
* [ ] Contradiction handling tests.
* [ ] Snapshot/freshness tests.
* [ ] Satire/fiction boundary tests.
* [ ] Formalization-versus-empirical-claim tests.
* [ ] Project relationship tests.
* [ ] Publication/DOI identity tests.
* [ ] Reproducible model report-card format.

### Comparison matrix

Compare the same models under:

```text
NAKED MODEL
vs
MICRO TEXT CAPSULE
vs
STANDARD TEXT CAPSULE
vs
FULL TEXT CAPSULE
vs
VECTOR-SELECTED CONTEXT
vs
LATENT / KV-PREFIX SUBSTRATE
vs
EPISTEMIC PREFIX + FACTUAL TEXT
vs
TOOL-ENABLED RETRIEVAL
```

Measure:

* [ ] Factual accuracy.
* [ ] Unsupported assertion rate.
* [ ] `UNKNOWN` precision.
* [ ] `UNKNOWN` recall.
* [ ] Alias resolution accuracy.
* [ ] Provenance fidelity.
* [ ] Contradiction handling.
* [ ] Claim-boundary preservation.
* [ ] Context/token efficiency.
* [ ] Substrate uplift over naked-model baseline.
* [ ] Hallucination reduction relative to baseline.

A central research question is:

> How much substrate is enough?

A compact, well-structured substrate may outperform a much larger undifferentiated
context dump.

## Phase 8 — Release discipline

* [ ] Semantic versioning policy.
* [ ] Release manifests.
* [ ] Canonical substrate snapshot identity.
* [ ] Immutable probe snapshots.
* [ ] Release fingerprints.
* [ ] Toolless capsule fingerprints.
* [ ] Vector-index fingerprints.
* [ ] Model-specific projection manifests.
* [ ] Compatibility metadata for latent/KV artifacts.
* [ ] Reproducible build commands.
* [ ] Optional archival DOI workflow.

Canonical substrate releases and derived projections must remain distinguishable.

Example:

```text
Canonical substrate:
QSOL-SUBSTRATE v1.2.0
commit=<git-sha>
sha256=<canonical-fingerprint>

Derived artifact:
profile=toolless-standard
or
projection=qwen3-8b-kv-prefix
source_substrate=v1.2.0
source_sha256=<canonical-fingerprint>
artifact_sha256=<derived-artifact-fingerprint>
```

The roadmap is intentionally incremental.

A substrate should become more portable, more compact, and more useful without
becoming less inspectable or less trustworthy.

The canonical public substrate remains the source of truth.

Everything else — prose bundles, vector indexes, adapters, soft prompts,
KV caches, and model-specific latent projections — is a reproducible projection
of that source.
