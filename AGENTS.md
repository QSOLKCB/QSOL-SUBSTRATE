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

## Documentation split

- Human prose: `README.md`, `docs/`, `CONTRIBUTING.md`, `ROADMAP.md`, `SECURITY.md`, `CHANGELOG.md`.
- Machine contracts: `ai/`, `schema/`.
- Transport/adaptation guidance: `adapters/`.

## Change discipline

For changes affecting machine semantics, update all relevant layers in the same change:

- canonical contract;
- JSON schema when applicable;
- human explanation;
- changelog;
- tests/validation once tooling exists.

Do not silently change the meaning of an existing epistemic state or trust level.

## Security posture

This repository is public by design. Treat every committed byte as permanently public. Never commit secrets, private context exports, access tokens, private URLs, unpublished personal data, or raw private-source snapshots.
