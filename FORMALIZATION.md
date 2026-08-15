# QSOL-SUBSTRATE v1.0.0 — Formal Specification

**Title:** QSOL-SUBSTRATE: A Deterministic, Provenance-Aware Public Context Substrate for AI Systems  
**Version formalized:** 1.0.0  
**Release tag:** `v1.0.0`  
**Release commit:** `4483582173abf62f61bcc18076b22c1db10b26ca`  
**Canonical substrate SHA-256:** `fb6e7a694ff1279af67d4aaf776e232e31025d9737011f6768fdc79c0f63eb25`  
**Release date:** 2026-08-15  
**Creator:** Trent Slade (QSOL-IMC / QSOLKCB)  
**ORCID:** `0009-0002-4515-9237`  
**License:** Apache-2.0

## Abstract

QSOL-SUBSTRATE is a public, vendor-neutral context substrate for artificial-intelligence systems. It defines a deterministic external knowledge layer for identity, terminology, projects, publications, provenance, relationships, chronology, and epistemic boundaries while preserving a strict separation between canonical public facts and derived delivery mechanisms. The system includes an explicit-allow private-to-public export boundary, schema and cross-file validation, deterministic fingerprints, portable model adapters, tool-less cold-boot capsules, vector retrieval, model-specific latent/prefix experiment contracts, a deterministic evaluation suite, Australian-pragmatics probes, and release chain-of-custody.

The principal semantic invariant is that **absence from the public substrate means unavailable, not false**. Canonical records carry explicit epistemic states and provenance. Derived adapters, capsules, embeddings, indexes, projection recipes, evaluation reports, release manifests, and archive records may transport, compress, retrieve, test, or attest to canonical information, but they do not acquire canonical fact authority merely by existing.

This document formalizes the v1.0.0 software architecture and its epistemic contract. It is a specification of software semantics and reproducibility constraints; it is not a claim that every mathematical statement below has been mechanically proved in a theorem prover, nor is a formal software invariant evidence of an empirical claim about a physical system or model behavior.

---

## 1. Release anchor

Let the immutable release object be

\[
R_0 = (v, g, h_C)
\]

where

- \(v = \texttt{1.0.0}\),
- \(g = \texttt{4483582173abf62f61bcc18076b22c1db10b26ca}\), and
- \(h_C = \texttt{fb6e7a694ff1279af67d4aaf776e232e31025d9737011f6768fdc79c0f63eb25}\).

All claims in this formalization about the released software refer to that tag/commit pair unless a later version is explicitly named.

The v1.0.0 canonical public payload is represented by the repository-declared canonical files:

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

The payload is **selective, public, and intentionally incomplete**.

---

## 2. Core sets and functions

Define:

- \(U\): universe of possible claims about the QSOL ecosystem;
- \(C \subset U\): claims explicitly represented by the canonical public substrate;
- \(S\): public source/provenance registry;
- \(I\): canonical identifiers;
- \(A\): aliases;
- \(G\): directed relationship graph over canonical identifiers;
- \(T\): chronology records;
- \(E\): epistemic-state set;
- \(V\): visibility states used by the export boundary;
- \(\kappa\): canonical serialization function;
- \(H\): SHA-256 digest function.

The epistemic-state set is

\[
E = \{\text{known},\text{retrieved},\text{inferred},\text{unknown},\text{conflict},\text{fiction}\}.
\]

These values are **epistemic species**, not numeric confidence bins.

For a canonical record \(x\), let

\[
\epsilon(x) \in E
\]

be its epistemic state, and let

\[
P(x) \subseteq S
\]

be its declared public provenance references when applicable.

The canonical substrate fingerprint is

\[
h_C = H(\kappa(C)).
\]

For v1.0.0, \(h_C\) is the SHA-256 value given in Section 1.

---

## 3. Partial-information semantics

QSOL-SUBSTRATE uses an open-world/partial-information rule for omission.

For an arbitrary proposition \(p \in U\):

\[
p \notin C \not\Rightarrow \neg p.
\]

Instead, absence establishes only that the public substrate does not establish \(p\):

\[
p \notin C \Rightarrow \operatorname{availability}_C(p)=\text{unavailable}.
\]

Therefore:

```text
ABSENCE_FROM_PUBLIC_SUBSTRATE != FALSE
UNKNOWN != FALSE
```

A consumer MUST NOT turn a missing record, field, edge, publication, event, or alias into a negative fact.

---

## 4. Epistemic typing

The canonical interpretation rules are:

```text
KNOWN      = explicitly established by canonical substrate or stronger evidence
RETRIEVED  = obtained from cited external primary evidence
INFERRED   = reasoned from evidence but not explicitly established
UNKNOWN    = not established
CONFLICT   = relevant evidence cannot currently be reconciled
FICTION    = deliberately fictional, satirical, simulated, or role-play content
```

The following non-equivalences are normative:

\[
\text{inferred} \neq \text{known}
\]

\[
\text{unknown} \neq \text{false}
\]

\[
\text{conflict} \neq \text{permission to choose a preferred source}
\]

\[
\text{fiction} \neq \text{biography}
\]

\[
\text{formalization} \neq \text{empirical validation}
\]

An AI system may report an inference as an inference. It may not promote that inference to `known` merely because it is plausible.

---

## 5. Provenance semantics

For a record \(x\) whose contract requires provenance, validity requires that every declared source reference resolve in the public source registry:

\[
\forall s \in P(x),\; s \in S.
\]

A dangling provenance reference invalidates the substrate under the validator.

Provenance is not transferable by semantic similarity. If \(x\) cites \(s\), a nearby embedding or related record does not thereby inherit \(s\) as evidence.

```text
SIMILARITY != PROVENANCE
NEAREST_NEIGHBOR != EVIDENCE
```

---

## 6. Canonical identifiers and aliases

Let \(i \in I\) be a canonical identifier and \(a \in A\) an alias.

Resolution MUST prefer canonical identity before alias convenience:

\[
\operatorname{resolve}(q)=i
\]

only when the alias mapping is unambiguous under the validated substrate.

Alias collisions fail closed. An unresolved alias does not authorize a guessed identity.

---

## 7. Public/private export boundary

Let \(C_p\) denote private working context and let \(D\) be an explicit allow directive set. Let field visibility be

\[
\nu(f) \in \{\text{allow},\text{deny},\text{unknown}\}.
\]

The public export function \(X\) is permitted to emit a private field \(f\) only if

\[
\nu(f)=\text{allow}
\]

and the directive identifies the exact source object, allowed field, public target, and acceptable public provenance.

Thus:

\[
\nu(f)\in\{\text{deny},\text{unknown}\}\Rightarrow f\notin X(C_p,D).
\]

This is the fail-closed rule:

```text
EXPLICIT_ALLOW_ONLY
UNKNOWN_VISIBILITY => DO_NOT_EXPORT
```

The default public grant set is empty.

---

## 8. Validation acceptance predicate

Let \(\mathcal{V}(C)\) be the canonical substrate validation predicate.

\[
\mathcal{V}(C)=\text{true}
\]

only when all required schemas and cross-file invariants succeed, including canonical-ID integrity, provenance closure, alias consistency, DOI uniqueness, relationship endpoints, chronology ordering, release-source consistency, public-boundary checks, secret/private-reference checks, and deterministic fingerprint generation.

Unresolved integrity errors are rejecting conditions, not warnings that silently permit publication.

---

## 9. Derived projection family

Define a projection

\[
\Pi_j(C,r)
\]

as a deterministic or model-bound representation derived from canonical substrate \(C\) under recipe/configuration \(r\).

QSOL-SUBSTRATE v1.0.0 defines projection classes including:

- portable transport adapters;
- tool-less MICRO/STANDARD/FULL capsules;
- deterministic vector records and embeddings;
- retrieval-selected factual context;
- latent/prefix experiment recipes and compatibility identities;
- probe/evaluation bundles;
- release manifests and archival metadata.

For every derived projection:

\[
\operatorname{authority}(\Pi_j(C,r)) \leq \operatorname{authority}(C).
\]

A projection may omit, reformat, index, transport, or select canonical material according to its contract. It MUST NOT obtain authority to invent or redefine canonical facts.

```text
CANONICAL_TRUTH != DERIVED_PROJECTION
FACT_REDEFINITION_BY_PROJECTION = FORBIDDEN
```

---

## 10. Tool-less capsules

Let \(L_b(C)\) be a tool-less capsule generated under portable-token budget \(b\).

The v1.0.0 declared budgets are:

```text
MICRO      8192
STANDARD  24576
FULL     131072
```

Selection occurs at whole-record granularity. Dependency closure requires included public provenance and relationship endpoints to remain resolvable.

For FULL:

\[
L_{FULL}(C)=C_{projection}
\]

for the complete canonical payload projection defined by the capsule contract, or the build fails.

For compact profiles, omission has the same partial-information semantics as the canonical store:

\[
x\notin L_b(C) \not\Rightarrow \neg x.
\]

---

## 11. Vector retrieval

Let \(\phi(x)\in\mathbb{R}^{256}\) be the deterministic `qsol-hash-embed-v1` representation of canonical chunk \(x\), encoded as float16 in the reference bundle.

Let query retrieval be

\[
R(q,k)=\operatorname{topk}_{x\in C}\operatorname{sim}(\phi(q),\phi(x)).
\]

The returned similarity order is a **selection mechanism only**.

\[
\operatorname{sim}(q,x) \not\Rightarrow \operatorname{truth}(x)
\]

and

\[
\operatorname{sim}(q,x) \not\Rightarrow \operatorname{confidence}(x).
\]

Before delivery, selected records are closed over required public provenance and relationship dependencies. Canonical IDs, source references, visibility, epistemic state, and canonical payload objects remain outside the embedding coordinates.

---

## 12. Model-specific latent and prefix projections

A model-specific projection artifact is valid only under an exact compatibility identity. The compatibility tuple includes at least:

\[
M=(k,m,v_m,a,t,h_t,c,d,l,n,h,k_v,p,q)
\]

where the tuple binds projection kind, model identifier/revision, architecture, tokenizer identity/hash, context size, hidden dimensions, layer/head geometry, KV layout, precision, and quantization identity.

Compatibility is equality-sensitive:

\[
M_1 \neq M_2 \Rightarrow \text{artifact reuse is invalid unless a new compatibility rule explicitly establishes otherwise}.
\]

A recipe for LoRA, soft prompts, virtual tokens, KV prefill, or reusable prefix state is not evidence that such an artifact was trained or executed.

```text
RECIPE != TRAINED_ARTIFACT
COMPATIBILITY_METADATA != EXECUTION_EVIDENCE
```

---

## 13. Substrate Probe

Let \(Q\) be the deterministic Phase 7 probe set. In v1.0.0:

\[
|Q|=48
\]

with 24 substrate factual/epistemic probes and 24 YEAH-NAH/1 pragmatic probes.

The comparison condition set is:

\[
K=\{\text{naked},\text{micro},\text{standard},\text{full},\text{vector},\text{latent-prefix},\text{hybrid},\text{tool-enabled}\}.
\]

Reports may measure factual correctness, unsupported assertions, UNKNOWN precision/recall, alias resolution, provenance fidelity, contradiction handling, claim-boundary preservation, token efficiency, hallucination reduction, pragmatics classification, hostility false positives, severity preservation, and confidence calibration.

The deterministic scoring oracle verifies scorer plumbing only:

```text
SCORING_ORACLE != EMPIRICAL_MODEL_RESULT
```

An empirical comparison MUST bind the same probe-bundle and substrate identities and MUST use the same model identity when computing uplift from the naked baseline.

---

## 14. YEAH-NAH/1 pragmatics contract

The Australian-pragmatics probe preserves these rules:

```text
SURFACE_MEANING != NECESSARILY_INTENDED_MEANING
SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED
UNCERTAIN != SARCASTIC
BANTER != HOSTILITY
UNDERSTATEMENT != LOW_SEVERITY
CONTEXT > TOKEN_POLARITY
```

An unconfirmed sarcasm classification remains an inference. Speaker confirmation may establish the communicative intent as known for the relevant utterance. The probe also includes controls for genuine hostility and ambiguous utterances so that cultural competence is not reduced to “assume every Australian is sarcastic.”

---

## 15. Release identity and chain-of-custody

Let a release identity be

\[
\mathcal{R}=(v,d,g,h_C,h_A,h_L,h_V,h_P,h_Q,h_R)
\]

where:

- \(v\): SemVer release label;
- \(d\): snapshot date;
- \(g\): exact Git source commit;
- \(h_C\): canonical substrate fingerprint;
- \(h_A\): adapter bundle fingerprint;
- \(h_L\): tool-less bundle fingerprint;
- \(h_V\): vector bundle fingerprint;
- \(h_P\): model-projection bundle fingerprint;
- \(h_Q\): immutable probe bundle fingerprint;
- \(h_R\): aggregate release fingerprint.

The release label does not replace snapshot identity:

```text
RELEASE_VERSION != SNAPSHOT_IDENTITY
CANONICAL_FINGERPRINT != DERIVED_ARTIFACT_FINGERPRINT
ARCHIVE_DOI != CANONICAL_FACT_AUTHORITY
```

Component manifests are insufficient by themselves. Release sealing revalidates the corresponding component bytes before accepting their fingerprints.

A DOI, when assigned, identifies an archival record. It does not retroactively establish or modify a canonical substrate fact.

---

## 16. Normative invariants

The following invariants summarize the v1.0.0 contract.

**I1 — Omission is not negation**

\[
x\notin C \not\Rightarrow \neg x.
\]

**I2 — Unknown is not false**

\[
\text{unknown}\neq\text{false}.
\]

**I3 — Inference is not knowledge**

\[
\text{inferred}\neq\text{known}.
\]

**I4 — Conflict is preserved**

Unreconciled evidence remains `conflict`; a consumer may not silently choose a preferred source.

**I5 — Fiction is typed**

Fictional or satirical content may not be promoted into biography or event history.

**I6 — Provenance closure**

Required public source references must resolve.

**I7 — Explicit-allow export**

Private material crosses the boundary only through explicit field-level authorization.

**I8 — Fail closed**

Unknown visibility, unresolved integrity, or ambiguous release identity rejects the operation.

**I9 — Canonical serialization determines canonical fingerprint**

Equivalent canonical content serializes deterministically under the declared canonicalization contract before hashing.

**I10 — Projection non-authority**

Adapters, capsules, vectors, latent recipes, reports, release manifests, and archive metadata are not independent canonical fact stores.

**I11 — Similarity is not truth**

Vector similarity selects candidates; canonical records and their provenance remain evidence.

**I12 — Exact model compatibility**

Model-specific projection artifacts are invalidated by incompatible changes in model, tokenizer, geometry, KV layout, precision, or quantization identity.

**I13 — Oracle is not empirical evidence**

A deterministic perfect-answer run cannot be represented as a real model benchmark.

**I14 — Pragmatics remains epistemically typed**

Unconfirmed sarcasm/deadpan/banter classifications remain inferred or uncertain according to the probe contract.

**I15 — Release identity is composite**

A SemVer label alone is insufficient to identify the exact canonical and derived state.

**I16 — Archive identity is metadata**

A DOI improves persistence and citation but does not redefine canonical truth.

---

## 17. AI-consumer algorithm

A conforming AI consumer should execute the following conceptual procedure:

```text
1. LOAD ai/bootstrap.json
2. FOLLOW declared machine load order
3. RESOLVE canonical IDs before aliases where possible
4. READ epistemic_state and provenance before asserting a claim
5. IF information is absent:
       return unavailable / unknown
       DO NOT convert absence to false
6. IF evidence conflicts:
       preserve conflict
       DO NOT silently choose a preferred source
7. IF reasoning extends beyond explicit evidence:
       mark result inferred
8. IF content is fictional/satirical/simulated:
       preserve that boundary
9. IF current state is required and snapshot is insufficient:
       retrieve current primary evidence when tools exist
       otherwise state the snapshot limit and return unknown where necessary
10. TREAT adapters, capsules, embeddings, projections, reports, and DOI metadata as derived carriers/attestations, not new canonical truth
```

This algorithm is intentionally conservative. The substrate is designed to reduce unsupported invention, not to maximize the number of claims a model can emit.

---

## 18. Reproducibility contract

For release-derived artifacts, reproducibility requires at least:

1. exact Git source revision;
2. clean reproducibility-relevant source tree;
3. canonical validation success;
4. deterministic canonical fingerprint;
5. deterministic reconstruction of applicable derived bundles;
6. component validation over actual bytes, not manifest assertions alone;
7. exact snapshot and release identity binding;
8. deterministic release-manifest validation.

The repository CI for the v1.0.0 release line completed the hardened regression suite with 195 passing tests before the stable release tag was created.

---

## 19. Scope and non-claims

QSOL-SUBSTRATE v1.0.0 does **not** claim:

- that its public payload is exhaustive;
- that absence establishes falsity;
- that vector similarity establishes truth or confidence;
- that latent/prefix recipes imply trained weights or executed KV states;
- that scoring-oracle performance is empirical model performance;
- that formalized software invariants establish physical truth;
- that a DOI creates new canonical knowledge;
- that private QSOL-CONTEXT can be reconstructed from public omissions.

The formalization is therefore a **software, provenance, and epistemic-interface specification**.

---

## 20. Discovery vocabulary

For indexing, retrieval, and scholarly discovery, QSOL-SUBSTRATE v1.0.0 is associated with the following concepts and aliases:

```text
AI context substrate
context engineering
large language model context
LLM context
machine-readable knowledge substrate
epistemic provenance
epistemic state
open-world semantics
unknown != false
deterministic AI context
AI hallucination reduction
retrieval-augmented generation
RAG
vector retrieval
model adapters
tool-less AI context
cold-boot context
AI provenance
software reproducibility
release chain-of-custody
latent prefix
KV cache compatibility
AI evaluation
Australian sarcasm detection
Australian pragmatics
YEAH-NAH/1
QSOL
QSOL-SUBSTRATE
```

---

## 21. Canonical citation target

Until a Zenodo DOI is assigned, the exact v1.0.0 release should be identified by:

```text
QSOLKCB/QSOL-SUBSTRATE
Version: 1.0.0
Tag: v1.0.0
Commit: 4483582173abf62f61bcc18076b22c1db10b26ca
Canonical substrate SHA-256: fb6e7a694ff1279af67d4aaf776e232e31025d9737011f6768fdc79c0f63eb25
Release: https://github.com/QSOLKCB/QSOL-SUBSTRATE/releases/tag/v1.0.0
```

After archival publication, the Zenodo DOI should be added as archival/citation metadata without altering the meaning of the canonical substrate fingerprint.

---

## 22. Compact statement

The complete architecture can be reduced to one sentence:

> **The canonical substrate is truth storage; everything else is a validated projection, retrieval mechanism, experiment, evaluation, transport, or archival attestation.**
