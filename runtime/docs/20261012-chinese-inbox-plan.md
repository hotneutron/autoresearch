# Chinese review inbox and display-only localization

Status: implementation in progress; changes affect only the review interface and versioned review package, not Accorde's pinned scientific runtime.

## User Prompt, Verbatim

```text
create a chinese version of the review inbox
```

## Design

Provide English and Simplified Chinese (`zh-CN`) interface messages, an explicit language selector and a bookmarkable `?lang=zh-CN` view. Preserve a user's language preference locally; use English fallback when a translation is absent. Translate the newcomer introduction, glossary labels, effort/decision rationale labels, evidence controls, statuses, filters, feedback descriptions and safety warnings. Source evidence and exact user feedback remain original bytes, with a clear notice that switching language does not translate or alter evidence.

Optional packet/document `translations` contain display-only narrative fields. Strict validation rejects changes to identifiers, hashes, numeric results, source paths, action eligibility/approval flags, workflow status, effort IDs, feedback IDs or evidence references. Translated arrays must align with canonical items and the translations are included in the immutable packet hash. The UI overlays only validated text while continuing to submit the canonical packet/action identities. No language choice changes execution gates or feedback meaning.

H3 supplies a reviewed Chinese newcomer overview covering project goal/background, terms, the E1–E6 question/motivation/alternatives/results/decision/uncertainty trail, current budget/checkpoint and a Chinese summary source. E5/E6 result cards can publish new narrative-only Chinese translations referencing the same frozen scientific evidence; original packet revisions stay immutable. Do not translate machine verdicts into different scientific claims.

Package localization resources in a new review patch release, test source and wheel-only installs plus actual English/Chinese renderer behavior and canonical feedback identities. Keep port 8765 stable by replacing only the verified review-server process after compatible-store backup. Accorde's scientific 0.2.0 lock and all receipts remain untouched. Commit tested fork and project translation changes separately; do not push.

E7 preparation remains a separate pending diagnostic under the eight-hour aggregate cap; no E7 measurement or campaign is claimed to have started during this interface work.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 12:47 -0700 | Preserved the exact Chinese-version request and specified display-only localization, canonical evidence/feedback identities, isolated review adoption and regression checks. |
