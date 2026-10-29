# Distributed POC runtime

The optional runtime now includes an opt-in coordinator, anonymous review API,
source-host agent and independent systemd supervision interface. Legacy `autoresearch`
commands retain their protocol/store versions. Distributed contracts and coordinator
stores use version 1. Run new distributed campaigns in a separate environment/store.

## User Prompt, Verbatim

```text
execute the plan with trackers in .plan/trackers/ for each milestone.
```

## Local commands

Install the built wheel in an isolated Python 3.11+ environment. The runtime has no
Torch, model-provider or statistics-library dependency.

```bash
python -m pip install ./runtime
autoresearch-dist --store /durable/research preflight
autoresearch-dist --store /durable/research --archive /durable/artifacts serve --port 8766
autoresearch-dist --store /durable/research call projects/register project.json
autoresearch-dist --store /durable/research call rounds/admit round.json
autoresearch-dist --store /durable/research status
autoresearch-dist --store /durable/research backup /durable/recovery-001
```

Local HTTP is for conformance or a backend behind the HTTPS proxy. A source agent
requires verified HTTPS and no client authentication in `anonymous_poc` mode. Native
TLS can use `serve --bind 0.0.0.0 --tls-cert cert.pem --tls-key key.pem`; configure the
certificate and authority to match the deployed URL. Deployment templates are in
`runtime/deploy/` relative to the repository root.

## Ownership and review

Framework and subject are independent Git repositories. Unit contracts contain both
full commit identities, benchmark/evaluator/environment hashes, exact logical argv,
input hashes, metric criteria, seed/replicate, timeout, profile and integer costs.
`framework`, `subject`, `input`, `evaluator` and `output` are explicitly bound roots.
A source host does not mount the coordinator's SQLite file.

Configure a host agent with `coordinator_url`, `round_id`, `host` (id, boot_id,
capacity and profiles), `roots`, and optional `systemd_user`. It uses the pinned
systemd supervisor and persists claim/start/receipt requests before network calls.
The `local-container` profile additionally freezes `executor` settings (image digest,
uid/gid, memory_bytes, cpu_millis and pids), with read-only input/source mounts.

The coordinator stores one global round and transactional ownership/budget/exposure
state in SQLite WAL with FULL durability. Duplicate request bodies return their
committed result. Changed bodies conflict. Uncertain jobs retain capacity and budget;
a heartbeat lapse never establishes that a remote child stopped.

Use `units/qualify`, `rounds/seal`, `review`, and `review/apply` to submit complete
qualification, seal the inventory, record the exact successor decision, and apply it
at the global boundary. The next round's hash must match that applied review.
Reviewer labels are self-reported and unverified during POC. A separate actor adapter
and authenticated profile require future configuration; the API never claims they
are active now. Final promotion separately requires the global one-time exposure
and aggregate-only confirmation records.

## Current verification boundary

Portable contract, metric, SQLite race/idempotence, round-review, exposure, artifact
restore, subject snapshot/pool/promotion, context/delta/stall/hook and anonymous HTTP
CPU-fixture tests run locally. The 24-candidate test is a logical fleet simulation.
The HTTP fixture supervisor is synchronous CPU conformance, not independent systemd
supervision. No simulated pass qualifies a real source executor or distributed host.

Real Linux/systemd/container/GPU and two-host conformance, remote archive deployment,
and the HTTPS deployment are explicitly deferred. Backend availability is reported
separately from qualification. Lifecycle/resource enforcement and artifact migration
must be qualified with the planned failure injection before enabling real research.
The initial generated CPU subject is a contract fixture; scientific metric adequacy,
comparison assumptions, input access and final population identity belong to a real
subject adapter and reviewer.

Legacy export preserves packet bytes/hashes and marks accounting/exposure as not yet
imported. Do not initialize a fresh global budget as a continuation of an existing
goal until its historical charges, pauses, active reservations and exposure have been
reconciled. Recovery catalogs require the referenced archive in addition to a SQLite
backup; a database file alone does not contain all experiment bytes.

## Trackers

The repository's `.plan/trackers/` files contain package status and evidence for
M0 through M4. Pending/deferred conformance remains visible alongside implemented
interfaces and portable tests.

## Revision History

| Revision | Timestamp | Change |
|---|---|---|
| r1 | 2026-10-28 | Documented the opt-in distributed POC, ownership, commands and explicitly deferred qualification boundary. |
