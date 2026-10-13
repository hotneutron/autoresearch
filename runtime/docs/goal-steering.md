# Goal-linked steering (runtime 0.5.0)

Goal steering is a persistent control loop **above** immutable execution campaigns. It prevents a sequence of locally valid experiments from silently replacing the user's goal with a prerequisite. It does not launch an LLM, establish scientific relevance, grant new scientific scope, or replace campaign verifiers/approvals.

## Project-neutral lifecycle

```bash
autoresearch --store /durable/project-goals goal anchor goal.json
autoresearch --store /durable/project-goals goal status
autoresearch --store /durable/project-goals goal proposal proposal.json
autoresearch --store /durable/project-goals goal assess assessment.json
autoresearch --store /durable/campaign init campaign.json
autoresearch --store /durable/campaign submit complete-unit
autoresearch --store /durable/campaign run --port 0
autoresearch --store /durable/project-goals goal checkpoint checkpoint.json
autoresearch --store /durable/project-goals goal status
autoresearch --store /durable/project-goals goal reorient reorientation.json
```

Publish the goal before the proposal; inspect the current context before the assessment. Each `goal` command accepts a version1 JSON document with an immutable `id` and exact `prompt_verbatim`. `status` needs no document. Complete fixture builders in `tests/test_goals.py` use an unrelated image-upload project.

### Goal anchor

Required fields:

- `schema_version: 1`, unique `id`, consecutive `revision`, stable `project_id`, `prompt_verbatim`.
- `goal`: the end goal; `claims`: `{id, question, success_evidence}` records.
- `non_goals`, `allowed_scopes`: explicit nonempty text lists.
- `budget: {max_seconds, imported_seconds, import_evidence}`. Import all earlier completed/failed unit charges exactly once, with selected `{path, sha256}` released evidence. Later goal revisions cannot reset imported accounting. An explicit user budget change is a new goal revision, not a new ledger.
- `drift_policy: {max_diagnostic_campaigns, max_diagnostic_seconds, max_unchanged_checkpoints}`: finite positive prospective checkpoints, not statistical early-stopping rules. Thresholds trigger reassessment, not automatic hypothesis rejection.

An anchor and source hashes preserve procedural provenance. The trusted project adapter determines the actual authorization envelope and imports; arbitrary same-user code can lie about authority. This is not an adversarial security boundary. Never create a new ledger to evade prior charges.

### Proposal

Required fields:

- `schema_version`, `id`, `prompt_verbatim`, current `goal_hash`.
- `campaign_id`, `contract_sha256`, `parent_claim`, `scope`, `kind` (`diagnostic`, `evidence` or `modeling`). Scope/claim must occur in the goal anchor.
- `decision`: the downstream choice the study can change.
- `blocker: {description, evidence}` and `endpoint_relevance` linking its estimator/effect/support to that choice, not merely a mechanism to investigate.
- `outcomes`: exactly `supported`, `unsupported`, `inconclusive`, `invalid`, each `{observation, decision, action}`. An informative negative can rule out a candidate; improvement is not required. An invalid execution cannot authorize a retry or dependent work.
- `alternatives`: `{option, reason}` records, including a sensible no-new-acquisition option supplied by the agent.
- `budget: {campaign_seconds, downstream_seconds}`: full credible campaign maximum plus complete dependent obligations needed for the stated decision. A scoped existing-evidence decision can have zero downstream cost; do not claim a full model/confirmation deliverable with zero unfunded obligations.

Compute the binding using `goals.contract_hash(contract)`, which hashes the canonical JSON contract excluding **only** `goal_gate` to avoid circular references. Do not use the byte hash of a differently formatted file. Every other command, gate, source/input closure, budget and authorization field is bound.

After a terminal checkpoint, the ledger rejects a successor proposal until the
outer loop publishes a reorientation record. If that record selects a viable
candidate, its exact proposal ID, claim, scope, kind, decision, endpoint relevance
and complete budget bind the successor proposal. This prevents a locally plausible
new study from silently bypassing the documented brainstorm/selection checkpoint.

### Assessment and controls

A fresh assessment requires:

`{schema_version, id, prompt_verbatim, proposal_id, proposal_hash, goal_hash, context_hash, action, reason, trigger_dispositions, evidence, next_checkpoint}`.

`context_hash` comes from goal `status`. `action` is `CONTINUE`, `PIVOT`, `DEFER`, `STOP` or `ASK_HUMAN`; only CONTINUE/PIVOT can permit new admission. Explain each current trigger with `{trigger, reason}`. The runtime validates completeness, bindings, scope, active-campaign exclusion and budget. The project agent supplies the scientific relevance judgment; the existence of prose is not proof that it is sound. No independent reviewer participation is implied.

Controls use `{schema_version,id,prompt_verbatim,action,reason}`:

- `REVIEW`: explicit goal intervention makes old pre-admission assessments stale.
- `STOP`: persistent explicit stop; agent assessment cannot clear it.
- `RESUME`: explicit resumed authority clears STOP but still requires a fresh assessment.

A STOP assessment holds that exact proposal; a persistent user stop must also be recorded as STOP control. UI overview comments remain advisory; the agent/host must record an authorized control separately, preserving the exact instruction. Silence, acknowledgement and a changed language are not controls.

### Enforced new-campaign gate

New campaign contracts opt into enforcement with:

```json
"goal_gate": {
  "ledger": "/durable/project-goals",
  "goal_hash": "<goal hash>",
  "proposal_id": "proposal-1",
  "proposal_hash": "<proposal hash>",
  "assessment_id": "assessment-1",
  "assessment_hash": "<assessment hash>"
}
```

The project ID, exact contract, allowance, evidence and current context must match. Missing/stale assessments, unresolved reservations, unsupported scope and inadequate aggregate **route** budget deny first launch. The controller reserves the full declared campaign maximum transactionally immediately before first launch, after independent source/scientific/review/resource checks. Multiple controllers cannot overlap reservations in one project ledger. A reservation surviving an interrupted controller requires reconciliation; there is no automatic retry or silent release.

Once admitted, the complete frozen design may finish even if the goal changes. This deliberately prevents a drift counter or new comment from retrospectively altering sampling. Existing study-specific pause/approval rules and scientific failures still apply at their declared boundaries. New campaigns remain held until complete reconciliation/checkpoint and a fresh assessment. Holds do not grant a campaign permit or bypass confirmation eligibility.

### Complete checkpoint and accounting

Submit:

`{schema_version,id,prompt_verbatim,campaign_id,outcome,decision_changed,blocker_changed,explanation,evidence}`.

The ledger independently reads the admitted campaign's runtime database, exact runtime/contract and all reconciled receipts. It refuses active, queued or unresolved units; all declared tasks must be complete unless a fixed failed unit stopped its dependent design. Failure requires outcome `invalid`. All completed/crashed/interrupted wall times, including failed units, are charged; only unused reservation is released. No re-admission of a closed campaign, replacement directory or changed contract is permitted. A checkpoint records scientific progress as the agent's evidence-backed report, not a deterministic proof of relevance.

Diagnostic count/cost and consecutive unchanged checkpoints remain cumulative and visible. After reaching a prospective limit, each fresh assessment must address the trigger; reassessment does not erase history. Every successor after a checkpoint requires a fresh exact context binding. New evidence, controls or goal revisions invalidate pre-admission assessments, not previously admitted experiments.

### Outer-loop reorientation

After every terminal campaign checkpoint, submit a version1 record before the
next proposal:

```json
{
  "schema_version": 1,
  "id": "reorient-after-study-1",
  "prompt_verbatim": "exact user or governing prompt",
  "goal_hash": "<current goal hash>",
  "context_hash": "<status context before this record>",
  "checkpoint_id": "study-1-complete",
  "checkpoint_hash": "<latest checkpoint hash>",
  "unresolved_claim": "What parent claim remains unresolved?",
  "exhausted_path": "Which experiment family is exhausted, and why?",
  "candidates": [
    {
      "id": "independent-label-source",
      "proposal_id": "independent-label-source-proposal-v1",
      "parent_claim": "quality-speed",
      "scope": "released-evidence",
      "kind": "evidence",
      "decision": "Test an independent label source.",
      "endpoint_relevance": "Direct endpoint evidence rather than another variance surrogate.",
      "novelty": "Changes the label source instead of repeating the exhausted path.",
      "status": "viable",
      "reason": "Complete bounded route fits and can change the parent decision.",
      "budget": {"campaign_seconds": 30, "downstream_seconds": 60},
      "evidence": [{"path": "/released/report.json", "sha256": "<hash>"}]
    }
  ],
  "selected_candidate": "independent-label-source",
  "no_viable_reason": null,
  "next_checkpoint": "Publish the exact selected proposal and fresh assessment."
}
```

Candidate `status` is `viable`, `rejected` or `blocked`. Supply1–10 candidates.
If any candidate is viable, select exactly one. If none is viable, set
`selected_candidate` to null and provide a nonempty `no_viable_reason`; successor
proposals then remain blocked. A viable candidate must use an allowed claim/scope
and its campaign plus downstream maximum must fit the aggregate remainder.

This is concise evidence-backed public rationale, not private chain-of-thought.
The project agent generates and scientifically judges candidates. The generic
runtime only validates identity, scope, evidence, budgets and handoff consistency.

## Review display, scope and limitations

`status` and `review status`/HTTP snapshots for goal-bound stores include the parent goal, goal state, triggers, charged/reserved/limit accounting and current reorientation inventory. States distinguish `reorientation_required`, `candidate_selected` and `no_viable_candidate`. The English/Chinese UI has a read-only goal-steering panel with escaped text and no new execution controls. Project-authored goal/candidate prose may remain English unless localized separately. Evidence/feedback bytes and permissions are unchanged.

Existing campaigns without `goal_gate` retain legacy behavior. The new feature is explicitly opt-in for **new** contracts; deleting a gate from an already initialized contract conflicts with its immutable store. Host/project policy must require a goal gate for new scientific work; generic runtime compatibility cannot discover undisclosed old stores or prevent an adversarial user from starting a separate unbound ledger. Keep prior campaigns on their pinned runtime; do not mutate an installed runtime or force migration to use the UI.

The ledger's imported accounting is a trusted adapter input, and later settlement uses durable pinned receipts. Goal controls are trusted host/user events, not authenticated human identity claims. Source hashes, same-user SQLite and path controls are procedural safety/provenance—not a sandbox. No statistical threshold or scientific policy is invented by this module.

## User Prompt, Verbatim

```text
impl the generic steering mechanism, then restart the campaign.
```

```text
when stucked like this, the outer loop should brainstorm on "fundamentally different reliable label source or measurement/model objective", right?
```

```text
update the autoresearch framework.
```

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 16:35 -0700 | Documented versioned goals, decision-linked proposals, fresh assessments/controls, transactionally enforced complete-campaign admission, failure-inclusive settlement, safe course correction, read-only bilingual display and explicit procedural/legacy limits. |
| r2 | 2026-10-13 00:00 -0700 | Added mandatory post-checkpoint outer-loop reorientation, evidence-backed candidate inventory, exact selected-proposal binding, explicit no-viable state and bilingual read-only presentation. |
