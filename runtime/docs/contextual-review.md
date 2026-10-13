# Contextual changes and descriptive evidence review · 0.4.1

A research inbox must explain what a finding changes about the project goal—not merely list executed jobs or display numbers. Runtime0.4.1 adds a project-neutral, source-backed `narrative` to schema2 review packets and overview documents. The same schema works for ordinary studies and consolidated overviews; no H3, GPU or ML knowledge is built into it.

## What the reader sees

1. **What changed, and why it matters:** the previous question/state, the new observation, and why it changes the next decision.
2. **What remains unanswered, and why:** the unresolved claim, why current evidence is insufficient, its consequence for the goal, and the evidence needed next. Workflow permissions stay in the separate steering section.
3. **3-minute evidence review · what the findings mean:** comparison/control, support, finding, interpretation, goal relevance and caveat. This is expanded by default. The raw metric table sits inside collapsed **Technical detail · exact metrics, rules and scope**. Hash-bound source snapshots remain available.

The framework does not infer causality, scientific success or uncertainty from raw numbers. The project agent/adapter supplies accurate explanations, including negative and inconclusive outcomes. A source reference proves provenance, not the truth of prose. Numeric metrics retain their separate exact JSON-selector validation.

## Schema

Optional packet field `narrative`:

```json
{
  "schema_version": 1,
  "changes": [{
    "id": "encoder-result",
    "title": "Smaller files shift the next question to quality",
    "before": "Original photos used more bytes; whether compression would help was unknown.",
    "after": "The new encoder produced smaller files on the same comparison images.",
    "why_it_matters": "Transfer-size evidence improved; we must now check whether detail is preserved.",
    "evidence": [0]
  }],
  "limitations": [{
    "id": "unseen-quality",
    "question": "Will new photos retain visual detail?",
    "why_unanswered": "This comparison measured file size, not visual quality on unseen images.",
    "goal_impact": "Faster uploads are not useful if photos lose important detail.",
    "next_evidence": "A prespecified quality assessment on held-out photographs.",
    "evidence": [0]
  }],
  "insights": [{
    "id": "size-not-quality",
    "title": "Reduced bytes are a promising intermediate result",
    "comparison": "Two encoders applied to the same images with upload settings fixed.",
    "support": "State the actual image count, independence/grouping and coverage here.",
    "finding": "Describe the observed change and baseline, with numbers where they help.",
    "interpretation": "Smaller files can reduce transfer work, but file size is not a visual-quality test.",
    "goal_relevance": "The next useful decision is whether quality remains acceptable, not simply how to shrink files further.",
    "caveat": "Do not claim unseen-image or production performance from this panel.",
    "evidence": [0]
  }]
}
```

All3 sections are required when `narrative` is supplied. Changes/limitations allow1–6items; insights1–12. Each item has a unique stable ID, all explanatory text fields, and distinct valid released source indices. Empty text, omitted context, invalid/bool/out-of-range/duplicate references and unknown fields are rejected. The narrative is part of the immutable packet hash; corrections require a new packet revision. Legacy packets stay valid and show an explicit missing-explanation note rather than a fabricated insight.

### Authoring rules

- Say what was actually compared and controlled; explain abbreviations, estimator/metric meaning and baseline.
- State the number of independent kernels/images/configurations separately from repeated seeds/windows. Do not count repeated summaries as independent evidence.
- Explain why an observation matters for the end goal and what decision it changes. A valid process exit is not the finding.
- State why the evidence does not answer a specific broader question. 'No promotion' or 'unqualified' alone is not a helpful limitation.
- Preserve all failures and fixed gates; explain a failed prerequisite rather than masking it with a pooled number.
- Before/after refers to the earlier scientific question/interpretation and current finding, not an invented claim that the last packet said something it did not.
- Missing observations are 'not collected yet', not planned successes. No private reasoning or unopened evidence is included.

## Builders and automated publication

`overview.json` accepts optional `changed`, `limitations` and `narrative`. Explicit authored lists are used unchanged after validation. Without them, the builder derives contextual summaries from the supplied goal/current question/next checkpoint and last6effort records. It reuses their reported outcome, rationale and uncertainty; it cannot infer observation counts absent from the source. For detailed support/control explanations, supply authored `narrative` rather than rely on this fallback.

New Controller tasks can declare:

- `review_changed: {pending: [...], completed: [...]}` for phase-specific plain summaries.
- `review_narrative: {pending: {...}, completed: {...}}` for fixed explanatory records.
- `report_narrative_pointer: "/review/narrative"` to read a completed explanation from the task's fixed result JSON. It is validated and published with the source0 released unit evidence. A missing/malformed result narrative produces a report-schema failure, never an invented explanation or new authorization.

Controller-generated packets keep declared source/scientific/approval/resource gates. A default completion string now names the study and its declared check result; default limitations explain the restricted scope rather than repeat 'execution success is not qualification'. High-quality domain insight still requires the adapter's authored narrative. Never modify old initialized contracts to add these fields; adopt in a new campaign/runtime or a separate review-only publisher.

## English / Simplified Chinese

`translations.zh-CN.narrative` may contain `changes`, `limitations`, and/or `insights`. Included arrays must match canonical length/order and each exact item ID. Only explanatory text may be overlaid; no schema version, evidence index/path/hash, metric value, action or eligibility can be translated into a different value. Untranslated fields fall back to canonical text. IDs/source references stay unchanged in Chinese. Text is escaped in the browser and offline export; raw source bytes and feedback remain in their original language.

The generic section labels and fallback text are translated. Project adapters must supply faithful scientific Chinese narration when available; the runtime does not silently translate scientific evidence.

## User Prompts, Verbatim

```text
the current "What changed" gives no context, and use generic terms that's hard to interpret. Also "What this does not establish" suffers the same deficiency.
```

```text
also "3-minute evidence review · metrics, controls and scope" should give detailed descriptive insights, not throwing raw data at me.
```

```text
make the meta change to the auto-research framework.
```

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 17:20 -0700 | Documented generic source-backed contextual explanations, narrative-first evidence review, builder/controller authoring, immutable/locale boundaries and explicit non-inference/legacy limits; all exact requests preserved. |
