# Report execution and overall research are different scopes

## User prompt, verbatim

```text
why the status for finished experiments are still "当前状态： 已有活动正在执行" for review dashboard?
```

## Why the old display was misleading

The project host provides one `goal_steering` snapshot for the overall research goal. Its `active_campaign` state means an admitted campaign exists somewhere under that goal. The old frontend rendered this same state inside every selected report, making finished studies look active whenever a successor ran.

This is a presentation-scope bug, not a scientific result, restarted experiment or charge. An overall goal can still have running work while a particular experiment is finished and unsupported.

## Presentation contract

- Overall read-only live execution and goal steering have independent global panels explicitly labeled **not this report**. They name actual active campaign identities.
- A selected study gets **This report’s experiment status**. Exactly one ledger admission must match its full `contract_id` or `branch`. No substring, title, success-looking prose or evidence-validity guess binds execution.
- A closed admission displays **Finished execution**. Its exact checkpoint ID can be shown; the scientific outcome appears only if that checkpoint record also binds to the same campaign. Finished does not mean supported or promoted.
- An active admission displays **Running execution** only when the live observation names that exact campaign and a running unit has a verified live process. Otherwise it displays **Admitted · running not verified**. Offline snapshots never assert current liveness.
- Missing or ambiguous bindings display **Execution state not linked**, not a different campaign’s global running state. Hosts should provide exact bindings if they want a historical report to show a verified lifecycle.
- Global heartbeats and unrelated successor changes do not rebuild a selected report or erase its feedback draft. Report-state changes do rebuild with the draft preserved under that report revision.
- These are presentation-only fields. Packet bodies, hashes, outcomes, named approvals, pauses, feedback and execution gates are unchanged.

## Review-only deployment

The Accorde host retains its original0.5.7reviewwheel and scientific0.5.4installation. A timestamped, SHA-256-pinned presentation overlay replaces only `inbox.html` and `zh-CN.json` in the separate review environment. The stable server reads these assets per page request; it does not need a restart or Python-module hot-reload. The prior lock/assets are archived, package hashes and installed RECORD reflect the overlay, and no immutable packet is overwritten.

An already-open browser must reload once to load changed JavaScript; five-second data polling alone cannot update an older script. After that, normal polling keeps both global and selected-report status fresh.

## Tests

`tests/test_report_execution_ui.js` exercises the actual shared template: a finished unsupported experiment beside a live successor, an unlinked report, exact/ambiguous contract binding, a dead or unverified worker, offline snapshots, English/Chinese scope labels, and draft preservation through lifecycle changes. Existing workflow/live-refresh/Markdown suites must still pass. Python tests are run from an isolated installed wheel so scientific worker children do not depend on development `PYTHONPATH`.

## Revision History

|Revision|Timestamp|Change|
|---|---|---|
|r1|2026-10-20T21:38:00+00:00|Recorded exact userprompt and generic scope-correct execution display, exact-binding/unknown/offline policy and no-restart review-only asset overlay.|
