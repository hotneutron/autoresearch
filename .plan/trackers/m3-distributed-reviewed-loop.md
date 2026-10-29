# M3 execution tracker

Created: 2026-10-28T20:04:36-07:00
Status: Anonymous local POC verified; real two-host/HTTPS deployment qualification deferred.
Source plan: [P0–P2 implementation](../261028-1937-p0-p2-implementation-plan.md), SHA-256 `80446b0a87e677472d0e67458fa81b6bf7e29d16d4f61d16f2ae3ed01fb2453e`.

## User Prompt, Verbatim

```text
execute the plan with trackers in .plan/trackers/ for each milestone.
```

## Packages

| Package | Implementation | Verification | Required evidence |
|---|---|---|---|
| W07 | implemented | HTTP CPU-agent fixture tests pass | Durable claim/start/heartbeat/receipt outbox, query/cancel, result archive and no blind reschedule; test supervisor is a fixture, not qualified systemd. |
| W13 | implemented | 24-candidate logical fleet and reviewer gate tests pass | Four C_host=2 profiles, C_global=8, k=3; all outcomes retained and no successor without exact global review. |
| W16 | implemented POC | anonymous API/CORS and six JS suites pass | Fleet view plus canonical report/evidence routes, bilingual assurance/drafts and native TLS/proxy configuration; real remote browser/deployment deferred. |

## Environment and outstanding inputs

The active checkout is macOS, Python 3.12 is available, and local Docker/systemd
are unavailable. Linux SSH targets, qualified executor access, HTTPS hostname and
remote artifact archive are explicitly deferred by the user. Portable implementation and CPU
fixture work continue. Simulation is recorded separately from real qualification.

```text
defer that for now.
```

## Evidence and changes

- Implementation and verification snapshot: 2026-10-28T20:40:08-07:00.
- Files/evidence: control_plane.py, host_agent.py, hosting.py, dist_cli.py and fleet.html; test_hosting.py, test_search.py and test_fleet_ui.js. The fleet is simulated on one physical machine.
- Portable installed-wheel results: [verification](portable-verification.json); real infrastructure explicitly deferred.

- Tracker initialized before code changes. Existing plan edits are retained.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-28T20:04:36-07:00 | Created milestone tracker with exact execution request and package gates. |
| r2 | 2026-10-28T20:11:40-07:00 | Recorded explicit deferral of real-host/deployment qualification; continue local implementation and conformance. |
| r3 | 2026-10-28T20:40:08-07:00 | Recorded local implementation, passing contract/fixture evidence and explicit deferred qualification; retained the original requests and package boundaries. |
