# Contextual, narrative-first research review

Created: 2026-10-12 17:10 -0700
Status: generic0.4.1 implementation and source/clean-wheel76-test verification complete; both-locale renderer checks pass. Local commit/review-only adoption follow; scientific runtimes remain pinned.

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

## Generic mechanism

Add optional versioned schema2 `narrative` containing source-backed structured changes (before/after/why it matters), remaining questions (question/why unanswered/goal impact/next evidence), and descriptive insights (comparison/support/finding/interpretation/goal relevance/caveat). Validate IDs, required context, text sizes and released source indices. Preserve numerical evidence validation separately; narrative references prove provenance, not scientific truth. Locale overlays can change text but never IDs, source refs or permissions.

Render contextual sections and an expanded evidence explanation before a separately collapsed raw metric table. Legacy packets remain valid, with explicit no-interpretation guidance rather than invented insights. The overview builder can accept complete authored narrative/changed/limitations or derive honest contextual summaries from the supplied workflow (not guess previous outcomes or raw metric meaning). Controller contracts can supply pending narrative and a fixed result-JSON narrative pointer; invalid/missing completed narrative produces explicit report failure rather than silently fabricated findings. Immutable old contracts are not edited for adoption.

Document authoring requirements and add an unrelated image-upload example, unit/locale/controller and actual renderer tests. Build a new review-only0.4.1 wheel, test it in isolation, commit locally and pin it separately from scientific0.4.0/0.2.0 execution. Project adapters must supply detailed domain interpretations; software can enforce their presence/bindings but cannot certify them from prose. No independent reviewer or automatic scientific inference.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 17:10 -0700 | Preserved all3 requests and designed generic context schemas/authoring, narrative-first renderer, safe controller/builder paths and strictly display-only locale/test/adoption boundary. |
| r2 | 2026-10-12 17:30 -0700 | Implemented0.4.1 schemas/builder/controller/locale/renderer, documented generic authoring example and verified76 source/wheel tests plus both-locale renderer. Report failures preserve scientific receipts; no scientific pin change. |
