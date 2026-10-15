# Workflow overview 0.3.0 verification

Status: source and installed-wheel checks pass. This is generic runtime validation, not qualification of any project's experiments.

## Verified behavior

- **49 Python tests** pass against the source package, including existing queue, receipt, source identity, budgets, confirmation, migration and review tests.
- The same **49 tests pass from a wheel installed in a new Python 3.11 environment**, with the checkout removed from `PYTHONPATH` and isolated-mode unittest invocation.
- A Node test executes the actual inline UI renderer with a minimal DOM: Start here selection/order, plain-language context, glossary, motivation/approach/alternatives/outcome/rationale/uncertainty/next step, stale study links, advisory-only overview controls, search/filter, escaping, and ordinary packet compatibility.
- HTTP tests reject pause/approval on an overview, preserve safe-checkpoint comments, and reject stale feedback while retaining prior immutable evidence.
- The image-upload example has no H3/ML/GPU dependencies and is labeled illustrative, not measured scientific evidence.
- Overview publication produces no jobs, permits or experiment budget changes. Same-project study-target ID/hash and applied-feedback disposition checks are mandatory.

## Reproduction

```bash
PYTHONPATH=runtime/src python3.11 -m unittest discover -s runtime/tests -v
node runtime/tests/test_workflow_ui.js runtime/src/autoresearch_runtime/inbox.html
uv build --wheel --out-dir /tmp/autoresearch-workflow-release runtime
uv venv --python /usr/bin/python3.11 /tmp/autoresearch-workflow-wheel-env
uv pip install --python /tmp/autoresearch-workflow-wheel-env/bin/python \
  /tmp/autoresearch-workflow-release/autoresearch_runtime-0.3.0-py3-none-any.whl
env -u PYTHONPATH /tmp/autoresearch-workflow-wheel-env/bin/python -I \
  -m unittest discover -s runtime/tests -v
```

The UI test is renderer-level, not a browser visual/accessibility audit. The runtime enforces evidence provenance and schema, not whether arbitrary project prose is scientifically correct or genuinely written in plain language. Projects must maintain their own truthful summaries and publish them at safe checkpoints.

## Adoption boundary

The source change is developed separately on `feature/workflow-review-overview` in the autoresearch fork. A wheel/install is not automatically adopted by Accorde's scientific campaign runtime. Its private 0.2.0 lock, installed package payload and completed freezes remain untouched. A new review-only environment may serve the compatible store schema; new experiments need their own exact runtime pin and frozen contract. No remote push is authorized by the local commit instruction.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 12:10 -0700 | Recorded source/installed-wheel regression success and renderer/HTTP boundary coverage, with explicit scientific and browser-test limitations. |
