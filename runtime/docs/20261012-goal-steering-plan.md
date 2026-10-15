# Generic goal-linked steering and campaign admission

Created: 2026-10-12 16:18 -0700
Status: implementation and source/clean-wheel verification complete;69 tests plus both-locale renderer checks pass. Local commit and H3 adoption are separate follow-up steps. See20261012-goal-steering-verification.md.

## User Prompt, Verbatim

```text
impl the generic steering mechanism, then restart the campaign.
```

## Design

Add a separate durable project goal ledger. Immutable versioned goal anchors retain the parent claims, allowed scope, non-goals, original instruction and cumulative budget including imported historical charges. New proposals bind the current goal, exact campaign contract (excluding only the goal-gate references), released evidence, endpoint relevance, outcome-to-decision maps, alternatives and complete downstream allowances. Every campaign needs a fresh assessment bound to the ledger's exact context; explicit review/intervention and prospective diagnostic thresholds require reasoned dispositions. Human stops persist until an explicit resume control, independently of advisory feedback.

Admission is enforced for goal-bound new campaign controllers immediately before first launch. One transactional full-campaign reservation prevents overlaps and over-budget paths. Once started, goal changes hold new campaigns, not the admitted complete design; scientific/source/approval/resource gates still apply. A complete verified checkpoint records all attempted failures and actual charged time, releases only the unused reservation, updates goal-progress evidence and requires reassessment before any successor. Goal assessments are project-agent scientific judgments, not numerical expected-value models or independently verified relevance.

The CLI and review snapshots expose the goal, current hold/trajectory, admission and cumulative accounting. The generic ledger does not select an LLM, generate experiments, infer private reasoning or grant authorization outside the frozen scope. Same-account source hashing is procedural integrity, not an adversarial security boundary. Historical campaigns remain on their pinned runtime; optional adoption only for new contracts. No old runtime/config/store is migrated in place.

## Acceptance

Test strict schemas, complete outcome coverage, immutable/stale hashes, evidence drift, scope/cost rejection, old-charge preservation, concurrent reservations, explicit hold/stop/resume, prospective detour triggers, complete checkpoints and restart idempotency. Test actual Controller dispatch denial and admitted-design completion after goal intervention, plus non-bypass of scientific failures and approvals. Run source and clean-wheel Python suites and existing bilingual UI renderer tests. Document adoption and exact limits; local commit only, no push or co-author trailer.

H3 restart is a project-specific follow-up: choose the modeling claim before freezing any new unit; preserve the 28800-second cap and all 27847.335206361488 prior charges. Do not automatically select a 4020-second proposal within 952.6647936385125 seconds remaining. Do not retry failed/completed experiments or weaken old labels/gates.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 16:18 -0700 | Preserved request and specified generic durable goal/proposal/assessment/admission/checkpoint mechanism, complete-campaign safety and unchanged historical-runtime/H3 budget boundaries. |
| r2 | 2026-10-12 16:40 -0700 | Completed generic ledger/CLI/Controller enforcement and read-only bilingual panel; recorded69 source/wheel tests and actual renderer checks. No H3 experiment or old runtime migration claimed. |
