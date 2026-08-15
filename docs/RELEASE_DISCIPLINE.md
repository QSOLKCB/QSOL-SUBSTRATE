# Phase 8 — Release Discipline

Phase 8 freezes the distinction between **canonical substrate identity**, **release identity**, and **derived artifact identity**.

```text
RELEASE VERSION != SNAPSHOT IDENTITY
CANONICAL FINGERPRINT != DERIVED-ARTIFACT FINGERPRINT
ARCHIVE DOI != CANONICAL FACT AUTHORITY
CI RELEASE CANDIDATE != PUBLISHED RELEASE
MANIFEST HASH != COMPONENT VALIDATION
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

Publishability is derived from the channel and is validated even when `validate_release.py --no-rebuild` is used. It is not a user-editable escape hatch.

The CI contract uses `0.8.0-ci.0`. This is deliberately **not** a public release version claim.

## Snapshot identity

A release version is a label for a software release. It is not the identity of the underlying canonical knowledge snapshot.

Snapshot identity is derived from all three normative identity fields:

```text
snapshot_date
source_commit
substrate_sha256
```

The human-readable snapshot identifier is:

```text
snapshot-YYYY-MM-DD@git:<40-char-source-commit>@sha256:<canonical-substrate-sha256>
```

Two commits on the same date with byte-identical canonical payloads therefore remain distinguishable exact snapshots when release/projection tooling differs.

## Release bundle

After adapters, tool-less capsules, vectors, projections, and probes are built, run:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"
python tools/build_release.py \
  --source-commit "$SOURCE_COMMIT" \
  --version 1.0.0 \
  --channel stable \
  --output dist/release

python tools/validate_release.py --bundle dist/release
```

Release construction re-runs every component validator before trusting any component manifest or bundle fingerprint. An unchanged manifest cannot hide modified adapter, capsule, vector, projection, or probe bytes.

Generated output:

```text
dist/release/
├── archive-metadata.json
├── build-plan.json
├── manifest.json
├── probe-snapshot.json
└── SHA256SUMS.txt
```

`manifest.json` binds release/channel/tag/publishability, the exact canonical snapshot, independently validated derived-component fingerprints, the immutable Phase 7 probe snapshot, reproducible build-plan identity, archive metadata, and the aggregate release fingerprint.

`SHA256SUMS.txt` covers every file in the release bundle except itself.

## Fail-closed rules

Release construction or validation refuses to proceed when:

1. `source_commit` is not a 40-character lowercase Git commit SHA;
2. the declared source commit does not equal checked-out `HEAD`;
3. tracked source files contain uncommitted changes;
4. an untracked file exists in a reproducibility source path such as `tools/`, `schema/`, release policy/contracts, canonical payloads, tests, or adapter source material;
5. an existing stable `v<version>` tag resolves to a different commit;
6. a derived component validator reports tampering or deterministic-rebuild drift;
7. a derived component was built from a different source commit or canonical substrate fingerprint;
8. release policy, archive metadata, or release manifest schemas fail;
9. channel and `publishable` disagree;
10. probe snapshot identity cannot be reproduced;
11. helper-file hashes or `SHA256SUMS.txt` disagree;
12. a deterministic release rebuild produces different bytes.

Generated `dist/` output is deliberately excluded from the untracked-source rule. Untracked source code or schemas are not.

## Stable tag collision rule

Stable release construction supports the documented build-before-tag workflow: a missing `v<version>` tag is allowed. If that tag already exists, however, it must resolve to the exact declared `source_commit`. Reusing a stable tag that points elsewhere fails closed.

## Immutable probe snapshots

`probe-snapshot.json` records the exact Phase 7 probe bundle SHA-256, probe count, file hashes, source commit, and canonical substrate SHA-256. The release validator reconstructs this snapshot from the validated probe bundle and rejects drift.

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

Changing model revision, architecture, tokenizer identity/hash, dimensions, attention/KV layout, precision, or quantization invalidates the artifact. Renaming the file does not make it compatible again. Nice try. :-)

## Reproducible build plan

`build-plan.json` contains the ordered **network-free repository commands** required to reconstruct validated derived layers and release metadata from the exact source commit.

Dependency acquisition is intentionally **not** a command in that plan. `requirements-validation.txt` dependencies must already be installed or supplied from an offline wheelhouse before the network-free plan begins. This prevents a supposedly offline recipe from silently consulting a package index on a clean machine.

The release validator rebuilds release metadata into a temporary directory and requires byte-for-byte equality.

## Optional archival DOI workflow

`archive-metadata.json` defaults to `status=unassigned` and `doi=null`.

When Zenodo reserves or publishes a DOI, rebuild the release metadata explicitly with that assignment:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"
python tools/build_release.py \
  --source-commit "$SOURCE_COMMIT" \
  --version 1.0.0 \
  --channel stable \
  --archive-status published \
  --doi 10.5281/zenodo.EXAMPLE \
  --output dist/release

python tools/validate_release.py --bundle dist/release
```

The assigned DOI/status are included in the deterministic build plan, archive metadata, release manifest, and checksums. Validation rebuilds with the same archive inputs, so assigned DOI metadata survives ordinary validation instead of requiring a manual JSON patch or `--no-rebuild` bypass.

A DOI is an archive/citation identity. It does not replace or modify the canonical substrate fingerprint.

## Verification hierarchy

For a claimed release, verify in this order:

```text
Git commit
  -> stable tag binding, if tag exists
  -> canonical substrate SHA-256
  -> full component validators
  -> derived component fingerprints
  -> immutable probe snapshot
  -> release SHA-256
  -> SHA256SUMS.txt
  -> optional archive DOI
```

The canonical substrate is truth storage.

The release manifest is chain-of-custody.

Everything else is a projection, evaluation, transport, or archive location.
