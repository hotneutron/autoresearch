# Workflow overview: a newcomer-friendly decision record

Runtime **0.3.0** adds an advisory-only overview document and a **Start here** inbox view. It works for any project: no H3, GPU, ML or repository-specific dependencies. The agent or project adapter writes accurate public summaries; the runtime validates structure, released evidence links and feedback boundaries. It does not generate private chain-of-thought or infer scientific decisions from plan filenames.

## Use it in another project

```bash
python3.11 -m pip install ./runtime
# Demo is illustrative and runs no experiment:
autoresearch --store /tmp/image-review review overview \
  runtime/examples/workflow-overview/overview.json \
  --repo runtime/examples/workflow-overview
autoresearch --store /tmp/image-review review serve --port 8765
# Read-only export, with all released evidence embedded:
autoresearch --store /tmp/image-review review export --output /tmp/image-review.html
```

Open http://127.0.0.1:8765 and select **Start here**. The example is an image-upload project and is explicitly not measured research. Replace its document with your own project goal, terminology and evidence. `autoresearch-review --repo PROJECT --store STORE overview overview.json` is an equivalent publication entry point. Plain schema-2 packets can now also be published with `autoresearch ... review publish packet.json --repo PROJECT`.

Use a stable **project review store** across campaigns if you want a persistent decision trail. This command does not automatically aggregate arbitrary campaign databases or copy private files. Existing stores keep their own execution identity; do not install new code underneath an active pinned runtime. Use a separate review-only environment/store, or adopt 0.3.0 when preparing a new frozen campaign.

## Contextual changes and evidence explanations · 0.4.1

See [the contextual-review schema and authoring guide](contextual-review.md).
Overview documents now accept optional authored `changed`, `limitations` and
structured source-backed `narrative`. Defaults reuse supplied effort outcomes,
rationales and uncertainties—not generic publication/private-reasoning boilerplate.
The inbox explains comparison, support, finding, interpretation, goal relevance
and caveats before optionally expanded raw metrics. Ordinary study packets use
the same generic structure and strictly display-only Chinese overlays.

## What a newcomer sees

1. **Start here:** human-readable project name, goal, short background and plain-language success criteria.
2. **Where we are:** explicit planned/running/completed/blocked/deferred/stopped/awaiting-context-change state, current question, next checkpoint, author-reported timestamp and publication time. `awaiting_context_change` means the current candidate slate is scientifically exhausted and names the evidence, architecture, authority or infrastructure change required before proposing another campaign; it is distinct from an operational block. This is a snapshot, not inferred job liveness.
3. **Glossary:** domain terms explained without assuming project expertise. Metrics still include units, observation counts and acceptance rules.
4. **What we tried, why and what we learned:** each effort's question, motivation, approach, alternatives and why they were not chosen, outcome, decision, concise rationale, uncertainty and next step. A completed but negative or inconclusive study is not mislabeled as a program failure.
5. **Evidence:** selected immutable text snapshots, one click away. Valid evidence is not automatic scientific qualification, deployment permission or a model-success claim.
6. **How to steer:** suggest a direction on the overview; open the current linked study to approve or pause its exact named actions. Receipt delivery and actual adoption of feedback are shown separately.

## Document schema

`overview.json` has schema version **1** for this builder. It generates a normal schema-2 packet with optional validated `workflow` metadata, `project_id`, a stable `<project_id>-overview` branch and consecutive `<branch>-rN` IDs. It always has `actions=[]` and advice mode. The database/store schema stays at version 2; old ordinary review packets remain readable.

Required document fields:

| Field | Meaning |
|---|---|
| `schema_version` | Exactly 1 |
| `revision` | Positive consecutive integer within this overview branch |
| `summary` | Plain-language brief (maximum 320 characters) |
| `prompt_verbatim` | Exact instruction authorizing the work, not an invented approval |
| `sources` | 1–12 selected released evidence files, with `label`, `path` and optional expected `sha256` |
| `workflow` | Structured overview described below |
| `metrics` (optional) | Existing typed schema-2 metric objects; values must match JSON source selectors |

Required workflow fields:

- `kind`: exactly `overview`.
- `project_id`: stable machine identity; `project_name`: human-readable name.
- `goal`, `background`, `success_criteria`: plain-language introduction. Explain technical abbreviations in the glossary.
- `status`, `current_question`, `next_checkpoint`, `updated_at`: an explicit checkpoint with timezone-bearing ISO timestamp. Do not claim a unit is live unless the project has verified it.
- `glossary`: list of `{term, meaning}` objects, at most 40 distinct terms; can be empty when there are no unfamiliar terms.
- `efforts`: ordered list, at most 100. Empty is valid before work starts. For each effort provide `id`, `title`, `status`, `question`, `motivation`, `approach`, `alternatives` (`[{option, reason}]`), `outcome`, `decision`, `rationale`, `uncertainty`, `next_step`, and `evidence` (distinct source indices). Say “not collected yet” rather than fabricating a planned outcome. Alternatives can be empty when none were relevant.
- `feedback_dispositions`: list of `{feedback_id, disposition, reason, evidence}`; dispositions are `adopted`, `deferred` or `declined`. Empty is valid. References must point to actual **applied** feedback in this overview or a linked same-project study. These are the agent's documented decisions, not automatic proof of adoption.

Sources must be `.md`, `.json`, `.csv` or `.txt` within `--repo`, at most 2 MB each. Symlink/path escapes fail. Publication snapshots and hashes the actual released bytes. A narrative source reference establishes provenance, not the truth of free-text prose. Numeric metrics use the existing exact-type/value JSON selector validation. Never select private confirmation labels or logs as overview evidence.

Optional effort `target`:

```json
{"packet_id": "study-r4", "packet_hash": "<exact published 64-character SHA-256>"}
```

The target must already exist in the **same store**, carry the same declared `project_id`, and be an ordinary study packet, not another overview. The exact hash is checked. Its historical result remains bound to that revision; the UI identifies when it has been superseded and offers the current study report for steering. Links do not import authority or approve anything. For automatic runtime packets, freeze optional top-level `project_id` in a **new** campaign contract; the controller carries it into each study packet. An established branch cannot change project identity or be converted from execution to overview. Legacy study packets without project identity can remain evidence, but cannot be strict steering targets until published on a new explicitly project-tagged branch.

## Agent/checkpoint integration

At design freeze, completed study, pivot, feedback disposition, or budget boundary:

1. Verify actual job/receipt/feedback state and use only released data.
2. Update your document's status and effort entries with the question, why the attempt was informative, alternatives, fixed outcome, uncertainty and decision rationale. Do not rewrite old scientific verdicts.
3. Select compact evidence and exact current study targets. Consume feedback at existing safe checkpoints; then document adopted/deferred/declined advice with its actual applied feedback ID and reason.
4. Increment `revision`, save a timestamped project artifact, and invoke `publish_overview` or `review overview`. Preserve earlier packet IDs; they are immutable.
5. Continue only eligible declared work. Overview publication never submits a job, changes resource budgets, modifies gates or assumes user approval.

A project integration may call this automatically at its legal checkpoints, but the runtime does not invent the scientific explanation. It deliberately does not silently merge unrelated campaign stores, auto-follow private sources or grant project-wide pause semantics. The host project owns any cross-campaign state pointer and evidence-release policy.

## Feedback semantics

**Overview:** comments and mark-read only. Approve/reject/pause/resume submitted to an overview are rejected even if a client bypasses the UI. A comment becomes `applied` when delivered at a safe checkpoint; it is not necessarily adopted. The subsequent overview must explain the actual response in `feedback_dispositions` when known.

**Study:** existing revision/hash-bound approval, hard eligibility checks and safe-boundary pause/resume continue unchanged. Follow the study link and inspect current evidence first. No response, overview acknowledgement, positive narrative or expired review window can approve an experiment.

## English / Simplified Chinese presentation (0.3.1)

Open `http://127.0.0.1:8765/?lang=zh-CN` or choose **简体中文** in the language selector. `?lang=en` switches back. The UI remembers the preference locally and uses the browser's Chinese locale only when there is no explicit choice. Ordinary packets remain readable with English fallback where translated project content is absent. Offline exports embed the same language resources.

Optional packet or overview-document `translations` supplies **display-only** narrative text:

```json
{
  "translations": {
    "zh-CN": {
      "title": "图片上传研究 · 从这里开始",
      "takeaway": "质量评估尚未完成，因此不授权部署。",
      "workflow": {
        "project_name": "图片上传研究",
        "goal": "更快上传图片，同时保持质量。",
        "efforts": [{"id": "smaller-files", "motivation": "文件大小是可控制的传输时间影响因素。"}]
      }
    }
  }
}
```

Translated effort lists must match the canonical list length/order and exact effort IDs. Other translated arrays also align to their canonical items. Supported text fields are the packet's brief/recommendation/limitations, source labels, metric name/rule/scope, action labels, and workflow goal/background/glossary/effort narrative/feedback reasons. The locale validator rejects any attempt to change machine identities, evidence paths/hashes/indices, scientific numeric metric values, workflow status, action eligibility/approval flags or feedback identity. The entire translation is part of the immutable report hash; editing a translation requires a new revision. A source citation validates provenance, not accuracy of arbitrary translated prose; projects remain responsible for faithful translations.

The browser overlays only these text fields. Feedback still submits canonical packet ID/hash, action ID and kind, even in Chinese. Evidence bodies and user comments retain original bytes and their original language; switching locale is not scientific reclassification or an automatic translation of private files. A language switch preserves the current feedback draft. No locale grants approval or changes safe checkpoint rules.

## Verification and release

```bash
PYTHONPATH=runtime/src python3.11 -m unittest discover -s runtime/tests -v
node runtime/tests/test_workflow_ui.js runtime/src/autoresearch_runtime/inbox.html
```

Tests cover an unrelated image project, ordinary-packet compatibility, strict identities, escaped rendering, typed metrics, immutable sources/revisions, stale study links, real feedback dispositions, HTTP errors, no overview approval/pause/dispatch, and newcomer UI order/glossary/explanations. Validate a wheel in an empty environment before adoption. Existing experiments must retain their prior installed package hashes.

## User Prompts, Verbatim

```text
For the review inbox, I would like it contains overview, the thought process, and reasons for the efforts tried, in addition to the outcome. This way I can moinitor and steer as I see fit.
```

```text
make the inbox comprehensible even for a newcomer.
```

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 12:08 -0700 | Documented reusable overview format, newcomer context, evidence-linked effort rationale, explicit feedback disposition and unchanged execution boundaries, with a non-H3 example. |
| r2 | 2026-10-12 12:56 -0700 | Documented Simplified Chinese selector, strict display-only translation schema and canonical evidence/feedback semantics. |
| r3 | 2026-10-12 17:20 -0700 | Added0.4.1 contextual change/limitation and narrative-first evidence authoring/schema reference for generic overview and study packets; exact requests preserved in contextual-review.md. |
