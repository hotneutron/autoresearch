# P0–P2 execution trackers

Created: 2026-10-28T20:40:08-07:00
Status: local POC implementation available; real infrastructure qualification is deferred.

## User Prompt, Verbatim

```text
execute the plan with trackers in .plan/trackers/ for each milestone.
```

```text
defer that for now.
```

## Milestones

- [M0](m0-contracts-and-correctness.md): Local implementation verified; Linux baseline qualification deferred.
- [M1](m1-qualified-local-execution.md): Backend interfaces implemented; actual source-executor qualification deferred.
- [M2](m2-global-and-scientific-contracts.md): Local coordinator/scientific contract implementation verified; real subject qualification deferred.
- [M3](m3-distributed-reviewed-loop.md): Anonymous local POC verified; real two-host/HTTPS deployment qualification deferred.
- [M4](m4-learning-and-release.md): Local learning/migration helpers verified; full deployment/recovery qualification deferred.

## Verification boundary

The portable runner excludes the three Linux-dependent runtime/goal/confirmation
suites on macOS. Real systemd/container/GPU, separate source hosts, remote archive,
and deployed HTTPS checks are deferred. Local tests and fixture passes do not
close those qualification gates. Existing plan POC edits remain intact and no
remote deployment or scientific experiment was launched.

See [distributed POC usage](../../runtime/docs/distributed-poc.md) for the installed
CLI, code ownership and current boundary. Source changes are recorded on dist-exec; infrastructure qualification remains deferred.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-28T20:40:08-07:00 | Added the milestone index and separated local evidence from explicitly deferred qualification. |
| r2 | 2026-10-28T20:45:06-07:00 | Recorded implementation commit preparation and retained the explicit qualification boundary. |
