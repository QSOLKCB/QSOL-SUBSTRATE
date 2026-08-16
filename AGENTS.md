# AGENTS.md

## Repository purpose

QSOL-SUBSTRATE is a public, vendor-neutral context substrate for AI systems. Changes must preserve the distinction between human prose and canonical machine-readable contracts.

## Mandatory agent rules

1. Treat `ai/bootstrap.json` as the machine entrypoint.
2. Treat structured files under `ai/` as normative when they conflict with explanatory prose.
3. Do not add private, sensitive, credential-bearing, unpublished, or ambiguously public information.
4. Public export is explicit-allow only. Ambiguous visibility fails closed.
5. Absence from this repository means `unknown` or `unavailable`, never `false`.
6. Never invent relationships between people, repositories, publications, claims, or projects.
7. Preserve epistemic classification. Do not promote inference, hypothesis, fiction, satire, simulation, or self-report to established fact.
8. Prefer current primary repositories and publication records over cached substrate summaries.
9. Exact release identity should use DOI, version, tag, and commit where available.
10. Model adapters must not alter canonical facts. They may change transport format only.
11. Do not design prompts that bypass or weaken model safety controls.
12. Keep vendor-specific behaviour isolated under `adapters/`.
13. Machine JSON must remain valid UTF-8 JSON with stable field names.
14. New normative fields require schema and documentation updates.
15. When evidence is insufficient or conflicting, preserve uncertainty explicitly.
16. Phase 7 probe cases, expected answers, model runs, report cards, and comparison artifacts are evaluation material, not canonical public facts.
17. Never present the Phase 7 scoring oracle as an empirical model result; `execution_kind=scoring_oracle` is scorer self-test evidence only.
18. Empirical Phase 7 comparisons must bind the same probe-bundle and substrate identity and use the same model revision for naked-baseline uplift.
19. Do not label a textual prompt simulation as a latent/KV/LoRA execution; model-specific projection claims require the Phase 6 compatibility identity and actual runtime evidence.
20. Mixed-register claims are evaluated claim-locally; supported neighbouring text never supplies provenance.
21. Keep primary epistemic status separate from satire/fiction/register annotations.
22. Phase 9 consumer evaluations are `derived_evaluation`, not canonical evidence, and may not cite themselves as factual authority.
23. Empirical MIXED-REGISTER/1 comparisons require the same complete evaluation-bundle fingerprint, substrate identity, provider/model ID, and immutable model revision; scoring-oracle runs are excluded.

## Documentation split

- Human prose: `README.md`, `docs/`, `CONTRIBUTING.md`, `ROADMAP.md`, `SECURITY.md`, `CHANGELOG.md`.
- Machine contracts: `ai/`, `schema/`.
- Transport/adaptation guidance: `adapters/`.
- Deterministic evaluation source material: `probe/`.

## Change discipline

For changes affecting machine semantics, update all relevant layers in the same change:

- canonical contract;
- JSON schema when applicable;
- human explanation;
- changelog;
- tests/validation once tooling exists.

Do not silently change the meaning of an existing epistemic state or trust level.

For Phase 7 changes, also preserve the boundary between **probe protocol validation** and **empirical model evidence**. A passing scorer, a perfect oracle, or a successful context build does not imply model uplift.

## Security posture

This repository is public by design. Treat every committed byte as permanently public. Never commit secrets, private context exports, access tokens, private URLs, unpublished personal data, or raw private-source snapshots.
