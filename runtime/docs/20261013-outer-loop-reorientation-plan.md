# Outer-loop reorientation after an exhausted research path

Status: implemented for runtime0.5.0.

## User Prompts, Verbatim

```text
when stucked like this, the outer loop should brainstorm on "fundamentally different reliable label source or measurement/model objective", right?
```

```text
update the autoresearch framework.
```

## Problem

A complete campaign checkpoint currently invalidates stale assessments but leaves
the generic state as `goal_review_required`. A project agent can incorrectly treat
that as the end of the outer loop, even when only one experiment family is
exhausted. The runtime does not require an explicit inventory of orthogonal paths
or bind the next proposal to a chosen path.

## Design

Add an immutable `reorientation` record after a terminal campaign checkpoint and
before any successor proposal. The project agent supplies concise public decision
records—not private chain-of-thought—including:

- the unresolved parent claim and exhausted path;
-1–10 candidate paths with exact proposed proposal ID, goal claim/scope/kind,
  endpoint relevance, novelty versus the exhausted path, disposition, selected
  evidence and complete campaign+downstream budget;
- exactly one selected viable candidate, or an explicit evidence-backed reason
  that no candidate is viable;
- the next safe checkpoint.

The ledger validates checkpoint/context identity, released evidence, goal scope,
aggregate budget and candidate selection. A selected candidate's ID, claim, scope,
kind, decision, endpoint relevance and complete budget bind the next proposal. A
rejected/blocked-only inventory prevents successor proposals. A later goal revision
is itself a material reorientation and supersedes an older inventory.

## Runtime and review behavior

- After an unreoriented checkpoint: `reorientation_required`.
- After selecting a viable path: `candidate_selected` until its proposal and fresh
  assessment are published.
- After finding no viable path: `no_viable_candidate` with the authored reason.
- After a fresh bound assessment: `ready_for_admission` under all existing gates.

The review inbox displays the unresolved claim, exhausted path, candidates,
dispositions, selected path, complete route budget and next checkpoint. It clearly
labels these as public decision summaries rather than private reasoning. The
runtime still does not generate ideas, run an LLM, establish scientific truth or
override approvals, scientific prerequisites, resources or aggregate budgets.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-13 00:00 -0700 | Preserved the exact user requests and specified the thin durable reorientation record, selected-candidate proposal binding, explicit no-viable state and review presentation. |
