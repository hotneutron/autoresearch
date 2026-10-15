# Justifications for AGENTS.md rules

One entry per rule in `AGENTS.md`, with the date it was introduced and why.
This file also serves as the revision history for `AGENTS.md`.

## Rule: Amendments to an existing artifact must add/update a timestamped `## Revision History`; agent-facing artifacts are exempted.

- Added: 2026-07-29
- Why: Artifacts (design docs, plans, reports) evolve across many agent runs;
  a timestamped revision history makes changes auditable and lets a later reader
  reconstruct what changed and when without diffing git.
- Exemption (added 2026-08-01): agent-facing artifacts (e.g. `AGENTS.md`,
  files under `.agent/`) are exempted to avoid recursion and boilerplate —
  their history lives here instead.

## Rule: No `Co-Authored-By` trailer in commits.

- Added: 2026-07-29
- Why: Commit authorship should reflect the human author only; automated
  co-author trailers add noise and misattribute ownership in this repo's history.

## Rule: Every rule here must have a justification entry in `.agent/rules-rationale.md` (which doubles as this file's revision history).

- Added: 2026-08-01
- Why: Rules without recorded rationale become cargo-culted or silently dropped.
  Requiring a justification keeps `AGENTS.md` terse (rules only) while preserving
  the reasoning, and gives `AGENTS.md` an audit trail without violating its own
  revision-history rule.

## Rule: Persist user prompts verbatim in artifacts.

- Added: 2026-08-03
- Why: Verbatim prompts make artifact intent and provenance auditable, easier to
  understand, and easier to debug. They also encourage concrete, thoughtful
  prompting and support sharing the user's thought process.
