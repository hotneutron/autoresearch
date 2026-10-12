# Goal steering 0.4.0 verification

Timestamp: 2026-10-12 16:40 -0700
Status: source and isolated-wheel verification passed; local commit/adoption follow separately.

## User Prompt, Verbatim

```text
impl the generic steering mechanism, then restart the campaign.
```

## Actual checks

- Source Python3.11 suite: **69 tests passed**, including16 new goal-ledger/Controller tests. Existing53 runtime, confirmation, review and locale tests remain passing.
- Clean installed wheel suite: **the same69 tests passed** under `/home/cliu/wk/accorde/local_artifacts/autoresearch/runtime-envs/v0.4.0/bin/python`, with no source-path override.
- Actual source and installed English/Chinese inline renderer checks passed, including escaped goal text, unchanged advisory overview controls and aggregate goal-state panel.
- `git diff --check` passed.
- Release wheel: `autoresearch_runtime-0.4.0-py3-none-any.whl`, SHA-256 `e7112b4be2dbca650a4694594836fb3551e8075be7f11d86f99ab4b60141b20f`.
- New tests cover immutable goals/no historical reset; missing/changed/stale assessment denial; explicit STOP/RESUME; outcome/scope/finite-route budgets; exact contract/evidence binding; admitted complete-design continuation after intervention; full/failure checkpoints and charges; concurrent admission; reservation persistence; no replacement/re-admission; independent scientific/approval gates; CLI and read-only review display.

No live H3 experiment used this version during software tests. Fixture projects are temporary image-upload examples; their outcomes are software behavior, not H3 modeling evidence. No independent reviewer, browser visual/accessibility audit or remote push is claimed.

## Build notes and limits

The review0.3.1 interpreter has no pip; build used available system Python3.11 `pip wheel --no-deps --no-build-isolation`, then installed into a fresh0.4.0 venv. An initial compatibility run exposed a missed controller initialization/parser insertion and a locale comma; fixed before the69-test release. No failed software test was an experiment unit or altered H3 accounting.

Full scientific relevance remains the project agent's responsibility: schema completeness cannot prove expected decision value. Opt-in host policy must bind new contracts to the persistent ledger; legacy campaigns remain on old pins. Same-user source/evidence hashes and imported prior accounting are procedural provenance, not protection from adversarial code. Reservations require explicit pinned reconciliation/checkpoints; no failed-unit retries or automatic release.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-12 16:40 -0700 | Recorded actual source/clean-wheel69-test and both-locale renderer results, release hash, resolved build/test issues and scientific/procedural limits; exact request preserved. |
