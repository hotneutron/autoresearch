# Live review freshness and immutable author snapshots

## User prompt, verbatim

```text
looks like the review dashboard is no longer updating
```

## Two kinds of freshness

A five-second HTTP poll does not make an authored scientific summary live. Model fits can run for many minutes without producing a supported intermediate result. A historical presentation store may also be different from the active scientific campaign store.

Runtime0.5.7 adds `LiveInbox(inbox, observe)`: a trusted host callback supplies a **read-only execution observation** on every API snapshot. The UI shows observation time, verified worker liveness, elapsed/ceiling, durable progress when available, and latest validated checkpoints separately from immutable published packets. Unknown progress stays unknown; liveness is not scientific support, approval, calibration or permission to deploy. The wrapper never dispatches a Controller, consumes feedback, changes admission or republishes reports. Callback errors keep the inbox available and explicitly show that the observation is unavailable.

```python
from autoresearch_runtime.live_review import LiveInbox
from autoresearch_runtime.review import server

live = LiveInbox(inbox, observe=lambda: {
    "observed_at": "2026-10-20T18:45:00Z",
    "active_campaign": "example-campaign",
    "summary": "One complete model unit is running; final outcome pending.",
    "progress_note": "This model emits results only after all fits finish.",
    "units": [{
        "id": "fit", "title": "Frozen model comparison", "state": "running",
        "process": {"live": True, "pid": 123},
        "elapsed_seconds": 300, "ceiling_seconds": 1200,
        "progress": None,
    }],
    "checkpoints": [],
    "translations": {"zh-CN": {"summary": "模型完整单元正在运行，最终结果待定。"}},
})
server(live, 8765).serve_forever()
```

The project must validate trusted artifact paths, exact process start identities, state/ledger consistency and result provenance. Do not infer progress from PID existence alone or silently invent successful fits. A project-owned review-only coordinator can publish new, hash-bound bilingual narrative revisions at **meaningful stage/checkpoint transitions**; it should not publish a new evidence revision merely because elapsed seconds changed. That publication policy is separate from runtime execution and scientific authority.

## Navigation and feedback safety

When polling supersedes the selected packet, the UI follows the latest revision of the **same branch**, not an unrelated waiting report. The branch survives skipped revisions; old drafts remain keyed to their old immutable packet IDs and are not carried into new approval or submission requests. The UI notifies the reader and requires a fresh review of the new revision. Source evidence remains an immutable rendered/raw reading view.

Manual refresh and visible last-success age make network failures distinguishable from an unchanged scientific checkpoint. Live status updates independently from the report/feedback form so elapsed-time updates do not reset a draft or scroll the current reading view.

## Revision History

|Revision|Timestamp|Change|
|---|---|---|
|r1|2026-10-20|Documented generic read-only live observation, bilingual display, same-branch revision following, meaningful-transition publication and scientific/feedback boundaries; exact prompt preserved.|
