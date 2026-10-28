# Fork Feature Adoption Priorities for the Peer-Checkout Runtime

Created: 2026-10-28T15:03:56-07:00
Status: source inspection and recommendations; no feature implementation or deployment performed.
Local baseline: `hotneutron/autoresearch` at `33ef750face59b42f9663c8e355a77600d1765e7`, optional runtime `0.5.8`.
Source document: [Lark review](https://bytedance.us.larkoffice.com/docx/Y6C8dMW0do0YMLxKm8duFJRqsId), revision `33` as read in this task.

## User Prompt, Verbatim

```text
read the forks mentioned https://bytedance.us.larkoffice.com/docx/Y6C8dMW0do0YMLxKm8duFJRqsId , identify the worthy features to be absorbed into this repo with priorities
```

## Recommendation

Absorb selected mechanisms into the existing runtime. The highest-value combination
is a frozen subject-project experiment specification, evidence-bound independent
review, explicit qualification of positive results, and resource-aware parallel
frontier search with reusable workspaces. Persist failure/context records and
compile accepted feedback into reviewed plan changes after those foundations.

The three true GitHub forks are primarily training-platform ports. They are useful
portability references, but the largest increments for this repo's peer-project,
auditable top-k search come from the acknowledged reimplementations and the
independent evo, FAROS, and EvoMap projects.

Preserve the [peer-checkout/search/HTTPS plan](261028-1205-host-review-dashboard-over-https.md)
and [runtime correctness priorities](261028-1147-todo-with-priority.md). This assessment
provides implementation references and adoption order for those plans; it does not
replace their authorization, scientific gates, or frozen campaign contracts.

## Scope and Evidence Quality

Read the Lark ecosystem section, references, methodological recommendations, and
its audit of this exact local baseline. Verified GitHub metadata, pinned each of
11 public repositories, and inspected README plus selected implementation/protocol
files and relevant tests. Repository code and tests were read, not executed; no
third-party training, LLM calls, benchmark gains, or containment guarantees were
independently reproduced.

The document carefully distinguishes forks, reimplementations, academic migrations,
and products. Keep that distinction. Its lower-evidence classification is now
incomplete for adoption analysis: current FAROS, EvoMap, and AutoKernel commits
contain concrete code worth inspecting. This is a new code-level assessment, not a
claim that their reported scientific results are verified.

Commercial [Frozo](https://research.frozo.ai/) and the YC listing now found at
[Autoresearch, Inc.](https://ycombinator.com/companies/autoresearch-inc) provide product
ideas—hosted campaigns, lineage, and observability—but no implementation was verified
for this assessment. Academic items in the document are methodological references,
not repository donors or evidence of this runtime's effectiveness.

## Repository Coverage

| Repository | Verified relationship | Inspected commit | Useful surface | Adoption conclusion |
|---|---|---|---|---|
| `miolini/autoresearch-macos` | True fork; parent `karpathy/autoresearch` | [537c6e6d](https://github.com/miolini/autoresearch-macos/tree/537c6e6d0ecf7d28f9d70ce20bb05d8c7ed9cfce) | MPS/CPU fallback, SDPA, compile/backend adaptation. | P3; portability recipe. |
| `jsegov/autoresearch-win-rtx` | True fork; parent `karpathy/autoresearch` | [a4123c6e](https://github.com/jsegov/autoresearch-win-rtx/tree/a4123c6e5c6287f90be04026642ba20b94e424df) | Capability/VRAM profiles, BF16/TF32, activation checkpointing. | P2 for capability profiles; P3 for Windows training. |
| `andyluo7/autoresearch` | True fork; parent `karpathy/autoresearch` | [c2c12b28](https://github.com/andyluo7/autoresearch/tree/c2c12b281c275850705031837e0f5712488a3982) | ROCm detection, SDPA fallback, compile adaptation. | P3; semantics must be requalified. |
| `trevin-creator/autoresearch-mlx` | Acknowledged reimplementation; `fork=false` | [766a25ff](https://github.com/trevin-creator/autoresearch-mlx/tree/766a25ff22afa799efd8d0aa450a4348e4749df2) | Repeated-run qualification, sample ledger, bootstrap comparison. | P1 concept; repair seed/identity/selection assumptions. |
| `davebcn87/pi-autoresearch` | Acknowledged reimplementation; `fork=false` | [04b8a50d](https://github.com/davebcn87/pi-autoresearch/tree/04b8a50dac7efe80ffc91648bd00ed9b022e24c2) | Generic metric tools, secondary checks, compaction from persisted state, failure/revisit hints, finalize workflow. | P1/P2; retain this repo's durability and authority. |
| `leo-lilinxiao/codex-autoresearch` | Acknowledged reimplementation; `fork=false` | [0f54c571](https://github.com/leo-lilinxiao/codex-autoresearch/tree/0f54c571707487f59486ba7c50d405edfc746c19) | Frozen scoped run configuration, explicit finite metric parser, validated event fold, guard and export. | P1 setup/validation; P2 history/context integration. |
| `evo-hq/evo` | Independent project; relationship unestablished | [c70c04b4](https://github.com/evo-hq/evo/tree/c70c04b4d2da2f2deb95d1d185b07d88d24f2ea7) | Implemented frontier strategies, pooled workspaces, inherited gates, Git bundles, parallel workflow. | P1 parallel engine; P2 memory/UI; P3 providers. |
| `RightNow-AI/autokernel` | Independent project; `fork=false`; README acknowledges autoresearch | [78435821](https://github.com/RightNow-AI/autokernel/tree/78435821cc3d5756ba6ee1785c397f6d8fa8c90d) | Five-stage correctness checks, profiler-guided prioritization, end-to-end verification. | P1 qualification pattern; P2 domain-specific adapter. |
| `OpenNSWM-Lab/FAROS` | Independent project; `fork=false` | [60ce4bc2](https://github.com/OpenNSWM-Lab/FAROS/tree/60ce4bc235f169d71f2d11dbe37445b4e402b528) | Evidence-bound human signoff, identity checks, hashed plan deltas, container execution profiles, claim/evidence links. | P0/P1/P2 concrete reusable mechanisms. |
| `EvoMap/AutoResearch` | Independent project; `fork=false` | [21f59129](https://github.com/EvoMap/AutoResearch/tree/21f591298aca78690722686c38984ac2b7d6f7e6) | Unit/cycle/artifact-bound review producer receipts, critic and blind-review stages, queue enforcement. | P1 reviewer receipts; P2 critic workflow. |
| `alchaincyf/darwin-skill` | Independent skill/protocol; `fork=false` | [8a8b6625](https://github.com/alchaincyf/darwin-skill/tree/8a8b66258e3c45d6ae4aea39719468c6428fcb0a) | Paired qualitative judgment, real-test/dry-run labels, human checkpoints, marginal-gain stopping. | P2 qualitative evaluation; protocol evidence only. |

Root licenses at these pins were inspected for the independent projects: MIT for
MLX, pi, codex, AutoKernel, FAROS, and Darwin; Apache-2.0 for evo and EvoMap. The three
platform forks say MIT in README but expose no root LICENSE in the inspected tree
and GitHub license metadata is null. Before importing literal code, verify the
specific file's provenance and retain required notices. Most recommendations below
are interface/protocol adaptations, with this repo's tests and invariants retained.

## Prioritized Adoption Matrix

Effort is relative: S = one focused interface/adapter; M = several modules and
contract tests; L = scheduler, state, or trust-boundary work. It is not a delivery-time
estimate. Priority includes dependencies and the user's independent-review/top-k
requirements, not repository popularity.

| Priority | Feature to absorb | Donor evidence | Increment over current repo | Effort / dependency |
|---|---|---|---|---|
| P0 prerequisite | Correct terminal acceptance, orphan deadlines, aggregate ceilings | Local worker/controller; document audit | Fix existing correctness before increasing search width. | S–L; existing P0-1/P0-2/P1-2 plan. |
| P0 | Qualified executor profiles and container lifecycle | FAROS Docker backend | Actual network/process/resource boundary beyond source hashing and flock. | L; integrate with independent supervision and frozen contract. |
| P1-1 | General-purpose frozen experiment specification and baseline gate | codex + pi | A usable subject-adapter setup path: scope, metric schema/direction/target, guards, inputs, budgets, and both Git refs. | M; reuses current campaign/verifier machinery. |
| P1-2 | Independent reviewer identity and evidence-bound decision receipts | FAROS + EvoMap | Enforce who reviewed, which artifact/round was reviewed, and whether it remains current. | M–L; require authenticated principals and source application. |
| P1-3 | Repeat/seed qualification and correctness-first promotion | MLX + AutoKernel; FAROS comparability | Establish validated-positive eligibility before top-k ranking. | M; subject defines statistics, margins, and scientific meaning. |
| P1-4 | Resource-aware frontier strategies, workspace pool, recoverable candidate snapshots | evo | Implement the planned N/C/k search without N public branches or shared mutable runs. | L; gated by P0 and P1-2/P1-3. |
| P2-1 | Durable resume context and conditional failure revisitation | pi + codex + evo | Derive a compact fresh-agent context and retrieve prior failures with their invalidation conditions. | M; use canonical ledger/archive references. |
| P2-2 | Typed feedback-to-plan deltas and inherited acceptance conditions | FAROS | Turn approved reviewer feedback into an auditable next-plan change with verified evidence references. | M; depends on review identity and dual-repository ownership. |
| P2-3 | Frontier/claim/evidence/decision observability | evo + FAROS; codex exports | Add search-tree and reviewer views to the existing history/bilingual dashboard. | M; integrate into planned authenticated HTTPS service. |
| P2-4 | Resource/capability preflight and optional bounded hooks | jsegov + pi | Record supported hardware modes and integrate project events without changing a frozen run. | S–M; hooks remain declared, budgeted, and advisory. |
| P3 | Training-backend ports, advanced exploration, remote providers | macOS/AMD/MLX forks + evo | Additional platform/provider reach after core search and review qualification. | M–L; separately qualify metrics, cancellation, and leases. |

## P0: Execution Containment and Existing Blockers

FAROS's [docker_backend.py](https://github.com/OpenNSWM-Lab/FAROS/blob/60ce4bc235f169d71f2d11dbe37445b4e402b528/backend/app/code/sandbox/docker_backend.py#L110)
constructs a Docker profile with network disabled, memory/CPU/PID limits,
capability dropping, a read-only root filesystem, temporary scratch, and a selected
GPU. Its timeout path explicitly removes the container after killing the Docker
client. Those are concrete patterns for an executor adapter.

Adapt them to this repo's stronger frozen-source requirements: separate read-only
source/input mounts and writable output/scratch mounts, a controlled execution UID,
pinned images, independent hard deadlines, and resource reservations. The donor's
workspace is mounted read-write and its UID follows the operator; those defaults do
not themselves establish the intended frozen-source boundary. Container removal is
useful but does not replace tested controller/supervisor-loss behavior.

The current local [correctness pipeline](https://github.com/RightNow-AI/autokernel/blob/78435821cc3d5756ba6ee1785c397f6d8fa8c90d/bench.py#L641)
shows why execution validity must precede performance promotion. Independently,
local `worker.py` still computes scientific acceptance from return code and verifier
without requiring `execution_status == completed`. Fix that known timeout case,
orphan supervision, and resource ceilings before parallel dispatch. These are local
prerequisites, not evidence that a donor already solved this runtime's lifecycle.

## P1-1: Frozen Experiment Specification for a Subject Peer

Borrow the codex [run validation](https://github.com/leo-lilinxiao/codex-autoresearch/blob/0f54c571707487f59486ba7c50d405edfc746c19/scripts/autoresearch_core.py#L238)
and [explicit metric parser](https://github.com/leo-lilinxiao/codex-autoresearch/blob/0f54c571707487f59486ba7c50d405edfc746c19/scripts/autoresearch_core.py#L933),
plus pi's [metric/check contract](https://github.com/davebcn87/pi-autoresearch/blob/04b8a50dac7efe80ffc91648bd00ed9b022e24c2/README.md#L144).

Add a generic `ExperimentSpec` builder that a subject adapter fills with original
instruction, exact subject root, allowed mutation paths, benchmark input/version,
metric name/unit/direction, explicit finite numeric parser or JSON selectors,
regression guards, baseline, timeout/budget, and framework/subject Git identities.
Baseline must pass guards and produce valid outputs before searching.

The runtime already freezes argv/closures and checks exact JSON values. Preserve
that implementation; the increment is usable setup and explicit metric/comparison
semantics, not a second executor. Subject Git owns scientific criteria and adapters;
`autoresearch` Git owns schema/compiler/validation and reusable examples.

Keep declared argv execution and structured output validation. Do not adopt a loose
shell-string interface, a named-branch prerequisite in framework Git, or unrestricted
agent edits to measurement/guard scripts after admission. Setup can author proposals;
only the frozen contract authorizes execution.

Acceptance: a CPU subject fixture can declare any finite numeric objective and guard,
with both repository pins, then reject malformed/nonfinite output, scope drift,
failed baseline, or an incompatible benchmark definition before promotion.

## P1-2: Independent Review as a Verified State Transition

FAROS [signoff subjects](https://github.com/OpenNSWM-Lab/FAROS/blob/60ce4bc235f169d71f2d11dbe37445b4e402b528/backend/app/modules/review/human_signoff.py#L64)
binds plan/repair/conclusion stages to current evidence; its
[signoff endpoint](https://github.com/OpenNSWM-Lab/FAROS/blob/60ce4bc235f169d71f2d11dbe37445b4e402b528/backend/app/modules/review/reviews_api.py#L1943)
derives actor identity from authorization rather than trusting the request's
reviewer name. Its [identity tests](https://github.com/OpenNSWM-Lab/FAROS/blob/60ce4bc235f169d71f2d11dbe37445b4e402b528/backend/tests/test_reviewx_signoff_identity.py#L50)
cover spoofed actor names, unauthorized judges, and restricted release assurance.

EvoMap's [review producer](https://github.com/EvoMap/AutoResearch/blob/21f591298aca78690722686c38984ac2b7d6f7e6/ar-runtime/scripts/ar-review-contract.ts#L76)
and [review receipt checks](https://github.com/EvoMap/AutoResearch/blob/21f591298aca78690722686c38984ac2b7d6f7e6/ar-runtime/scripts/ar-workflow-engine.py#L1658)
require unit/cycle/provenance, artifact hashes, current producer receipts, and
consistent blocker reporting. Its workflow also enforces a blind-review stage
before closure, including negative-result workflows.

Absorb the content/producer binding and role checks into the planned `RoundReview`:
trusted reviewer principal, proposer/author separation, candidate/selection hashes,
validated receipt refs, exact next-slate hash, budget/scope, both repository pins,
and source checkpoint receipt. A detached human/model review record is assessable
only when those bindings match. Changed evidence/slate makes it stale.

Keep reviewer authorization, model criticism, measured scientific support, and
source application as distinct states. Do not hardcode Gemini/Qwen roles, copy
paper-rating thresholds, or treat self-reported model identity or multiple model
names as enforced independence. A blind context is useful but is not an access
boundary. Existing same-UID receipts retain their stated procedural trust limits.

Acceptance: author/self-review, forged actor, stale report, changed slate, wrong
project, and unsigned/untrusted decision provenance cannot start a successor round.

## P1-3: Qualification of Positive Outcomes

MLX [rigor.py](https://github.com/trevin-creator/autoresearch-mlx/blob/766a25ff22afa799efd8d0aa450a4348e4749df2/rigor.py#L79)
implements a sample ledger, repeated-run comparison, deterministic bootstrap draws,
and an early screen. AutoKernel's
[five-stage checks](https://github.com/RightNow-AI/autokernel/blob/78435821cc3d5756ba6ee1785c397f6d8fa8c90d/bench.py#L641) separates smoke,
shape/dtype sweep, numerical stress, determinism, and other correctness validation
from timing; [end-to-end verification](https://github.com/RightNow-AI/autokernel/blob/78435821cc3d5756ba6ee1785c397f6d8fa8c90d/verify.py#L1)
provides a second integration-level measurement surface.

Adapt these into a generic qualification contract with explicit seed/replicate IDs,
matched baseline/candidate inputs and budgets, scientific constraints, minimum
meaningful effect, uncertainty/multiplicity policy, and all samples/failed trials.
The subject adapter supplies domain-specific numerical or behavioral checks. The
framework tracks the protocol and prevents incomplete/invalid runs from eligibility.

Important code-level limits: MLX `rigor.py` calls the same `run_once()` in its
`--seeds` loop, while [training](https://github.com/trevin-creator/autoresearch-mlx/blob/766a25ff22afa799efd8d0aa450a4348e4749df2/train.py#L400)
sets `mx.random.seed(42)`. This is repeated fixed-seed execution, not explicit distinct
seed qualification. Its identity is only a shortened hash of `train.py`, ignoring
input/environment changes. Its first-sample early rejection and bootstrap comparison
also do not supply a complete adaptive/multiple-comparison promotion policy.

Use full protocol/source/data/environment identities for result reuse. Repeated
verification must remain possible under a declared protocol; never-repeat by code
hash alone is inappropriate for noisy measurements. The donor's probability display
and pi's improvement/noise ratio are diagnostics, not universal significance gates.
AutoKernel `--quick` explicitly skips stages: useful screening, insufficient as the
full qualification evidence by itself.

Acceptance: top-k is chosen only from completed, comparable, validated-positive
candidates. No candidate qualifies solely because it has the best observed noisy
score, a majority tie, an LLM rating, or a successful cheap screen.

## P1-4: Frontier Search with Controlled Git Cost

Evo has an actual [top-k implementation](https://github.com/evo-hq/evo/blob/c70c04b4d2da2f2deb95d1d185b07d88d24f2ea7/plugins/evo/src/evo/frontier_strategies.py#L218),
other exploration/Pareto strategies, a
[leased workspace pool](https://github.com/evo-hq/evo/blob/c70c04b4d2da2f2deb95d1d185b07d88d24f2ea7/plugins/evo/src/evo/backends/pool.py#L42),
[commit-bundle transport](https://github.com/evo-hq/evo/blob/c70c04b4d2da2f2deb95d1d185b07d88d24f2ea7/plugins/evo/src/evo/git_bundle.py#L34),
and [inherited pre/post gates](https://github.com/evo-hq/evo/blob/c70c04b4d2da2f2deb95d1d185b07d88d24f2ea7/plugins/evo/src/evo/core.py#L1306).
Its [resource sizing guidance](https://github.com/evo-hq/evo/blob/c70c04b4d2da2f2deb95d1d185b07d88d24f2ea7/plugins/evo/skills/discover/references/sizing-the-round.md#L3)
correctly separates independent edits from timing-sensitive benchmark concurrency.

Borrow a pluggable frontier comparator, explicit lineage, gate inheritance, pooled
workspaces, and recoverable snapshot objects. Compile one finite reviewed round
under one aggregate admission; dispatch at most C units and preserve all charges.
Apply root scientific constraints to descendants before ranking; descendants can
add constraints, but cannot silently remove inherited constraints from the contract.

Use the existing planning choices: configuration trials need immutable manifests;
code trials use detached commits/private archival refs in **subject Git**. Publish
at most k retained subject path branches plus an optional campaign branch. Candidate
Git objects must be archived before workspace/ref cleanup. Framework Git receives
only scheduler/protocol changes, never experiment branches.

Evo's top-k comparator ranks supplied nodes; it does not itself establish validated
positive support or independent next-iteration authorization. Its default unattended
continuation and per-branch follow-ups must be constrained by our finite slate and
mandatory reviewer gate. The pool currently performs branch checkouts; adapt its
lease mechanics to detached snapshot ownership and the shared-branch bound.

Acceptance: N=24/C=4/k=3 can evaluate a finite batch with isolated runs, retain fewer
than k when evidence requires, restore a losing snapshot, and launch no successor
until the independently approved exact next slate is applied.

## P2: Memory, Feedback, and Product Features

- **Resume/context:** pi's
  [persisted-state compaction](https://github.com/davebcn87/pi-autoresearch/blob/04b8a50dac7efe80ffc91648bd00ed9b022e24c2/extensions/pi-autoresearch/compaction.ts#L45)
  carries baseline/best, current segment, recent runs, and an ideas backlog. Codex
  [event loading/folding](https://github.com/leo-lilinxiao/codex-autoresearch/blob/0f54c571707487f59486ba7c50d405edfc746c19/scripts/autoresearch_core.py#L413)
  rejects missing/partial/contradictory state. Generate a bounded subject-specific
  context pack from this repo's canonical ledger/manifests and artifact links.
  Keep SQLite/outboxes as authority; JSONL is an export/audit surface, not a replacement
  for stronger transactional state already present here.
- **Failure revisitation:** pi's
  [revisit fields](https://github.com/davebcn87/pi-autoresearch/blob/04b8a50dac7efe80ffc91648bd00ed9b022e24c2/extensions/pi-autoresearch/index.ts#L2207)
  records hypothesis, rollback reason, next hint, and `revisits_run`. Make changed
  assumptions and related evidence explicit. Connect this to existing context-change
  rebrainstorming; a prior failure is neither permanently forbidden nor automatic
  permission to rerun. Verification repeats remain distinct from revived hypotheses.
- **Feedback-to-plan changes:** FAROS
  [PlanDeltaContract](https://github.com/OpenNSWM-Lab/FAROS/blob/60ce4bc235f169d71f2d11dbe37445b4e402b528/backend/app/modules/review/plan_delta.py#L75)
  binds benchmark, trigger/evidence, feasible candidates, field-level before/after
  changes, and a content hash. Its
  [condition verification](https://github.com/OpenNSWM-Lab/FAROS/blob/60ce4bc235f169d71f2d11dbe37445b4e402b528/backend/app/modules/review/human_feedback_verification.py#L62)
  invalidates conditions when their subject changes. Adapt this into a model-neutral
  reviewed next-slate delta in subject Git. A proposed expected effect is not observed
  proof; non-waivable scientific constraints remain non-waivable.
- **Dashboard and sharing:** borrow evo's frontier/backend views and FAROS claim/evidence/
  signoff connections. Extend this repo's working immutable report history, bilingual
  UI, and offline export with candidate lineage, qualification samples, reply parents,
  reviewer bindings, and delivery/application/archive states. A replaceable HTML page
  remains a view. Donor local dashboards do not establish production HTTPS/authentication.
- **Bounded hooks/preflight:** pi
  [hook contract](https://github.com/davebcn87/pi-autoresearch/blob/04b8a50dac7efe80ffc91648bd00ed9b022e24c2/extensions/pi-autoresearch/hooks.ts#L7)
  has typed payloads, timeout, and output limits; jsegov
  [GPU profiles](https://github.com/jsegov/autoresearch-win-rtx/blob/a4123c6e5c6287f90be04026642ba20b94e424df/train.py#L57)
  records architecture/precision/VRAM-related modes. Declare and budget hooks before
  admission; output is advisory. Probe hardware before freezing the contract; changing
  precision, batch, compilation, or validation data cannot happen silently mid-run.
- **Qualitative tasks:** Darwin's
  [paired comparison protocol](https://github.com/alchaincyf/darwin-skill/blob/8a8b66258e3c45d6ae4aea39719468c6428fcb0a/SKILL.md#L211)
  is preferable to unrelated absolute judge scores, and its human checkpoint and
  real-test/dry-run labels are useful. Adopt as an optional subject evaluation protocol,
  not the default scientific validator. It is instruction-level evidence; its
  tie-inclusive keep rule does not satisfy this repo's positive-outcome criterion.

## P3 and Items to Defer

Platform code is useful as a reference for subject adapters: macOS
[MPS/SDPA path](https://github.com/miolini/autoresearch-macos/blob/537c6e6d0ecf7d28f9d70ce20bb05d8c7ed9cfce/train.py#L1), AMD
[ROCm path](https://github.com/andyluo7/autoresearch/blob/c2c12b281c275850705031837e0f5712488a3982/train.py#L20), Windows profile logic, and
native MLX. Do not add their training dependencies to the generic runtime. A macOS
training port does not make the current Linux `/proc` worker supervision portable.
AMD's SDPA path notes that the sliding-window pattern degrades to full attention;
that is a semantic change requiring qualification, not merely a packaging change.
Cross-hardware metrics require new evidence and cannot be pooled as equivalent wins.

Evo's provider surface is a useful later interface reference, but every remote
executor still requires query/cancel, identity, receipt, resource/lease, hard-deadline,
and recovery qualification. Hosted UI access does not authorize remote shell execution.

Defer entire FAROS/EvoMap scientist stacks, broad paper/literature pipelines,
provider credentials/SDKs, and automatic source mutation. Import the narrow contracts
needed by this runtime. AutoKernel's profiling/Amdahl prioritization is a valuable
subject-specific cost/benefit adapter when optimizing kernels, not a universal
scientific ranking function. Commercial marketing numbers and paper-review ratings
are not evidence for an adoption benefit.

## Adoption Sequence and Repository Boundaries

1. Complete existing terminal-validity/supervision/ceiling work and qualify the
   executor profile. Monitoring-only HTTPS work can proceed independently.
2. Implement frozen `ExperimentSpec`, reviewer provenance/round bindings, and
   qualification contracts with a CPU subject fixture.
3. Add frontier/pool/snapshot mechanics behind those gates; prove bounded concurrency,
   budget/lease behavior, and independent next-round authorization on Linux.
4. Add canonical resume packs, failure retrieval/revisit evidence, and typed plan deltas.
5. Add candidate/review/audit views to authenticated HTTPS hosting and share exports.
6. Qualify additional training backends, exploration strategies, or remote providers
   only for explicit subject needs.

`autoresearch` Git owns reusable schemas, scheduler/executor interfaces, protocol
validation, audit transports, generic UI, and deployment examples. Subject Git owns
hypotheses, scientific acceptance rules, benchmark/verifier code, mutation scope,
candidate commits, plan amendments, and retained paths. Durable run stores and remote
artifact/message archives own operational traffic. Every adoption test records both
Git identities; a donor's single-repository assumptions cannot collapse these peers.

Do not silently upgrade a pinned running campaign. Scheduler/goal/confirmation
changes require explicitly versioned behavior adopted for new campaigns, with legacy
single-path behavior kept assessable. Decisions bind current candidate/evidence and
next-slate hashes; Git merge/rebase or changed evaluation inputs require revalidation.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-28T15:03:56-07:00 | Read document revision 33; pinned and inspected 11 repositories; preserved the exact request; prioritized concrete transferable features against current runtime gaps and peer-checkout/top-k/reviewer requirements, with source links and adoption limits. |
