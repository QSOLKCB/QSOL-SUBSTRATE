# Zenodo Deposition Guide — QSOL-SUBSTRATE v1.0.0

This file is the human-facing deposition checklist for the immutable GitHub release:

- **Release:** `v1.0.0`
- **Release commit:** `4483582173abf62f61bcc18076b22c1db10b26ca`
- **Release date:** 2026-08-15
- **Canonical substrate SHA-256:** `fb6e7a694ff1279af67d4aaf776e232e31025d9737011f6768fdc79c0f63eb25`

Do **not** move or recreate the `v1.0.0` tag to add metadata. Stable release identity is immutable under the Phase 8 release contract.

## Recommended record type

**Resource type:** Software

## Title

**QSOL-SUBSTRATE: A Deterministic, Provenance-Aware Public Context Substrate for AI Systems**

## Version

`1.0.0`

## Publication date

`2026-08-15`

## Creator

**Slade, Trent**  
Affiliation: **QSOL-IMC**  
ORCID: **0009-0002-4515-9237**

## License

**Apache-2.0**

## Language

**English (`eng`)**

## Description

QSOL-SUBSTRATE is a public, vendor-neutral context substrate for artificial-intelligence systems. It provides deterministic, provenance-aware public context for identity, terminology, projects, publications, relationships, chronology, and epistemic state while preserving a strict boundary between canonical public facts and derived delivery mechanisms.

Version 1.0.0 completes the Phase 0–8 roadmap: documentation and machine contracts; a canonical public substrate; explicit-allow private-to-public export; schema and cross-file validation; deterministic fingerprints; portable model adapters; tool-less MICRO/STANDARD/FULL cold-boot capsules; deterministic vector retrieval; model-specific latent/prefix experiment contracts; a 48-case Substrate Probe including the YEAH-NAH/1 Australian-pragmatics suite; and release chain-of-custody.

The central semantic rule is that **absence from the public substrate means unavailable, not false**. Epistemic states are explicitly typed as `known`, `retrieved`, `inferred`, `unknown`, `conflict`, or `fiction`. Derived adapters, capsules, embeddings, vector indexes, projection recipes, evaluation reports, release manifests, and archive metadata may transport, select, test, or attest to canonical information, but they do not become independent canonical fact authority.

The companion `FORMALIZATION.md` specifies the software semantics, open-world information model, epistemic invariants, explicit-allow export boundary, provenance closure, deterministic fingerprinting, projection non-authority, evaluation boundaries, Australian-pragmatics interpretation contract, model-projection compatibility, and release identity for v1.0.0.

## Notes

QSOL-SUBSTRATE v1.0.0 is anchored to Git commit `4483582173abf62f61bcc18076b22c1db10b26ca` and canonical substrate SHA-256 `fb6e7a694ff1279af67d4aaf776e232e31025d9737011f6768fdc79c0f63eb25`.

The canonical substrate is truth storage. Adapters, tool-less capsules, embeddings, vector indexes, latent/prefix recipes, probes, report cards, release manifests, and archive records are derived projections, experiments, evaluations, transports, or attestations.

The following distinctions are normative:

```text
ABSENCE_FROM_PUBLIC_SUBSTRATE != FALSE
UNKNOWN != FALSE
INFERENCE != FACT
FICTION != BIOGRAPHY
FORMALIZATION != EMPIRICAL_VALIDATION
NEAREST_NEIGHBOR != EVIDENCE
SCORING_ORACLE != EMPIRICAL_MODEL_RESULT
RELEASE_VERSION != SNAPSHOT_IDENTITY
ARCHIVE_DOI != CANONICAL_FACT_AUTHORITY
```

## Keywords

Use the following keywords as separate Zenodo keyword entries:

```text
artificial intelligence
large language models
LLM
AI context substrate
context engineering
machine-readable knowledge
epistemic provenance
epistemic state
open-world semantics
deterministic AI
retrieval-augmented generation
RAG
vector retrieval
model adapters
tool-less AI context
AI hallucination reduction
software reproducibility
release provenance
Australian pragmatics
sarcasm detection
YEAH-NAH/1
QSOL
QSOL-SUBSTRATE
```

## Related identifiers

1. **GitHub v1.0.0 release**  
   Identifier: `https://github.com/QSOLKCB/QSOL-SUBSTRATE/releases/tag/v1.0.0`  
   Relation: `isIdenticalTo`  
   Resource type: Software

2. **Exact release commit**  
   Identifier: `https://github.com/QSOLKCB/QSOL-SUBSTRATE/commit/4483582173abf62f61bcc18076b22c1db10b26ca`  
   Relation: `isIdenticalTo`  
   Resource type: Software

3. **Living source repository**  
   Identifier: `https://github.com/QSOLKCB/QSOL-SUBSTRATE`  
   Relation: `isSupplementTo`  
   Resource type: Software

## Files for a manual v1.0.0 Zenodo deposit

Recommended minimum:

1. the immutable GitHub `v1.0.0` source archive (`.zip` or `.tar.gz`);
2. `FORMALIZATION.md` as a companion formal specification;
3. optionally `CITATION.cff`, `.zenodo.json`, and `codemeta.json` as explicit metadata companions.

The formalization document is intentionally allowed to be deposited as a companion file describing the already-immutable v1.0.0 software object. It must not be used as a reason to move the original tag.

## Automatic GitHub → Zenodo route

The metadata files in this repository were prepared **after** the immutable `v1.0.0` tag. Therefore, do not assume that archiving that old tag through an automated integration will ingest metadata that is not present inside the tag snapshot.

For automated future release ingestion, merge this metadata/formalization change and prepare a subsequent release (for example a metadata-only patch release) using the following order:

1. choose the new release version and tag, for example `1.0.1` / `v1.0.1`;
2. **before creating the tag or GitHub release**, update `.zenodo.json`, `CITATION.cff`, and `codemeta.json` so their version and release/tag identifiers describe that new release rather than `1.0.0` / `v1.0.0`;
3. remove any stale `v1.0.0` exact-commit binding from metadata intended to describe the new release;
4. commit the updated metadata and formalization;
5. create the new tag and GitHub release **on that exact metadata commit**;
6. after the release commit SHA is known, record that exact SHA in the Zenodo record's related identifiers and in subsequent citation/archive metadata.

A metadata file cannot deterministically embed the SHA of the same Git commit that contains that file: changing the embedded SHA changes the commit SHA. Therefore the safe pre-tag requirement is **no stale commit identity**, followed by an external/post-publication binding to the exact tagged commit once it exists.

At minimum, the commit used for the automated release must actually contain:

```text
.zenodo.json
CITATION.cff
codemeta.json
FORMALIZATION.md
```

Never cut a follow-up release while those files still advertise `1.0.0`, `v1.0.0`, or the v1.0.0 release commit. Do not retag `v1.0.0`.

## After Zenodo assigns a DOI

Record the assigned DOI as archival/citation metadata. The DOI identifies the preserved record; it does not replace:

- the Git source commit;
- the canonical substrate SHA-256;
- the release tag;
- the component fingerprints;
- or the release chain-of-custody.

A DOI should be added to future citation metadata or a subsequent metadata release without changing the meaning of the v1.0.0 canonical fingerprint.
