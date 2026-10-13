# Overview narrative effort cross-references

Status: implemented for runtime0.5.1.

## User Prompt, Verbatim

```text
for the review inbox, in the "overview" card, "What changed, and why it matters" should have related effort index so I can cross check.
also, provide effort index for "What remains unanswered, and why" as well.
then execute the planned action.
```

## Design

Overview narrative `changes` and `limitations` accept an optional canonical
`efforts` list containing workflow effort IDs. The validator requires1–12 unique
IDs and rejects references absent from the overview workflow. Study packets without
a workflow cannot claim effort references. Translations cannot change the IDs.

The UI labels every workflow effort `E1`, `E2`, … in canonical order. Both
requested narrative sections render **Related efforts** as `E# · title` buttons;
clicking a button scrolls to the matching effort. Older packets without effort
references remain valid and render unchanged. Evidence-source indices remain
separate and unchanged.

Derived overview narratives automatically reference the effort from which each
change/limitation was built. Explicit project narratives must author their own
references so the runtime never guesses scientific relationships.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-13 00:00 -0700 | Preserved the exact request and specified validated canonical effort IDs, stable E-index rendering, clickable cross-checks, translation safety and legacy compatibility. |
