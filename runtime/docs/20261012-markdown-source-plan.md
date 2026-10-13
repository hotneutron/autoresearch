# Render source Markdown safely in the review inbox

Created: 2026-10-12 17:43 -0700
Status:0.4.2 implemented and source/clean-wheel78tests plus actual modal/security renderer checks pass. Local commit and review-only adoption follow.

## User Prompt, Verbatim

```text
for the "source report", please show the markdown in rendered format.
```

## Design

Render .md source snapshots in the generic source-report modal with local, dependency-free Markdown support for headings, paragraphs, lists, tables, blockquotes, fenced/inline code, emphasis and safe external links. Keep exact raw text selectable via a View raw source toggle. Non-Markdown JSON/CSV/TXT remain raw. Preserve immutable source bytes/hashes and offline embedding; no evidence is rewritten or reparsed as instructions.

Use a deliberately bounded Markdown subset, not arbitrary HTML. Escape raw HTML and code; never execute scripts, event handlers, iframes or SVG, and do not auto-load images/resources. Links allow only explicitly parsed http/https URLs opened by the reader with noopener/noreferrer; dangerous schemes are inert. Relative source links stay explanatory text rather than accidentally resolving to arbitrary local files or the inbox origin. Relative links and anchors remain inert text rather than resolving outside the snapshot; exact raw view preserves their syntax. Document unsupported syntax/fallback, test malicious inputs and actual source modal in English/Chinese/offline cases, including stale asynchronous fetch cancellation.

Package the renderer in the generic runtime and embed it in HTML for live/offline use without CDN/network dependencies. Release0.4.2 in a separate review-only environment after source/wheel and renderer/security tests, local commit, then adopt only the known review listener. Keep scientific0.4.0/0.2.0 pins untouched. No new experiment, model fit, private data or authorization.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 17:43 -0700 | Preserved exact rendered-source request and designed bounded local safe Markdown modal/raw toggle, offline/locale compatibility and separate review-only adoption. |
| r2 | 2026-10-12 17:53 -0700 | Implemented/tested0.4.2 local renderer and exact raw toggle;78source/wheel tests plus actual modal/security/locale/offline checks pass. Relative/anchor links clarified as inert; no scientific changes. |
