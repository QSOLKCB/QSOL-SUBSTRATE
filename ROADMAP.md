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

Phase 1 establishes the canonical public knowledge layer. The registry is selective rather than exhaustive: absence from the substrate means unavailable, not false.

## Phase 2 — Export pipeline

- [x] Define explicit-allow export policy from private QSOL-CONTEXT.
- [x] Add field-level visibility rules.
- [x] Add redaction and secret scanning.
- [x] Add deterministic canonicalisation.
- [x] Add export manifest and fingerprint.
- [x] Fail closed on unknown visibility or provenance.
- [x] Preserve public/private omission semantics during export.
- [x] Guarantee that generated public records contain no private source references.

The export pipeline treats publication as an explicit act. Private context never becomes public merely because a field was not explicitly marked private. The shipped allowlist contains zero private-to-public publication grants.

## Phase 3 — Validation and CI

- [x] JSON Schema validation.
- [x] Referential-integrity validation.
- [x] Provenance validation.
- [x] Alias collision checks.
- [x] DOI uniqueness checks.
- [x] Relationship endpoint validation.
- [x] Chronology ordering validation.
- [x] Public-boundary checks.
- [x] Secret/private-reference scanning.
- [x] SHA-256 substrate fingerprint.
- [x] GitHub Actions validation workflow.

Validation fails closed when canonical identity, provenance, visibility, relationships, chronology, publication/release identity, or the public boundary cannot be resolved safely. The integrity validator is deliberately network-free: live-source freshness and frozen-snapshot consistency remain separate concerns.

## Phase 4 — Portable model adapters

- [x] Generic single-file substrate bundle.
- [x] Grok chat bootstrap.
- [x] xAI retrieval export.
- [x] Grok Build project rules/skill export.
- [x] Sider prompt/knowledge-base bundle.
- [x] Ollama Modelfile/system-context bundle.
- [x] OpenAI-compatible API bundle.
- [x] Anthropic-compatible context bundle.
- [x] Model-independent adapter manifest.
- [x] Record exact substrate version, commit, and adapter identity for reproducible runs.

Adapters are disposable transport layers. They may change formatting and delivery, but must never redefine canonical substrate facts. Phase 4 generates all adapter knowledge from one byte-identical canonical projection and records snapshot identity, source commit, substrate SHA-256, projection SHA-256, adapter identity, per-file hashes, and an aggregate adapter-bundle fingerprint.

## Phase 5 — Toolless Substrate Capsule

Create a deterministic, self-contained substrate representation for AI systems that have no browsing, retrieval, file-system, repository, or external tool access.

### Profiles

- [x] `MICRO` tool-less profile for small-context and 4B–8B class models.
- [x] `STANDARD` tool-less profile for general-purpose local and hosted models.
- [x] `FULL` tool-less profile for large-context models.
- [x] Deterministic token-budgeted compilation.
- [x] Priority-aware truncation that preserves epistemic rules before optional detail.
- [x] Strategic semantic redundancy for small models.
- [x] Inline critical claim boundaries with high-risk project records.

### Toolless cold boot

- [x] Add a compact cold-boot header declaring that the model has no tools.
- [x] Declare substrate snapshot date prominently.
- [x] Declare substrate version and SHA-256 fingerprint.
- [x] Require `UNKNOWN != FALSE`.
- [x] Require `INFERENCE != FACT`.
- [x] Require `SATIRE != BIOGRAPHY`.
- [x] Require `FORMALIZATION != PHYSICAL_TRUTH`.
- [x] Require models not to claim freshness beyond the substrate snapshot.
- [x] Require models to state snapshot limitations when current state cannot be verified.

Example invariant:

```text
IF_CURRENT_STATE_REQUIRED
AND_TOOLS_UNAVAILABLE
THEN:
    use snapshot only if sufficient;
    state snapshot date;
    do not claim currentness beyond snapshot;
    return UNKNOWN for unresolved post-snapshot state.
```

### Toolless serialization

- [x] Define a compact LLM-oriented substrate serialization.
- [x] Preserve canonical IDs and aliases.
- [x] Inline important relationships where this improves local comprehension.
- [x] Preserve publication and DOI identity.
- [x] Preserve provenance class and epistemic state.
- [x] Preserve chronology without requiring external lookup.
- [x] Avoid deeply nested structures where they waste context.
- [x] Generate all tool-less artifacts from the canonical substrate rather than maintaining duplicate facts manually.

Generated output:

```text
dist/toolless/
├── QSOL-SUBSTRATE-MICRO.txt
├── QSOL-SUBSTRATE-STANDARD.txt
├── QSOL-SUBSTRATE-FULL.txt
└── manifest.json
```

Phase 5 uses deterministic model-independent `qsol-portable-token-v1` build budgets: `MICRO=8192`, `STANDARD=24576`, and `FULL=131072`. These values control compilation only and are not claims about any vendor/model tokenizer.

Records are admitted only at whole canonical-item boundaries. Admission brings public `source_refs`, relationship endpoints, and other resolvable canonical-ID dependencies with the record, so compact profiles cannot gain space by leaving dangling provenance. Omitted material remains unavailable, not false.

The `FULL` profile must contain the complete canonical payload projection or the build fails closed. `MICRO` deliberately repeats the highest-risk epistemic rules for small-model robustness. Generated artifacts record the exact source commit, snapshot identity, canonical substrate SHA-256, deterministic portable token count, inclusion/omission counts, per-profile hashes, and aggregate capsule-bundle fingerprint.

The tool-less representation behaves as a frozen public context image: one artifact in, no external tools required, no freshness claims beyond the snapshot, and no invented lore to fill omissions.

## Phase 6 — Vector and Latent Substrate Projection

Explore whether the same canonical substrate can be projected into more compact machine representations without modifying the underlying canonical knowledge.

The canonical substrate remains vendor- and model-independent. Vector indexes, prefix states, caches, and learned adapters are disposable model-specific projections.

### Vector substrate

- [x] Define deterministic record chunking.
- [x] Generate deterministic reference embeddings for canonical substrate records.
- [x] Preserve canonical record IDs alongside every vector.
- [x] Preserve provenance and epistemic metadata outside the embedding itself.
- [x] Add deterministic nearest-neighbour retrieval experiments.
- [x] Compare vector-selected context against fixed textual profile budgets.
- [x] Evaluate whether retrieval can reduce prompt size without dropping provenance closure.
- [x] Add fail-closed deterministic rebuild validation for the complete vector bundle.

Generated output:

```text
dist/vectors/
├── records.jsonl
├── embeddings.f16
├── index.json
├── retrieval-report.json
└── manifest.json
```

Phase 6 uses `qsol-record-chunk-v1` for one-canonical-item-per-chunk record projection and `qsol-hash-embed-v1` as a dependency-free 256-dimensional float16 reference embedding backend. The reference backend exists to make network-free CI and retrieval contracts reproducible; it is not asserted to be equivalent to a learned semantic embedding model.

Embedding vectors are retrieval indexes, not canonical truth. Raw embedding coordinates must never be treated as meaningful factual context by an LLM without an explicit retrieval/projection mechanism.

Primary vector matches are closed over public provenance references and relationship endpoints before delivery. The reference retrieval report measures context size and expected-ID retrieval hits only; downstream model quality remains a Phase 7 measurement.

### Latent / prefix substrate

Phase 6 implements reproducible **experiment contracts** for model-specific substrate initialization. A checked item below means the recipe, source identity, compatibility requirements, invalidation behavior, and deterministic experiment payload are defined. It does **not** claim that generic repository CI trained model-specific weights or captured a universal KV cache.

- [x] Soft prompt / prefix-tuning experiment recipe.
- [x] Prompt-tuned virtual-token experiment recipe.
- [x] Model-specific epistemic LoRA experiment recipe.
- [x] Prefilled attention/KV-cache experiment recipe.
- [x] Reusable model-specific prefix-state experiment recipe.
- [x] Epistemic-prefix plus factual-text hybrid mode.
- [x] Deterministic regeneration from declared snapshot/version + commit + substrate SHA-256.
- [x] Model/version compatibility manifest schema and compatibility checker.
- [x] Explicit invalidation when model revision, architecture, tokenizer, dimensions, attention layout, or KV layout changes.
- [x] Deterministic validation of the model-projection experiment bundle.

Generated output:

```text
dist/projections/
├── epistemic-prefix.txt
├── projection-recipes.json
├── delivery-matrix.json
└── manifest.json
```

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

A model-specific latent projection must never replace the canonical public substrate or become an independent source of truth.

### Hybrid epistemic projection

Phase 6 fixes a deterministic candidate split:

```text
LATENT / PREFIX EPISTEMIC SUBSTRATE
    UNKNOWN != FALSE
    INFERENCE != FACT
    SATIRE != BIOGRAPHY
    REPLAY != EMPIRICAL VALIDATION
    FORMALIZATION != PHYSICAL_TRUTH
    PRESERVE PROVENANCE
    RESOLVE CANONICAL IDS

            +

TEXTUAL / RETRIEVED FACTUAL SUBSTRATE
    identity
    projects
    publications
    chronology
    relationships

            +

USER TASK
```

- [x] Define deterministic textual, epistemic-prefix, and hybrid delivery conditions for `YEAH-NAH/1`.
- [x] Keep identical pragmatic rule payloads across those Phase 7 comparison conditions.
- [x] Mark actual model-behaviour preservation/uplift measurement as Phase 7 work rather than inferring it from representation plumbing.

This architecture keeps frequently changing public facts inspectable and textual while testing whether stable epistemic behaviour can be efficiently projected into temporary inference state.

## Phase 7 — Substrate Probe

Build a deterministic evaluation suite for measuring whether substrate delivery actually improves model behaviour.

A checked Phase 7 item means the **probe corpus, response contract, scorer, metric, report-card format, or comparison protocol is executable and reproducible**. Generic repository CI does not claim that it ran hosted/open-weight models. Empirical model results require explicit model-run records and are separate evidence.

- [x] Deterministic question set.
- [x] Exact-known-fact tests.
- [x] `unknown`-answer tests.
- [x] Unsupported-assertion tests.
- [x] Provenance preservation tests.
- [x] Entity/alias disambiguation tests.
- [x] Contradiction handling tests.
- [x] Snapshot/freshness tests.
- [x] Satire/fiction boundary tests.
- [x] Formalization-versus-empirical-claim tests.
- [x] Project relationship tests.
- [x] Publication/DOI identity tests.
- [x] Reproducible model-run and report-card formats.
- [x] Fail-closed deterministic probe-bundle validation.
- [x] Scoring-oracle self-test that is mechanically excluded from empirical comparisons.

Generated protocol bundle:

```text
dist/probes/
├── substrate-probe.jsonl
├── yeah-nah-1.jsonl
├── conditions.json
├── scoring-contract.json
└── manifest.json
```

The reference corpus contains 48 cases: 24 substrate epistemic/factual probes and 24 `YEAH-NAH/1` pragmatic probes. Model runs bind the exact probe-bundle SHA-256 and substrate identity before they can be scored.

### YEAH-NAH/1 — Australian Pragmatic Humour Probe

Build a deterministic cultural-pragmatics stress test for sarcasm, deadpan, understatement, banter, mock hostility, affectionate insult, and polarity reversal in Australian English. The purpose is not to assume that Australian speech is sarcastic; it is to test whether a model can avoid naive literalism without over-classifying ambiguous language as sarcasm or hostility.

- [x] Context-paired literal-versus-sarcastic utterance set.
- [x] Deadpan interpretation tests.
- [x] Understatement tests, including high-severity contexts expressed mildly.
- [x] Mock-hostility versus actual-hostility tests.
- [x] Affectionate-insult and familiar-banter tests.
- [x] Positive/negative polarity-reversal tests.
- [x] Contextual `yeah nah` / `nah yeah` interpretation tests.
- [x] Relationship-familiarity and conversational-context controls.
- [x] Sarcasm-confidence and uncertainty-calibration tests.
- [x] Speaker-confirmed sarcasm controls that distinguish explicit confirmation from model inference.
- [x] Cross-model comparison protocol for small open-weight and hosted models.
- [x] Compare naked, textual-substrate, vector-selected, latent-prefix, hybrid, and tool-enabled conditions.

Normative interpretation guards for the probe:

```text
SURFACE_MEANING != NECESSARILY_INTENDED_MEANING
SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED
UNCERTAIN != SARCASTIC
BANTER != HOSTILITY
UNDERSTATEMENT != LOW_SEVERITY
CONTEXT > TOKEN_POLARITY
```

Measure at least:

- [x] Sarcasm precision and recall.
- [x] Literal-meaning error rate.
- [x] Banter misclassification rate.
- [x] Hostility false-positive rate.
- [x] Understatement severity-preservation rate.
- [x] Confidence calibration via Brier score.
- [x] Cultural-context dependence and uplift from substrate delivery.

`YEAH-NAH/1` is a pragmatic interpretation probe, not a canonical-fact source. A sarcasm classification remains `inferred` unless the speaker or cited evidence explicitly confirms the intended meaning.

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

- [x] Factual accuracy.
- [x] Unsupported assertion rate.
- [x] `UNKNOWN` precision.
- [x] `UNKNOWN` recall.
- [x] Alias resolution accuracy.
- [x] Provenance fidelity.
- [x] Contradiction handling.
- [x] Claim-boundary preservation.
- [x] Context/token efficiency from the actual runner's tokenizer usage.
- [x] Substrate uplift over the same model's naked baseline.
- [x] Hallucination reduction relative to the same model's naked baseline.
- [x] Reject comparisons across mismatched probe/substrate identities.

A central research question is:

> How much substrate is enough?

A compact, well-structured substrate may outperform a much larger undifferentiated context dump. Phase 7 supplies the machinery to measure that claim; it does not fabricate the empirical answer.

## Phase 8 — Release discipline

- [ ] Semantic versioning policy.
- [ ] Release manifests.
- [ ] Canonical substrate snapshot identity.
- [ ] Immutable probe snapshots.
- [ ] Release fingerprints.
- [ ] Toolless capsule fingerprints.
- [ ] Vector-index fingerprints.
- [ ] Model-specific projection manifests.
- [ ] Compatibility metadata for latent/KV artifacts.
- [ ] Reproducible build commands.
- [ ] Optional archival DOI workflow.

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

A substrate should become more portable, more compact, and more useful without becoming less inspectable or less trustworthy.

The canonical public substrate remains the source of truth.

Everything else — prose bundles, vector indexes, adapters, soft prompts, KV caches, model-specific latent projections, and probe/report artifacts — is a reproducible projection or evaluation of that source.
