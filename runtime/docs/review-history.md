# Complete report and experiment history

User prompt, verbatim:

```text
I need to monitor the history and progress of the expeirments in the review dashbaord. But now I can see is r48 snapshot. I have no visibility of what happened before. and overview tab doesn't show r1-r131 either. The current dashboard is un-usable.
```

Runtime `0.5.8` makes the stored history navigable without changing it.

## Report revisions

The Reports and revisions view catalogs every branch and every immutable packet
revision. It loads at most 50 compact catalog rows at a time and retrieves the
full packet only when selected. First, older, newer, and latest controls navigate
the exact series. A historical packet remains pinned while the separate live
observation refreshes, and its feedback/actions are disabled. Returning to the
latest packet restores the current controls without discarding drafts kept for
that latest packet.

The loopback APIs are:

```text
GET /api/history?branch=<branch>&offset=0&limit=50
GET /api/report/<packet-id>
```

## Experiments

The Experiment history and progress view is separate because a report revision,
an overview effort index, and an actual bounded experiment are different
identities. A trusted project provider may expose one read-only row per ledger
admission, including invalid executions and registered pre-ledger campaigns.
Details bind the exact contract, checkpoint, charge, evidence hashes, result,
recovery, and later reorientation. Process state is verified from recorded host,
boot ID, PID, and start ticks; an active ledger row alone is not called running.
Intermediate model progress remains unknown unless the experiment emitted a
durable record.

The optional provider APIs are:

```text
GET /api/experiments?offset=0&limit=30&search=<text>&status=<filter>
GET /api/experiment/<campaign-id>
GET /experiment-evidence/<campaign-id>/<index>
```

These endpoints are read-only. They do not instantiate a controller, acquire a
scientific lease, approve work, amend evidence, or infer scientific promotion.

## Commit verification

Commit request, verbatim:

```text
commit the latest changes to autoresearch
```

- Python regression suite: 96 tests passed from the development environment.
- Built runtime 0.5.8 as a wheel and verified it contains the history module,
  inbox template and Chinese translations. All 96 Python tests passed again
  from a clean wheel installation with isolated mode and no `PYTHONPATH`.
- All five JavaScript suites passed: history navigation, live refresh,
  report/execution scope, workflow rendering and Markdown evidence.
- `git diff --check` passed. These checks cover the generic history interface;
  project-specific experiment data providers retain their own validation.

## Revision History

- 2026-10-21T03:15:00Z: Added paginated immutable report navigation and a
  complete read-only experiment chronology under the exact user request above.
- 2026-10-27T16:29:47-07:00: Preserved the commit request and recorded Python,
  installed-wheel and JavaScript verification for the pending history changes.
