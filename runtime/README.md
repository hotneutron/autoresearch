# Autoresearch runtime and review inbox

This optional subproject adds a durable local research queue and asynchronous
review inbox to autoresearch. It installs independently of the upstream training
example and has no Torch, CUDA, or project-specific dependencies.

```bash
python3.11 -m pip install ./runtime
autoresearch --store /durable/campaign init campaign.json
autoresearch --store /durable/campaign submit baseline
autoresearch --store /durable/campaign run --port 8765 --idle-timeout 3600
autoresearch --store /durable/campaign status
autoresearch --store /durable/campaign review export --output report.html
```

`run` starts the built-in loopback inbox and services the queue. Its lifetime ends
when all submitted work is settled, the idle timeout expires, or reconciliation
is necessary. `review serve` keeps the inbox available separately. `resume`
reconciles durable state and services pending feedback; it does not override a
human branch pause. Stop the controller with Ctrl-C; detached experimental units
keep running to their bounded timeout and retain resource leases. Reopen with the
same installed runtime and store to reconcile their receipts.

## Goal-linked steering · 0.4.0

Optional persistent goal steering binds new campaigns to the original goal,
parent modeling decision, outcome-to-action map and full downstream cost. It
requires a fresh assessment at every campaign boundary and after goal feedback;
prospective diagnostic limits trigger reassessment, not automatic rejection.
First launch transactionally reserves a complete campaign in the project ledger;
settlement charges all completed/failed units and never resets historical imports.
A goal hold affects new campaigns, not retrospective sampling in an admitted design.
Scientific/source/approval/resource gates remain independent.

```bash
autoresearch --store /durable/project-goals goal anchor goal.json
autoresearch --store /durable/project-goals goal proposal proposal.json
autoresearch --store /durable/project-goals goal assess assessment.json
autoresearch --store /durable/project-goals goal status
```

See [goal steering and admission](docs/goal-steering.md) for schemas, exact
`goal_gate` binding, controls/checkpoints and safety limits. The runtime enforces
records and context, not the scientific soundness of an author's relevance claim.
Existing campaigns remain pinned; opt in only with new contracts/environments.

## Contract and agent interface

A trusted project adapter creates `campaign.json`, with schema version 1, an ID,
project root, verbatim user instruction, finite `max_units`/`max_seconds` budget,
and a map of tasks. Each task declares branch, authorization, exact argv/cwd/env,
timeout, SHA-256 source/input/interpreter closure, prerequisites and fixed JSON
verifier checks. `{output}` expands to the unit's durable directory. The test
fixture in `tests/test_runtime.py` is a complete executable contract example.

The coding agent reads project policy, inspects results and submits a declared
task ID. It cannot submit an eligibility flag, substitute argv, or alter a verifier.
Each task has one logical unit identity; a new checkpoint cannot run it twice.
Additional candidates or protocol changes require a new frozen campaign contract.
This release executes declared candidate slates; it does not launch an LLM or
silently grant arbitrary source mutation. Host integrations can use the JSON CLI
for proposal/context exchange and `steer` for evidence-backed decisions.

Process completion, evidence validity and scientific promotion are separate.
Verifier checks compare exact JSON types and values. Missing/malformed outputs or
failed prerequisites block dependent work even if a process returned zero.
Only the trusted adapter establishes scientific meaning; the runtime enforces its
fixed contract. Include imported code and environment dependencies in the closure.
The worker verifies declared files before and after execution. Source hashing is
not an operating-system sandbox against an adversarial same-user process.

## Review behavior

Packets publish automatically when units are prepared/completed. FYI and advice
do not require acknowledgement. Explicit decisions cover only the named revision
and action. Applied pauses persist across revisions; resume still checks all gates.
Feedback queues during a unit and is consumed at completion or an idle boundary.
Comments are delivered in checkpoint receipts; the agent records adoption or
deferral in its steering record and subsequent report.

The UI provides brief, metric and evidence layers; typed metric selectors validate
reported values against released JSON snapshots. Units/support/baselines and
comparison keys are explicit. Offline HTML embeds evidence and is read-only.
The inbox is a local pull interface, not an email/Slack notification service.

## Project workflow overview · Start here

Runtime 0.3 adds a reusable, newcomer-friendly workflow overview alongside study
outcomes. It explains the project goal/background, success criteria and glossary,
then each effort's question, why it was tried, alternatives, result, decision
rationale, uncertainty and next step. Released evidence stays one click away.
This is a public decision record, not private internal reasoning.

```bash
autoresearch --store /durable/project-review review overview overview.json --repo /project
autoresearch --store /durable/project-review review serve --port 8765
```

See [the document/steering guide](docs/workflow-overview.md) and
[non-H3 illustrative example](examples/workflow-overview/overview.json).
The project agent/adapter publishes consecutive overview revisions at safe
checkpoints; it supplies the accurate rationale instead of the runtime inventing
one. Use one stable project review store to retain history across campaigns.
Overview feedback is advisory; approve/pause/resume through the linked current
study's exact actions. No overview publication creates jobs or expands scope.
Existing pinned campaigns keep their old installed runtime; use a separate
review-only installation or adopt the new release for a fresh campaign.

Runtime 0.3.1 adds English / Simplified Chinese presentation. Choose **简体中文**
or open `http://127.0.0.1:8765/?lang=zh-CN`. Project content can provide validated
`translations` narrative fields; IDs, source bytes, numeric results, permissions
and feedback kinds stay canonical. Missing content translations fall back to
English. See the [localization schema](docs/workflow-overview.md#english--simplified-chinese-presentation-031).

## Durability and recovery

`inbox.sqlite3` stores both the review data and runtime ledger. Results enter a
durable outbox before publication. Retrying publication preserves packet identity.
The supervisor records launch intent, Linux process start identity and worker
receipts; controller restarts never blindly rerun unknown jobs. A
`reconciliation_required` unit needs process/evidence investigation before a new
campaign can replace it. The interface deliberately does not offer a force-success
or blind retry command.

Local resource leases use `flock` under
`~/.local/state/autoresearch/leases`, keyed by resource ID such as `gpu:<UUID>`.
They are inherited by both worker and experimental child, so controller or worker
loss cannot release a lease while the child still holds it. These leases coordinate
participating runtimes; unrelated jobs must be checked by the project's measurement
protocol. Timeout terminates the entire child process group and invalidates the unit.

Back up an idle, reconciled store with `autoresearch_runtime.store.backup`, which
uses SQLite's online backup API rather than copying a live database file without
its WAL. `migrate` imports a prototype inbox into a new directory and preserves
packet bytes, feedback, receipts and hashes. The `review` command also works directly
on migrated inboxes that have no campaign contract. Existing runtime campaigns retain
their exact source identity; do not upgrade code beneath an active campaign. To
rollback, use the old runtime and its pre-upgrade backup at the original paths.

Remote job execution remains disabled pending a qualified query/cancel adapter.
Generic queue tests are not hardware or statistical qualification of a project's experiment.

## Procedural confirmation

Runtime 0.2 supports an explicitly declared `procedural` confirmation contract.
The project supplies a clean dedicated Git checkout, frozen commit, candidate and
verifier hashes, dataset hash and stable subject identities, a project-wide
exposure ledger, and an exact numeric/boolean aggregate output schema. The runtime
dispatches its fixed confirmation proxy, which invokes the frozen verifier and
releases only the validated aggregate result.

Opening is recorded before evaluator launch. Dataset hashes, cohort IDs and
overlapping subjects cannot be reopened by changing campaign names. Failed,
interrupted or uncertain openings remain consumed. A fresh-confirmation contract
rejects data declared previously exposed. Private verifier logs stay outside the
review packet. Project policy must keep cohort namespaces and the ledger stable
across branches and future tuning; the runtime cannot infer scientific group identity.

This is procedural separation under a trusted account. It does not stop an agent
with filesystem access from deliberately reading the label files. The project
must state this limitation and avoid reading private labels/logs in development.
Protocol fixtures and historical replays are labeled separately from actual fresh
scientific confirmation. See `tests/test_confirmation.py` for the complete contract.

## Verification

```bash
python3.11 -m unittest discover -s runtime/tests -v
```

Tests exercise the inherited inbox behavior plus durable queue/restart/outbox,
source and environment drift, exact unit identity, budget/resource exclusion,
timeout invalidation, typed metrics, migration and idle feedback. The package
must also be installed as a wheel into an empty environment and run without the
source checkout on `PYTHONPATH` before a release is pinned.

## User Prompt, Verbatim

```text
sibling repo it is then. execute the plan with a tracker by creating our own fork of autoresearch first.
```

```text
procedural separation is enough for now.
```

```text
create a chinese version of the review inbox
```

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-09 14:29 -0700 | Documented installed runtime, inbox, contract/agent interface, recovery and explicit unsupported execution boundaries. |
| r2 | 2026-10-09 14:41 -0700 | Documented review access to migrated inboxes without a campaign contract; patch release 0.1.1 retains the frozen-execution identity requirement. |
| r3 | 2026-10-09 14:50 -0700 | Added the explicitly accepted procedural confirmation contract, frozen checkout/verifier proxy, durable exposure ledger and aggregate-only release boundary. |
| r4 | 2026-10-12 12:08 -0700 | Documented 0.3 newcomer-friendly workflow overview, project-neutral publication and safe evidence/feedback boundary without changing old campaign pins. |
| r5 | 2026-10-12 12:56 -0700 | Added 0.3.1 Chinese presentation and display-only localization while preserving canonical numeric evidence and authority; preserved exact request. |
| r6 | 2026-10-12 16:35 -0700 | Documented 0.4.0 goal-linked proposal/assessment, enforced complete-campaign admission and failure-inclusive aggregate settlement; latest exact implementation request is preserved in docs/goal-steering.md and its plan. Old pins and scientific gates unchanged. |
