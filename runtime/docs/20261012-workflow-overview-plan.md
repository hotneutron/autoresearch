# Reusable, newcomer-friendly workflow overview

Status: implementation in progress on `feature/workflow-review-overview`; no installed experiment runtime changed.

## User Prompts, Verbatim

```text
I noticed that you have 10 new plan files 20261009* to 20261012*, how can I track your throught process? through review inbox or some other way?
```

```text
now can I make the workflow "overview card" works for other projects? Will the feature be checked into autoresearch fork?
```

```text
How can I make the workflow "overview card" works for other projects? Will the feature be checked into autoresearch fork?
```

```text
commit when you see fit.
```

```text
For the review inbox, I would like it contains overview, the thought process, and reasons for the efforts tried, in addition to the outcome. This way I can moinitor and steer as I see fit.
```

```text
make the inbox comprehensible even for a newcomer.
```

## Design and boundaries

Add optional structured `workflow` metadata to schema-2 review packets, plus a project-neutral builder/publication command. A separate stable overview branch contains no executable actions or approvals. Existing scientific packets, schema-1 compatibility, execution contracts and feedback gates remain intact. This is a new versioned release, never a mutation of the currently installed H3 runtime.

A newcomer first sees: plain-language project name, goal, background, success criteria, current question/status, glossary and next checkpoint. A visible effort timeline explains the question, why it was worth trying, approach, alternatives and why not chosen, result, decision and concise evidence-backed rationale, uncertainty and next step. Evidence references identify immutable released snapshots. This is public decision documentation, not private chain-of-thought or automatic inference from filenames.

The overview is revisioned and can contain the full history across campaign changes within one stable project review store. The project agent/adapter supplies the records and updates at legal checkpoints; the runtime validates structure, evidence references and identity, not the scientific truth of arbitrary prose. Typed metrics continue to check exact values against JSON selectors. Publication never creates experiments, changes budgets or relaxes gates.

Steering is explicit: comments/mark-read on an overview are advisory. To pause/resume or approve/reject a study, follow a verified link to that study's exact current packet and use its existing branch-scoped feedback. Overview pause/resume/approval are rejected to avoid implying a project-wide effect. Targets are only same-store packets and are verified by ID/hash; stale links are labeled and do not authorize actions. Feedback disposition records must refer to applied same-project feedback and carry adoption/defer rationale and evidence; they do not replace the actual receipts.

The UI keeps technical sources and raw identifiers in expandable details, explains evidence versus scientific success, marks snapshot freshness and does not say work is continuing when no runnable action exists. Search includes glossary/effort text. Ordinary packets remain usable without workflow metadata. Offline exports embed all released evidence and remain read-only.

## Execution plan

1. Implement workflow validator/builder, review publication CLI and safe target/disposition validation.
2. Add a newcomer-friendly Start here view and visible effort/decision timeline, with study-target steering links and evidence controls.
3. Add an unrelated-project example, JSON/schema guide and host-agent checkpoint integration recipe.
4. Run regression/adversarial/HTTP/CLI tests, JavaScript rendering tests and wheel-only tests in an empty environment. Check package resources and no execution changes.
5. Commit tested runtime feature and separately commit completed project artifacts; no push. Adopt a release only through explicit review-only integration or a new frozen campaign pin, preserving active old runtime identities.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 12:02 -0700 | Preserved all feature requirements and committed-work permission verbatim; specified generic content, newcomer UI and revision-bound steering without execution-authority expansion. |
