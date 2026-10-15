# Outer-loop reorientation verification

## User Prompts, Verbatim

```text
when stucked like this, the outer loop should brainstorm on "fundamentally different reliable label source or measurement/model objective", right?
```

```text
update the autoresearch framework.
```

## Verified behavior

- A terminal campaign checkpoint exposes `reorientation_required` and blocks a
  successor proposal.
- `goal reorient` accepts only a current goal/context/latest-checkpoint binding.
-1–10 candidates require evidence, explicit novelty/disposition and complete
  campaign+downstream budgets.
- A viable inventory selects exactly one candidate within current claim/scope and
  aggregate remainder.
- The selected proposal ID, claim, scope, kind, decision, endpoint relevance and
  complete budget bind the next proposal.
- A rejected/blocked-only inventory exposes `no_viable_candidate` and prevents
  successor proposals.
- A later consecutive goal revision is itself a material reorientation.
- Active campaigns, stale contexts, evidence drift, out-of-scope candidates and
  over-budget viable routes fail closed.
- The English/Chinese review UI escapes candidate text and shows the public
  unresolved claim, exhausted path, dispositions, selection and next checkpoint.
- The UI explicitly says these are public decision records, not private
  chain-of-thought; no new execution action is created.

## Test evidence

- Targeted goal/CLI tests:20 passed.
- Full source install:82 Python tests passed.
- Clean0.5.0 wheel install:82 Python tests passed.
- Source and clean-wheel workflow/goal bilingual UI checks passed.
- Source and clean-wheel safe Markdown live/raw/Chinese/offline checks passed.
- Wheel:`autoresearch_runtime-0.5.0-py3-none-any.whl`.
- Wheel SHA-256:`6add2b37c45deaddb8f6839ab26b14dd70728985c8b7497284c5ff124991d792`.

The tests are procedural runtime verification. They do not prove that a
project-authored candidate is scientifically sound or independently reviewed.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-13 00:00 -0700 | Recorded source/wheel/CLI/UI verification, release identity and explicit limitations for runtime0.5.0. |
