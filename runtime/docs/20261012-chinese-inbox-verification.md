# Chinese inbox 0.3.1 verification

Status: source, installed-wheel and renderer checks passed. This verifies presentation and review safety, not scientific qualification.

## Checks

- **53 Python tests** passed against source, including all original execution, budget, confirmation, migration, evidence and feedback tests.
- The same **53 tests** passed after wheel installation into a new Python 3.11 environment, using `-I` and no checkout `PYTHONPATH`.
- The actual inline UI renderer passed Node checks in English and Simplified Chinese: glossary/motivation/decision labels, localized project text, English fallback, canonical IDs/evidence/targets, escaping, advisory overview controls, retained comment drafts and locale switching.
- New locale-schema tests reject translations that change source paths, numeric metric values, action eligibility, workflow state, project/effort identity or evidence references. Translations are revision/hash bound; source evidence retains the same bytes.
- The wheel contains `zh-CN.json` and `localization.py`. Missing locale resources are covered by installed-wheel HTML/export tests.

## Reproduction

```bash
PYTHONPATH=runtime/src python3.11 -m unittest discover -s runtime/tests -v
node runtime/tests/test_workflow_ui.js runtime/src/autoresearch_runtime/inbox.html
uv build --wheel --out-dir /tmp/autoresearch-chinese-release runtime
uv venv --python /usr/bin/python3.11 /tmp/autoresearch-chinese-wheel-env
uv pip install --python /tmp/autoresearch-chinese-wheel-env/bin/python \
  /tmp/autoresearch-chinese-release/autoresearch_runtime-0.3.1-py3-none-any.whl
env -u PYTHONPATH /tmp/autoresearch-chinese-wheel-env/bin/python -I \
  -m unittest discover -s runtime/tests -v
```

The renderer test uses a minimal DOM, not a full browser visual/accessibility audit. The runtime validates translation structure and provenance, not the semantic accuracy of arbitrary supplied translations. The project must translate faithfully and preserve every scientific caveat. Raw evidence and user comments are intentionally not automatically translated.

## User Prompt, Verbatim

```text
create a chinese version of the review inbox
```

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 13:01 -0700 | Recorded source/wheel regression success, English/Chinese renderer and display-only safety checks, with explicit limitations and exact user request. |
