# Goal Revision After Recovery: Accounting Plan

Date: 2026-10-13
Status: implemented

## Trigger

An Accorde goal revision attempted to combine operation and shape after prior
procedural recoveries had already extended the effective aggregate budget. The
ledger rejected the revision because `anchor()` compared the new base cap alone
against cumulative spend, while `context()` correctly retained the recovery
extensions in the effective cap.

## Invariant

A goal revision must neither erase nor duplicate prior recovery extensions:

```text
effective_new_max = new_goal_base_max + historical_recovery_extensions
```

The revision is legal exactly when that effective cap covers committed spend and
active reservations. Recovery records remain immutable and continue to be summed
once by the ledger context.

## Change

- Validate goal revisions against the effective new cap.
- Preserve the goal's base cap unchanged when the user changes scientific scope.
- Add a regression with cumulative spend above the base cap but exactly covered
  by one historical recovery extension.
- Retain rejection when even the effective revised cap is too small.

## User Prompt, Verbatim

```text
can you combine the operation and shape together?
```

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-13 22:30 -0700 | Documented effective-cap accounting for goal revisions after procedural recovery. |
