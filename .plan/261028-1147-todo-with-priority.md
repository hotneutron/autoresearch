# Plan: Close the Partial Runtime Efforts by Priority

Created: 2026-10-28 11:47 -0700
Status: proposed; not implemented.
Scope: `~/wk/autoresearch`, primarily the optional `runtime/` package.

## User Prompt, Verbatim

```text
write a plan in ~/wk/autoresearch/.plan/{YYMMDD}-{HHMM}-topics.md to address the partial efforts, from most urgent to least.
```

## Objective

Turn the partially addressed runtime safeguards into a coherent, testable execution
boundary. The current runtime is strong at durable local bookkeeping and optional
goal-level accounting, but it still leaves a timeout-acceptance bug, weak orphan
supervision, no OS isolation, no hard cost ceiling, and no statistical promotion
protocol. Work proceeds from correctness and safety hazards to scientific
qualification, then to scale and productization.

Each item below is a separate topic so one topic can be planned, implemented, and
verified without silently expanding scope. Do not start a later topic until the
earlier topic's required tests land, except where explicitly marked parallelizable.

## Priority order

| Priority | Topic | Why now |
|---|---|---|
| P0-1 | Timeout must always invalidate scientific acceptance | Reproduced correctness bug: an interrupted unit can be recorded as scientifically valid. |
| P0-2 | Independent supervision for orphaned experimental processes | A worker/controller crash can leave a child and inherited lease running without a timeout authority. |
| P1-1 | Real execution isolation and least-privilege policy | Source hashing and git reset do not contain network, filesystem, process, or cgroup effects. |
| P1-2 | Hard campaign resource ceiling and startup/grace accounting | Admission reserves a nominal unit budget, but wall time can overshoot and there is no monetary/GPU budget. |
| P2-1 | Statistical promotion protocol | The runtime records evidence but does not distinguish signal from run-to-run noise. |
| P2-2 | Metric semantics, anti-fixation gates, and a sealed final test set | Fixed JSON checks verify declared values, not whether those values answer the goal. |
| P3-1 | Make safe defaults explicit and document deployment modes | Most strong controls are opt-in; new users can easily run without confirmation or goal gates. |
| P3-2 | Qualified distributed/remote execution adapter | Remote execution is intentionally rejected; future scale needs a cancel/query/lease contract rather than generic shell launch. |
| P4 | Repository and release hygiene | Lower-risk cleanup that should not interrupt correctness work. |

---

## P0-1 — Timeout must always invalidate scientific acceptance

### Problem

`worker.execute` sets `execution_status = "interrupted"` on timeout, but later computes
acceptance from `rc == 0 and verifier["passed"]` without requiring completed
execution. A cooperative child can handle SIGTERM, exit zero, and write a passing
verifier during the shutdown window. The observed receipt is:

```json
{"execution_status": "interrupted", "returncode": 0,
 "scientific_pass": true, "evidence_status": "valid"}
```

That contradicts the intended invariant stated in the timeout reason and in
`test_A12_timeout_invalidates_whole_unit` for the existing non-cooperative path.

### Contract

- `scientific_pass` must be true only when execution completed normally **and** all
  fixed verifier checks pass.
- `evidence_status` must be `invalid` for any non-completed terminal state,
  including interrupted, crashed, blocked, and reconciliation-failed units.
- Keep the raw return code and verifier object in the receipt for diagnosis, but do
  not let either promote an interrupted unit.
- Preserve the existing behavior where failed/interrupted openings remain consumed.
- Update `test_A12_timeout_invalidates_whole_unit` or add a neighboring regression
  that installs a cooperative SIGTERM handler which writes a passing result and
  exits zero.
- Assert all four fields for the cooperative fixture:
  `execution_status=interrupted`, `returncode=0`, `scientific_pass=false`,
  `evidence_status=invalid`.

### Verification

- New focused unit test plus the existing runtime suite.
- Full installed-suite run in a clean virtual environment.
- Manual CPU fixture check; no GPU or model execution required.

### Exit criteria

- No receipt can combine `execution_status != "completed"` with
  `scientific_pass=true` in a source test.
- Existing successful completion and ordinary timeout tests still pass.

---

## P0-2 — Independent supervision for orphaned experimental processes

### Problem

The experimental child is started in a new session and inherits lease descriptors.
Timeout enforcement lives in the worker. If the worker dies, controller
reconciliation can observe that the child is still alive and marks the unit
`reconciliation_required`, but no component is responsible for killing the child at
the deadline or releasing non-flock resources. The existing
`test_A13_child_retains_lease_if_worker_is_killed` intentionally proves the lease is
retained; it does not provide a bounded reaper.

### Contract

- Introduce a supervisor identity and deadline record that survive the worker.
- On controller restart/reconciliation, distinguish:
  1. live child inside its deadline;
  2. live child past its deadline;
  3. exited child awaiting receipt reconciliation;
  4. unknown launch with no trustworthy identity.
- For case 2, terminate the process group with SIGTERM then SIGKILL and write an
  interrupted receipt through the controller-owned recovery path.
- Never blindly rerun a unit solely because its worker disappeared.
- Keep flock participation conservative: only participating runtimes must be
  blocked by a recovered lease; unrelated jobs remain outside that protocol.
- Do not release a lease while an identified child remains alive; release it after
  confirmed process-group termination or explicit human adjudication.

### Verification

- Unit test killing the worker while a short-lived child holds a lease, then
  reconciling with an expired deadline.
- Test that a live, in-deadline child is not killed and is not auto-retried.
- Test that SIGKILL escalation terminates the full process group.
- Test that unknown launches stay `reconciliation_required`.

### Exit criteria

- Every launched process group has either a live supervisor or a deterministic
  controller recovery path bounded by the recorded deadline.
- No test leaves a child process or lock descriptor open after teardown.

---

## P1-1 — Real execution isolation and least-privilege policy

### Problem

The runtime uses ordinary subprocesses, `start_new_session=True`, source hashes,
and local flock leases. These are provenance and coordination controls, not a
security boundary. The README already states that source hashing is not an OS
sandbox. Network access, arbitrary filesystem writes, and process side effects are
not contained, and git reset cannot undo them.

### Contract

- Add an executor backend interface with at least two modes:
  - `local-direct`: current behavior, explicitly labeled unsuitable for
    untrusted/same-user adversarial code;
  - `local-container`: default target for production-like use, with no network,
    read-only source mounts, writable trial/output/tmp mounts only, dropped
    capabilities, non-root user, cgroup memory/CPU limits, and no inherited extra
    file descriptors beyond declared leases.
- Bind the executor identity and isolation profile in the campaign contract.
- Refuse to launch untrusted confirmation work in `local-direct` unless the
  contract explicitly accepts procedural-only separation.
- Keep the adapter's declared argv/cwd/env immutable; isolation must not be
  bypassable by task fields.
- Record the isolation profile and image/backend digest in the receipt.

### Verification

- Contract validation tests for missing/unsupported isolation profiles.
- A container-backed CPU test that verifies network denial, read-only source
  enforcement, writable output directory, and memory-limit behavior. If no
  container runtime exists in CI, mark the integration test as skipped with the
  exact missing backend while retaining pure contract tests.
- Negative test proving lease fds and unrelated host descriptors are not leaked
  beyond the declared set.

### Exit criteria

- The documented default for autonomous execution is either isolated or explicitly
  labeled procedural-only.
- Every receipt states how the process was isolated.

---

## P1-2 — Hard campaign resource ceiling and startup/grace accounting

### Problem

The controller checks `spent + task.timeout_seconds <= max_seconds` before dispatch.
That is a reservation against nominal unit time, not a hard wall-clock ceiling.
Interpreter startup, compilation, confirmation proxy execution, and the two-second
SIGTERM grace period are not fully bounded by the admitted reservation. There is
also no GPU-hour or monetary accounting and no runtime-level stall detector.

### Contract

- Define campaign limits in separate dimensions:
  - nominal training/unit seconds;
  - total wall-clock ceiling including startup and shutdown grace;
  - optional GPU-seconds and currency cap with explicit rate/card metadata.
- Maintain a hard deadline from launch intent to confirmed process-group teardown.
- Include SIGTERM grace and confirmation proxy time in reservation accounting.
- Charge crashed and interrupted units for actual elapsed wall time; reserve unused
  capacity only after reconciliation.
- Add optional stall policy: minimum number of windows, epsilon threshold, and
  required action (pause for review, pivot, or stop). Keep it distinct from
  statistical significance.
- Surface projected and actual spend in status and the review inbox.

### Verification

- Tests for budget denial when startup/grace could exceed the remaining ceiling.
- Test that a unit exceeding nominal time but terminating inside hard grace is
  recorded interrupted and charged for full elapsed time.
- Tests for currency/GPU cap denial and accurate status aggregation.
- Goal-ledger tests ensuring campaign reservations plus downstream obligations
  cannot exceed the aggregate goal cap.

### Exit criteria

- A campaign cannot silently run beyond its declared wall-clock ceiling.
- Every admitted cost dimension is represented in status and checkpoint receipts.

---

## P2-1 — Statistical promotion protocol

### Problem

The runtime freezes contracts and preserves traces, but one logical unit maps to
one execution. It has no built-in multiple-seed protocol, paired tests, confidence
intervals, multiple-comparison correction, matched classical baseline, or ablation
requirement. Adaptive keep/revert decisions can therefore retain run-to-run noise.

### Contract

- Add a project-defined promotion policy, separate from the scientific verifier:
  - baseline and candidate seed set;
  - minimum detectable effect;
  - paired statistical test or bootstrap confidence interval;
  - adaptive-selection correction policy;
  - required matched baselines (random search and at least one classical optimizer
    where the search space is structured);
  - ablation requirements for bundled changes.
- The runtime should enforce presence, identity, and completeness of declared
  replicates; the adapter remains responsible for statistical interpretation.
- A candidate cannot promote from iterative validation alone; final promotion
  requires a frozen candidate evaluated on a sealed final test set.
- Record every comparison, including failed candidates and corrected intervals, in
  durable evidence.

### Verification

- Tests reject promotion with missing seeds, mismatched candidate identity, or
  incomplete replicate sets.
- Tests distinguish validation iteration from one-time sealed final evaluation.
- Fixtures cover a declared matched baseline and ablation manifest.
- Keep runtime core dependency-free; statistics can live in an adapter or optional
  extra rather than being imported by the worker.

### Exit criteria

- The runtime can mechanically prevent under-replicated or uncorrected promotion.
- Scientific rationale remains supplied by a trusted adapter and is not invented by
  the framework.

---

## P2-2 — Metric semantics, anti-fixation gates, and a sealed final test set

### Problem

`verdict()` performs exact type/value JSON-pointer checks and requires every check
to pass. That prevents malformed or missing evidence but does not understand metric
semantics, inequality thresholds, proxy-metric gaming, or validation-set
overfitting. The optional confirmation proxy protects aggregate release and
exposure bookkeeping procedurally, but same-account filesystem access is still
trusted.

### Contract

- Support a typed metric schema with units, direction, thresholds, comparisons, and
  declared business/scientific meaning while retaining exact-value checks as the
  safe default.
- Permit multi-objective acceptance with explicit conjunctive gates rather than a
  single optimizable proxy.
- Require adapter-declared validation and final partitions. The final partition is
  never present in iterative campaign contracts.
- Add optional rotating validation shards where scientifically appropriate, while
  documenting that rotation alone does not remove adaptive-selection bias.
- Extend procedural confirmation guidance to minimize label exposure and require a
  clean dedicated checkout for sensitive data.
- Keep raw/private verifier logs out of review packets.

### Verification

- Schema tests for metric direction, units, thresholds, and missing semantics.
- Negative tests where one proxy metric improves but a required usability/downstream
  metric fails.
- Test that final-test data cannot be referenced by ordinary iterative contracts.
- Confirmation tests for aggregate-only release and private-log retention.

### Exit criteria

- A passing verifier means the declared evidence matches a meaningful acceptance
  contract, not merely that JSON values exist.
- Final-test access requires a distinct confirmation boundary.

---

## P3-1 — Safe defaults and deployment-mode documentation

### Problem

Durable receipts are core behavior, but confirmation, goal gates, isolation,
statistical policy, and stall controls are optional or adapter-supplied. A new user
can run the generic runtime without adopting the strongest controls.

### Contract

- Define named deployment profiles:
  - `local-mechanical`: durable queue/receipts only;
  - `procedural-research`: frozen contracts plus confirmation and goal gate;
  - `isolated-research`: container isolation plus hard resource ceilings;
  - `qualified-scientific`: replicates, promotion policy, and sealed final test.
- Initializing a campaign without recommended controls must print/store an explicit
  accepted-risk record.
- Provide one complete example for each realistic profile.
- Document the exact boundary between mechanical guarantees and scientific or
  security guarantees in the README and generated review status.

### Verification

- CLI tests for profile validation and explicit risk acceptance.
- Documentation check that examples do not imply isolated or scientific guarantees
  in local-mechanical mode.
- Review inbox renders the active profile and missing controls.

### Exit criteria

- Users can tell from status and receipts which controls are active and which were
  deliberately waived.

---

## P3-2 — Qualified distributed/remote execution adapter

### Problem

The current controller is local and serial, and non-local backends fail closed with
`Remote execution requires a registered, qualified job adapter`. This is safe but
limits long-running or multi-server research. A remote adapter must not become a
generic shell escape.

### Contract

- Define a registered adapter interface with query, launch, heartbeat, cancel,
  output fetch, identity attestation, and lease semantics.
- Require immutable remote command/image specs, declared resources, and a hard
  cancel path independent of the local worker.
- Preserve exactly-once logical unit identity and no-blind-retry semantics.
- Support asynchronous worker pools only after the orphan supervisor and hard
  resource ceiling topics are complete.
- Keep online A/B and production deployment outside this runtime; consume their
  results as external evidence only.

### Verification

- Adapter conformance tests using a fake qualified backend.
- Cancellation and network-partition tests.
- Tests proving an unregistered backend cannot launch work.
- Lease/reconciliation tests across simulated controller restarts.

### Exit criteria

- Remote work has the same identity, budget, cancellation, and evidence guarantees
  as local work, or it is refused.

---

## P4 — Repository and release hygiene

### Problem

The source is well-structured, but generated `runtime/build/` artifacts exist in the
working tree and the runtime/README release requirement asks for a clean-wheel
test. Keeping hygiene last prevents churn from conflicting with correctness fixes.

### Contract

- Confirm generated artifacts remain ignored and are never committed.
- Add a documented release verification command for:
  - clean virtual environment;
  - wheel build/install without source checkout on `PYTHONPATH`;
  - full test suite from the installed wheel;
  - editable-install test during development.
- Pin/record the Python version used for release verification.
- Keep PROVENANCE user prompts and revision history current for any generic feature.

### Verification

- Clean-wheel installation and test run.
- `git status --short` clean after building.
- Release note includes test environment, runtime version, and limitations.

### Exit criteria

- A fresh environment can install and qualify the package using documented commands.

---

## Sequencing and dependencies

1. Land P0-1 first; it is small, fully local, and fixes a known acceptance
   invariant.
2. Land P0-2 before any isolation or distributed work because those topics rely on
   a trustworthy local supervisor.
3. P1-1 and P1-2 can be planned in parallel, but both should precede autonomous
   overnight production use.
4. P2-1 depends on hard accounting and reliable execution status; P2-2 can proceed
   in parallel with P2-1 after the metric schema is agreed.
5. P3-1 should follow P1/P2 so the named profiles reflect real controls.
6. P3-2 follows P0-2, P1-1, and P1-2.
7. P4 runs after code topics or immediately before a release.

## Non-goals

- Do not claim that deterministic hashing guarantees bitwise reproducible training.
- Do not treat the runtime as a replacement for project-specific scientific
  judgment.
- Do not add an LLM controller, arbitrary package installation, or auto-approval.
- Do not implement online production deployment from this runtime.
- Do not broaden the hotneutron runtime into a distributed scheduler before local
  safety invariants are closed.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-28 11:47 -0700 | Initial prioritized plan covering timeout acceptance, orphan supervision, isolation, hard resource ceilings, statistical promotion, metric semantics, safe profiles, remote execution, and release hygiene. |
