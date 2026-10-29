# M2 execution tracker

Created: 2026-10-28T20:04:36-07:00
Status: Local coordinator/scientific contract implementation verified; real subject qualification deferred.
Source plan: [P0–P2 implementation](../261028-1937-p0-p2-implementation-plan.md), SHA-256 `80446b0a87e677472d0e67458fa81b6bf7e29d16d4f61d16f2ae3ed01fb2453e`.

## User Prompt, Verbatim

```text
execute the plan with trackers in .plan/trackers/ for each milestone.
```

## Packages

| Package | Implementation | Verification | Required evidence |
|---|---|---|---|
| W05 | implemented | portable spec/metric/guard tests pass | Dual Git refs, exact argv/files, finite conjunctive metrics, final partition exclusion and frozen qualification policy. |
| W06 | implemented | SQLite race/BUSY/disk-limit/rollback/import tests pass | WAL/FULL local authority, bounded transactions, immutable attempts, budgets, leadership epoch and receipt/event deduplication. |
| W08 | implemented | archive/audit/restore tests pass | Immutable blob/manifest IDs, causal replies, sealed events, result publication and share bundles; remote archive conformance deferred. |
| W09 | implemented | paired/seed/control/ablation contract tests pass | Deterministic and Bonferroni paired bootstrap helpers, policy/evaluator/environment binding and recomputed qualification; actual scientific adequacy belongs to subject. |
| W10 | implemented ledger/helper | global exposure and final binding tests pass | One-time global cohort/subject reservation and accepted aggregate final-promotion gate; real sealed batch executor qualification deferred. |
| W11 | implemented | exact review/successor tests pass | Anonymous POC assurance is unverified; current selection and exact successor hash must be applied globally. |
| W12 | implemented | Git bundle/pool/promotion tests pass | Detached recoverable subject objects, lease-bound slots and expected-ref one-writer promotion; no public branch per candidate. |

## Environment and outstanding inputs

The active checkout is macOS, Python 3.12 is available, and local Docker/systemd
are unavailable. Linux SSH targets, qualified executor access, HTTPS hostname and
remote artifact archive are explicitly deferred by the user. Portable implementation and CPU
fixture work continue. Simulation is recorded separately from real qualification.

```text
defer that for now.
```

## Evidence and changes

- Implementation and verification snapshot: 2026-10-28T20:40:08-07:00.
- Files/evidence: global_store.py, artifacts.py, audit.py, qualification.py, review_policy.py, snapshots.py, workspace_pool.py and promotion.py; immutable object and domain invariants are exercised locally.
- Portable installed-wheel results: [verification](portable-verification.json); real infrastructure explicitly deferred.

- Tracker initialized before code changes. Existing plan edits are retained.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-28T20:04:36-07:00 | Created milestone tracker with exact execution request and package gates. |
| r2 | 2026-10-28T20:11:40-07:00 | Recorded explicit deferral of real-host/deployment qualification; continue local implementation and conformance. |
| r3 | 2026-10-28T20:40:08-07:00 | Recorded local implementation, passing contract/fixture evidence and explicit deferred qualification; retained the original requests and package boundaries. |
