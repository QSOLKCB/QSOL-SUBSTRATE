# Review Closure Policy

This policy prevents unbounded automated-review loops while preserving correctness, scientific integrity, and explicit human merge authority.

## Core rule

```text
AUTOMATED_SEVERITY != MERGE_AUTHORITY
REVIEW_COUNT != SOFTWARE_QUALITY
HARDENING_OPPORTUNITY != CURRENT_PR_OBLIGATION
```

A P0/P1/P2 label from Codex or another automated reviewer is an input to triage, not an automatic merge blocker by itself.

## Two substantive review passes

### Pass 1 — correctness and contract review

Fix findings that are materially:

- `CORRECTNESS` — the implementation can produce a wrong result, corrupt state, violate a declared invariant, or fail an intended path;
- `SCIENTIFIC_CONTRACT` — the implementation can overstate evidence, weaken reproducibility/provenance, blur epistemic boundaries, or misrepresent the scientific contract;
- `REGRESSION` — the PR breaks behaviour that was previously required or validated.

`ROBUSTNESS` findings are fixed when they protect a realistic supported input/path or a declared fail-closed boundary.

### Pass 2 — regression and material-new-finding review

After Pass 1 fixes, perform one further substantive review of the materially changed head.

Fix:

- regressions introduced by Pass 1;
- genuinely new `CORRECTNESS` findings;
- genuinely new material `SCIENTIFIC_CONTRACT` findings;
- realistic `ROBUSTNESS` defects whose impact justifies inclusion in the current PR.

A review rerun against a trivially changed head does not reset this budget. The count is of substantive review rounds, not bot invocations.

## Closure triage

After two substantive automated-review passes, the PR enters **closure triage**.

Every new finding must be classified before work is undertaken:

| Class | Default action |
|---|---|
| `CORRECTNESS` | Fix now |
| `SCIENTIFIC_CONTRACT` | Usually fix now |
| `REGRESSION` | Fix now |
| `ROBUSTNESS` | Human judgment: fix now only when materially relevant |
| `DEFENSIVE_HARDENING` | Follow-up issue/PR |
| `STYLE_NIT` | Ignore or follow-up |
| `FALSE_POSITIVE` | Dismiss with rationale |

Post-closure findings do not reopen unlimited review. If a material fix is made, perform the narrow verification needed for that fix and the normal CI suite. Do not restart an indefinite sequence of full automated reviews.

## Merge gate

A PR is eligible for merge when:

1. required CI and deterministic validation are green on the intended head;
2. no unresolved P0/P1 finding remains that has been independently triaged as `CORRECTNESS`, material `SCIENTIFIC_CONTRACT`, or `REGRESSION`;
3. material known limitations are documented rather than hidden;
4. required human review or authority gates are satisfied;
5. deferred hardening work that is worth retaining has been captured as follow-up work;
6. the human maintainer makes the final merge decision.

A clean automated review is useful evidence, but it is **not** a requirement for an infinite fixed point where no reviewer can imagine another defensive check.

## Scope control

Do not expand a healthy PR merely to satisfy increasingly remote malformed-input, pathological-environment, style, or speculative hardening findings unless the repository explicitly supports that threat/input model.

If a finding would substantially broaden the PR, change architecture, or create a new subsystem, prefer a follow-up issue/PR unless it is required for correctness or the scientific contract of the current change.

## Explicit exception

A human maintainer may extend the two-pass budget when there is a stated reason, such as unresolved data-loss risk, release-integrity risk, security-sensitive behaviour, or a material scientific-authority defect. The extension must be deliberate; automated review does not extend itself.
