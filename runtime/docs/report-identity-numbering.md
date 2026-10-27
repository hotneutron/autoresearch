# Effort indices, report revisions and experiment IDs

## User prompts, verbatim

```text
Why the latest experiment I saw on the 'review bashboard' is  unified-h3-continuation-v1?
```

```text
and E59, not r125?
```

## Three distinct identity levels

- **E59** is the display index of a workflow effort. Stable canonical effort IDs keep related-effort links consistent as reports change. An effort can summarize several bounded experiments; an E-index is not an experiment count.
- **Overview r125** is revision125 of the overview report series. A linked study report can have its own revision42. Neither revision is an experiment number, and the two series do not share revision counters.
- **Experiment ID** is the actual admitted scientific campaign identity in a trusted live observation. A generic continuation report branch such as `unified-h3-continuation-v1` can summarize an actual campaign named `unified-h3-scoped-access-model-cost-pilot-v1`. The branch is a report series, not itself proof of a current execution.

In the Accorde case, the transition publisher continually updated a single E59 umbrella effort and linked it to the latest immutable study-series revision. The dashboard was fresh but the umbrella grouping and buried report revision were confusing. This clarification does not create fabricated historical efforts, rename campaign IDs or interpret the report as a new scientific execution.

## Frontend presentation

The inbox now shows **Overview rN** or **Study report rN** prominently on list cards and selected reports. Report ID and **Report series (not experiment ID)** have separate labels. Overview history explains E-index versus r-version and lists each effort's exact linked packet ID. The global live panel shows **Running experiment ID** and a link to the **Latest published overview**, only clickable when that packet is in the current snapshot. Unrelated/historical report details never inherit the running campaign's status.

These presentation changes retain canonical packet/effort identities, evidence and feedback hashes, approval boundaries and immutable historical reports. Existing draft-preservation, offline status and same-branch refresh rules remain binding. A browser already holding an old script requires a one-time reload after deployment; save any unsent feedback first.

## Verification

The actual-template lifecycle test covers both a total-overviewr125 and a studyreportr1, separate series labels, exact latestoverviewlink, Chinese numbering explanation, finished-versus-running scope and draft safety. Existing workflow, Markdown and live-refresh suites must still pass. Deployment is an explicitly hash-pinned HTML/localization review-only overlay; Python execution/admission code, scientific pins and stable listener are unchanged.

## Revision History

|Revision|Timestamp|Change|
|---|---|---|
|r1|2026-10-20T23:28:00+00:00|Recorded exact prompts and generic effort/report/campaign identity distinctions; added prominent bilingual labels/currentoverviewlink while retaining stable numbering and scientific permissions.|
