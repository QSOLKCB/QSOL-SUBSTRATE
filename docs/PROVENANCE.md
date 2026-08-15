# Provenance

A context substrate is only as trustworthy as its ability to distinguish source, interpretation, and uncertainty.

## Provenance goals

Each substantive public record should identify enough provenance to answer where the information came from, what kind of source it is, when it was observed or published, what version/release/DOI/tag/commit identifies it, and whether the substrate is repeating a source, summarising it, or inferring from it.

## Preferred source classes

For public software and research, prefer canonical repository files, Git tags and releases, release artifacts, DOI landing records, authored papers and specifications, and first-party project documentation.

Secondary summaries are useful for discovery but should not silently outrank primary evidence.

## Live locator versus snapshot evidence

`sources/index.json` deliberately separates two ideas:

- `url` is a **live discovery locator** that may resolve to newer primary-source state later;
- `snapshot` records the evidence revision used by the declared substrate snapshot.

For repository documents, the snapshot stores an exact Git commit and commit-pinned URL. For release records, it stores the release tag commit together with the release tag and release identifier. Public identity records may use a captured API identity tuple when no Git commit exists.

This prevents a future `blob/main/...` change from silently rewriting the historical evidence behind an immutable substrate release.

## Epistemic classification

Provenance and epistemic state are related but not identical. A source can be authentic while the conclusion drawn from it is still an inference. A repository commit can prove that text existed at a commit; it does not automatically prove every scientific claim contained in that text.

Canonical `source` records therefore satisfy the shared record contract (`id`, `record_type`, `visibility`, and `epistemic_state`) while retaining source-class and snapshot metadata specific to provenance.

## Staleness

The substrate is versioned context. If a live primary source has changed after the substrate snapshot, consumers should prefer the live source for current state while retaining the pinned snapshot evidence for reproducibility and historical audit.

A newer source may supersede the current-state conclusion; it must not retroactively alter what evidence the older substrate snapshot used.

## Deliberate fiction and satire

QSOL projects may contain satire, fictional framing, game lore, personas, simulations, or deliberately absurd material. Provenance should preserve that classification rather than allowing a model to reinterpret fiction as biography or empirical fact.
