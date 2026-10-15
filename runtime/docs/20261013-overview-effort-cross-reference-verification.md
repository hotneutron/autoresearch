# Overview effort cross-reference verification

## User Prompt, Verbatim

```text
for the review inbox, in the "overview" card, "What changed, and why it matters" should have related effort index so I can cross check.
also, provide effort index for "What remains unanswered, and why" as well.
then execute the planned action.
```

## Verified behavior

- Workflow efforts render with stable canonical-order labels`E1`, `E2`, ... .
- Narrative changes and limitations accept optional stable effort IDs.
- Unknown, duplicate, empty and non-workflow effort references fail validation.
- Both requested sections render clickable`E# · effort title` references.
- Clicking a reference scrolls to the matching effort section.
- Simplified Chinese renders`相关尝试索引` while retaining canonical IDs.
- Display translations cannot change effort references.
- Derived overview narratives reference their originating efforts automatically.
- Explicit project narratives must author references; the runtime does not infer
  scientific relationships.
- Legacy packets without effort references remain valid and unchanged.

## Test evidence

- Targeted narrative/workflow/localization tests:19 passed.
- Full source installation:83 Python tests passed.
- Clean0.5.1 wheel installation:83 Python tests passed.
- Source and wheel workflow/goal bilingual UI checks passed.
- Source and wheel safe Markdown live/raw/Chinese/offline checks passed.
- Wheel:`autoresearch_runtime-0.5.1-py3-none-any.whl`.
- Wheel SHA-256:`9814c4d5db9aa27b0ba88a1f1c0e2197ee94c0ed2fa280ba0cd83a6538c57c29`.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-13 00:00 -0700 | Recorded source/wheel/schema/UI verification, exact release identity and legacy/translation safety. |
