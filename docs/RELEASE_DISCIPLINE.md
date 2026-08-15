# Phase 8 — Release Discipline

Phase 8 freezes the distinction between **canonical substrate identity**, **release identity**, and **derived artifact identity**.

```text
RELEASE VERSION != SNAPSHOT IDENTITY
CANONICAL FINGERPRINT != DERIVED-ARTIFACT FINGERPRINT
ARCHIVE DOI != CANONICAL FACT AUTHORITY
CI RELEASE CANDIDATE != PUBLISHED RELEASE
```

The canonical public substrate remains the source of truth. Adapters, tool-less capsules, vectors, model-projection recipes, probe bundles, release manifests, and archive metadata are reproducible projections or attestations of that source.

## Semantic versioning

`release/policy.json` is the normative machine-readable release policy. Versions use SemVer 2.0.0 and Git tags use the `v` prefix.

- **major** — incompatible canonical schema, machine-contract, or release-contract change;
- **minor** — backward-compatible canonical, projection, probe, or release capability addition;
- **patch** — backward-compatible correction/hardening that does not weaken epistemic or provenance semantics;
- **prerelease** — candidate or CI identity only.

Channels are strict:

- `stable`: publishable and must not contain a prerelease identifier;
- `candidate`: non-publishable and must contain a prerelease identifier;
- `ci`: non-publishable and must use a `ci.*` prerelease identifier.

The CI contract uses `0.8.0-ci.0`. This is deliberately **not** a public release version claim.

## Snapshot identity

A release version is a label for a software release. It is not the identity of the underlying canonical knowledge snapshot.

Snapshot identity is derived from:

```text
snapshot_date
source_commit
substrate_sha256
```

The human-readable snapshot identifier is:

```text
snapshot-YYYY-MM-DD@sha256:<canonical-substrate-sha256>
```

A different release version may refer to the same canonical snapshot when only derived tooling changes. Conversely, a canonical payload change necessarily changes `substrate_sha256` even if a maintainer accidentally attempts to reuse a release label.

## Release bundle

After adapters, tool-less capsules, vectors, projections, and probes are built and validated, run:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"
python tools/build_release.py \
  --source-commit "$SOURCE_COMMIT" \
  --version 1.0.0 \
  --channel stable \
  --output dist/release

python tools/validate_release.py --bundle dist/release
```

Generated output:

```text
dist/release/
├── archive-metadata.json
├── build-plan.json
├── manifest.json
├── probe-snapshot.json
└── SHA256SUMS.txt
```

`manifest.json` binds:

- release version, channel, tag, and publishability;
- canonical snapshot date, source commit, snapshot ID, and substrate SHA-256;
- portable adapter manifest and bundle fingerprint;
- tool-less bundle fingerprint plus MICRO/STANDARD/FULL profile fingerprints;
- vector bundle fingerprint plus exact `index.json` and `embeddings.f16` fingerprints;
- projection bundle fingerprint plus the model-projection compatibility schema contract;
- immutable Phase 7 probe snapshot and bundle fingerprint;
- deterministic build-plan fingerprint;
- archival metadata fingerprint;
- aggregate release fingerprint.

`SHA256SUMS.txt` covers every file in the release bundle except itself.

## Fail-closed rules

Release construction refuses to proceed when:

1. `source_commit` is not a 40-character lowercase Git commit SHA;
2. the declared source commit does not equal checked-out `HEAD`;
3. tracked source files contain uncommitted changes;
4. a derived component was built from a different source commit;
5. a derived component points at a different canonical substrate fingerprint;
6. required derived manifests or vector artifacts are absent;
7. release policy, archive metadata, or release manifest schemas fail;
8. probe snapshot identity cannot be reproduced;
9. helper-file hashes or `SHA256SUMS.txt` disagree;
10. a deterministic rebuild produces different bytes.

Untracked generated `dist/` output does not make the source tree dirty. Tracked source changes do.

## Immutable probe snapshots

`probe-snapshot.json` records the exact Phase 7 probe bundle SHA-256, probe count, file hashes, source commit, and canonical substrate SHA-256. A release validator reconstructs this snapshot from `dist/probes/manifest.json` and rejects drift.

A probe result therefore means:

```text
MODEL RESULT
  -> exact probe snapshot
  -> exact canonical substrate identity
  -> exact release provenance
```

not merely “roughly the same questions from around that time.”

## Model-specific latent / KV artifacts

Generic repository CI still does not fabricate model-specific trained weights or universal KV caches. Phase 8 records the projection-bundle fingerprint and requires model-specific artifacts to retain the exact Phase 6 compatibility identity.

A future binary latent/KV artifact must preserve at least the compatibility dimensions enforced by `schema/model-projection-compatibility.schema.json`, including model revision, architecture, tokenizer identity/hash, dimensions, attention/KV layout, precision, and quantization identity.

Changing an incompatible dimension invalidates the artifact. Renaming the file does not make it compatible again. Nice try. :-)

## Reproducible build plan

`build-plan.json` contains the ordered, network-free repository commands required to reconstruct the validated derived layers and release metadata from the exact source commit. The plan is itself hashed into the release manifest.

The validator rebuilds the release metadata into a temporary directory and requires byte-for-byte equality.

## Optional archival DOI workflow

`archive-metadata.json` is generated in a Zenodo-compatible, deposition-ready form with `status=unassigned` and `doi=null` by default.

The intended workflow is:

1. build and validate the immutable release;
2. create the Git tag matching `manifest.release.tag`;
3. attach the canonical release and derived artifacts to a GitHub Release;
4. optionally archive the same release in Zenodo;
5. record the assigned DOI as archival metadata without changing the canonical substrate payload or pretending the DOI created new facts.

A DOI is an archive/citation identity. It is not a replacement for the source commit, canonical substrate fingerprint, or derived-artifact fingerprints.

## Verification hierarchy

For a claimed release, verify in this order:

```text
Git commit
  -> canonical substrate SHA-256
  -> derived component fingerprints
  -> immutable probe snapshot
  -> release SHA-256
  -> SHA256SUMS.txt
  -> optional archive DOI
```

The canonical substrate is truth storage.

The release manifest is chain-of-custody.

Everything else is a projection, evaluation, transport, or archive location.
