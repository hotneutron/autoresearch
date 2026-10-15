# Rendered Markdown source reports · 0.4.2

Source reports ending in`.md` open in a **rendered reading view** in the generic evidence modal. The source text and SHA-256 evidence identity are unchanged. **View raw source** shows the exact stored text; **View rendered Markdown** switches back. JSON, CSV and TXT stay raw. Both controls support English/Simplified Chinese.

## Supported safe local subset

- ATX/setext headings, paragraphs and line breaks.
- Unordered/ordered/nested lists and textual task checkboxes.
- Pipe tables, including code/escaped pipes and column alignment.
- Blockquotes, horizontal rules, fenced/indented code blocks and inline code.
- Bold, emphasis and strikethrough.
- Explicit http/https links opened only on a reader click, with`noopener noreferrer`.

No network Markdown library/CDN is required. The bundled renderer is embedded in live/offline HTML. Source paths determine Markdown versus raw display; content is not inferred as an executable format. The language selector translates controls only; source text retains its original language.

## Safety and exact evidence

Raw HTML, scripts, event handlers, SVG, iframe and code contents are escaped. Markdown image syntax displays the alt text only; it never loads an image or remote/local resource. Dangerous link schemes (`javascript:`, `data:`, `file:`, protocol-relative etc.) are inactive text. Relative source links and in-document anchors are also shown as text rather than resolving to unserved local directories or a wrong inbox origin. Complex syntax outside this bounded subset remains readable/raw; this is not a full CommonMark implementation or a directory browser.

The reading view does not modify source snapshots, metric selectors, report hashes, scientific gates, feedback or execution permissions. A later fetched source cannot overwrite a newly selected report, and a fetch finishing after the modal closes is ignored. Offline snapshots render the exact embedded source without fetching. Template substitutions occur only once in the original HTML so marker-looking evidence text cannot become code.

The same-source bytes are still available through the existing plain-text evidence route. Rendered HTML is generated only from escaped source content and fixed parser markup. This is presentation, not an instruction interpreter or proof of scientific meaning.

## Verification and adoption

Run:

```bash
PYTHONPATH=runtime/src python3.11 -m unittest discover -s runtime/tests -q
node runtime/tests/test_workflow_ui.js runtime/src/autoresearch_runtime/inbox.html
node runtime/tests/test_markdown_ui.js runtime/src/autoresearch_runtime/inbox.html
```

Tests cover normal report formatting, escaped code/raw HTML, unsafe links/images, nested lists/tables, unchanged raw source, Chinese controls, actual live/offline modal, source-switch/close races and offline template-marker/script injection. Install and test a clean wheel before adopting. Keep scientific campaigns on their original runtime; use a separate review-only installation for display changes.

## User Prompt, Verbatim

```text
for the "source report", please show the markdown in rendered format.
```

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 17:55 -0700 | Documented safe local Markdown reading/raw views, supported/inert syntax, immutable evidence/offline/locale behavior and test/adoption boundaries; request preserved verbatim. |
