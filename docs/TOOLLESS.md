# Toolless Substrate Capsules

Phase 5 compiles QSOL-SUBSTRATE into deterministic, self-contained text artifacts for models that have **no browsing, retrieval, filesystem, repository, or external tool access**.

The capsules are derived artifacts. They do not replace the canonical public substrate and they do not redefine facts.

## Core contract

A tool-less run must behave as though the selected capsule is its complete available QSOL public context image.

```text
NO_TOOLS=true
UNKNOWN != FALSE
INFERENCE != FACT
SATIRE != BIOGRAPHY
FORMALIZATION != PHYSICAL_TRUTH
```

If current state after the declared snapshot date is required and cannot be resolved from evidence supplied directly in the task, the correct result is `UNKNOWN` plus the snapshot limitation.

A capsule must never claim that it browsed, retrieved, opened a repository, inspected a live release, or loaded a private context store.

## Generated profiles

```text
dist/toolless/
├── QSOL-SUBSTRATE-MICRO.txt
├── QSOL-SUBSTRATE-STANDARD.txt
├── QSOL-SUBSTRATE-FULL.txt
└── manifest.json
```

### MICRO

Budget: **8,192 qsol-portable-token-v1 units**.

Designed for small-context and 4B–8B-class models. Selection begins with epistemic/identity/terminology material and adds whole canonical records in deterministic priority order while preserving dependency closure.

MICRO deliberately repeats the four highest-risk epistemic guards at the end of the artifact. The redundancy is intentional: small models should encounter the same claim-boundary rules both before and after the factual substrate.

### STANDARD

Budget: **24,576 qsol-portable-token-v1 units**.

Designed for general-purpose local and hosted models. It expands project, publication, research-topic, relationship, chronology, and provenance coverage while retaining the same whole-record and dependency-closure rules.

### FULL

Budget: **131,072 qsol-portable-token-v1 units**.

FULL must include every canonical public payload item represented by the compiler. If the complete projection cannot fit the declared budget, the build fails closed rather than silently becoming a partial `FULL` profile.

## Portable token accounting

QSOL-SUBSTRATE does not use a vendor tokenizer to decide profile contents.

`qsol-portable-token-v1` is a deterministic budgeting contract:

1. normalize the candidate text using Unicode NFKC;
2. split it into Unicode word runs and individual non-whitespace punctuation/symbols;
3. charge each word run `ceil(UTF-8 bytes / 4)` units;
4. charge each punctuation/symbol one unit.

This count is **not** asserted to equal tokens from any particular OpenAI, Anthropic, xAI, Qwen, DeepSeek, Llama, Ollama, or other tokenizer. Runtime systems should measure their own model-specific token count separately when necessary.

The portable count exists so the same repository snapshot deterministically selects the same records independent of target model vendor.

## Priority-aware whole-record selection

The compiler never truncates a JSON record halfway through.

Priority order:

```text
P0  epistemic wrapper semantics, identity, terminology
P1  public context claims, projects, publications, research topics
P2  relationships, chronology, remaining wrapper semantics
P3  unreferenced source records
```

A record is admitted only when the record plus its unresolved dependency closure fits the selected profile budget.

Dependency closure includes:

- every included `source_ref`;
- both endpoints of every included relationship;
- canonical-ID references found inside included record fields.

Therefore a smaller profile may omit an otherwise useful relationship when its endpoints/provenance would not fit safely.

Omission always means **unavailable**, never false.

## Serialization

Capsules use a compact line-oriented format.

Each canonical item is serialized as:

```text
ITEM<TAB>kind<TAB>canonical-source-path<TAB>canonical-json-object
```

The JSON object is copied from the canonical substrate without factual transformation.

Wrapper-level canonical semantics such as selection/completeness statements are represented as `wrapper` items so FULL remains a semantic projection of the whole canonical payload rather than only its record arrays.

Relationships and chronology remain ordinary canonical objects with explicit IDs, provenance, and epistemic states. This avoids inventing a second knowledge schema simply for prompt delivery.

## Inline claim-boundary guards

For project records whose explicit tags indicate higher-risk interpretation domains, the compiler emits `BOUNDARY` lines immediately after the project record.

Examples:

```text
satire                  -> SATIRE != BIOGRAPHY
formalization / Lean 4  -> FORMALIZATION != PHYSICAL_TRUTH
AI observation/transcript/model evaluation
                        -> OBSERVED_OR_ARCHIVED_MODEL_OUTPUT != GENERAL_MODEL_IDENTITY
```

These lines are epistemic guards derived from explicit canonical project tags. They are not additional project facts.

The validator independently recomputes the expected guards from the canonical project records and rejects added, missing, or altered boundary lines.

## Build

```bash
python tools/build_toolless.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/toolless
```

The exact 40-character source commit is required because the canonical substrate fingerprint intentionally covers canonical public payload semantics, while the derived artifact identity must also record which repository revision generated it.

Inside the repository, output is restricted to exactly `dist/toolless`. The builder refuses repository source/tooling/contract paths such as `tools/`, `ai/`, or `projects/`, and it refuses symlinked output paths. Generated-artifact cleanup must never be able to remove canonical repository content.

CI explicitly checks out the revision used to build artifacts and stamps the exact `git rev-parse HEAD` value into adapter and capsule identity.

## Validation

```bash
python tools/validate_toolless_capsule.py --bundle dist/toolless
```

Validation checks:

- strict manifest schema;
- exact MICRO/STANDARD/FULL profile set;
- exact source commit format;
- protocol, schema, snapshot date/version, and canonical substrate fingerprint against `ai/manifest.json`;
- deterministic recomputation of MICRO/STANDARD/FULL record selection;
- deterministic recomputation of per-profile item counts, omission/truncation state, and `kind_counts`;
- complete byte-for-byte equality with the deterministic canonical renderer;
- deterministic portable token count and budget;
- exact canonical equality of every included `ITEM` object;
- source-reference closure;
- relationship endpoint closure;
- exact project boundary guards;
- MICRO semantic redundancy;
- FULL canonical completeness;
- regular non-symlink profile files that remain inside the bundle root;
- rejection of undeclared/extra bundle files;
- aggregate bundle fingerprint;
- fail-closed handling of malformed JSON, invalid UTF-8, and filesystem read errors.

The byte-for-byte renderer comparison is deliberately stronger than recognizing `ITEM` and `BOUNDARY` lines. Arbitrary prompt instructions, altered headers, removed-but-still-canonical records, or other extra text are invalid even if an attacker recomputes outer hashes and manifest counts.

Changing a fact and then recomputing the outer file hash is therefore insufficient: the complete artifact must still equal the deterministic rendering of current canonical state.

## Reproducible identity

`manifest.json` records:

```text
substrate version = snapshot-YYYY-MM-DD
source commit      = exact checked-out 40-character git SHA
substrate SHA-256  = canonical public payload fingerprint
capsule spec       = 1.0.0
portable tokenizer = qsol-portable-token-v1
profile budget/count/hash
aggregate bundle SHA-256
```

The snapshot date/version in a capsule is not self-authorizing metadata. Validation derives the expected identity from the repository's canonical machine manifest and rejects a capsule that merely claims to be newer.

Formal QSOL-SUBSTRATE release SemVer remains Phase 8 work. Until then, `snapshot-YYYY-MM-DD` plus exact commit and substrate fingerprint identifies the source state without conflating schema version with release version.

## Trust boundary

Toolless capsules are generated only from the **public canonical substrate**.

They do not read QSOL-CONTEXT, do not perform private-to-public export, and do not create publication authority. They preserve the same rule as the canonical repository:

> Absence from the public substrate means unavailable, not false.

The canonical repository remains the source of truth. Toolless capsules are disposable projections optimized for inference environments where the model cannot go and fetch anything else.
