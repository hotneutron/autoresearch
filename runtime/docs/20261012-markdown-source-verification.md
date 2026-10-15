# Rendered source Markdown0.4.2 verification

Timestamp: 2026-10-12 17:53 -0700
Status: source/clean-wheel tests passed; local commit and review-only adoption follow.

## User Prompt, Verbatim

```text
for the "source report", please show the markdown in rendered format.
```

## Actual verification

- **78 source Python3.11 tests passed**, including2 new exact-source/offline-template injection tests. Existing76 goal/execution/confirmation/narrative/review/locale tests still pass.
- **78 clean-wheel tests passed** in isolated`v0.4.2-review`, no source override.
- Source and installed actual renderer harnesses pass: bilingual narrative/goal controls plus safe Markdown headings/lists/nesting/tables/code, escaped raw HTML, inert dangerous schemes/images, exact raw toggle, Chinese controls, live/offline modal and stale source-switch/close fetch handling.
- `git diff --check` passed.
- Wheel SHA-256`931071aaf5d8c2f17354904978024c4c9448ec78bb29561d009052c272225245`.

The renderer is a bounded local subset, not full CommonMark. Relative links/anchors remain inert text, images do not load and embedded HTML never executes. Evidence source bytes and hashes stay unchanged. Offline marker-looking source text remains data via one-pass template substitution. A browser visual/accessibility audit, independent reviewer and remote push are not claimed. No scientific0.4.0/0.2.0 environment or experiment changes are part of this release.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 17:53 -0700 | Recorded78 source/wheel tests and actual both-locale/Markdown security/modal checks with wheel hash and unchanged evidence/scientific boundaries. |
