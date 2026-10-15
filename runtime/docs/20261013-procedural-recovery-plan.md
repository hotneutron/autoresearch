# Plan: Authorized Procedural Recovery Without Scientific Stopping

Created: 2026-10-13
Status: implemented and verified in runtime 0.5.3.

## User Prompt, Verbatim

```text
you do have the authorization for such procedural and budgetary stops. Stop only when it's scientific. Persist that note in the framework.
```

## Objective

Make procedural invalidity a bounded automatic-recovery condition rather than a
scientific stopping condition when the active goal explicitly records standing
authority. Preserve immutable failed campaigns and all charges.

## Contract

- Add an optional goal-level recovery policy. Legacy goals remain fail-closed.
- Permit one fresh replacement per exact invalid checkpoint when policy allows.
- Require `invalidity_kind=procedural`, unchanged scientific scope, explicit
  correction evidence, fresh campaign/proposal identities and an exact complete
  recovery budget.
- Extend the aggregate cap only by the minimum shortfall needed for that complete
  route; expose base cap and cumulative recovery extensions separately.
- Never reopen the failed campaign or use invalid evidence scientifically.
- Reject recovery of supported, unsupported or inconclusive scientific outcomes.
- Force a fresh candidate inventory after recovery and bind its selected proposal
  and complete budget to the recovery record.
- Preserve explicit user STOP and active-campaign exclusion.

## Verification

- Source tests for policy validation, minimal budget extension, fresh identity,
  scientific-outcome rejection, selected-candidate binding and old-campaign
  immutability.
- Full source and clean-wheel suites.
- English/Chinese review rendering remains compatible because recovery reuses
  existing goal states and publishes a clearer reason.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-13 | Preserved exact authority and froze generic bounded recovery semantics before implementation. |
| r2 | 2026-10-13 | Recorded completed runtime0.5.3 implementation and linked verification boundary. |
