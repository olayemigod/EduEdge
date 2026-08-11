# EduEdge Historical PR Recovery Ledger — August 2026

## Purpose

This ledger prevents useful EduEdge academic, profile and CBT work from being lost while historical stacked PRs are retired before combined QA.

The canonical current QA line is PR #19 / `agent/eduedge-full-academic-cbt-integration`.

Historical branches are classified as:

- **Functionally superseded** — the current PR #19 contains a newer implementation of the same capability and safety intent, even where Git ancestry is divergent.
- **Recovered** — a specific missing hardening item was ported into PR #19 during this cleanup.
- **Active recovery source** — the historical branch still contains substantive capabilities that are not yet fully represented in PR #19 and therefore must remain open until reconciled.

## PR #5 — Offline-Resilient CBT foundation

**Disposition: Functionally superseded by PR #19.**

The current integration branch now contains the richer end-to-end CBT runtime that the original foundation anticipated:

- server-timed candidate attempts;
- immutable question snapshots and separate protected scoring keys;
- one-active-attempt enforcement and maximum-attempt limits;
- launch-token checks;
- Pending Sync lifecycle;
- browser IndexedDB answer, batch and metadata storage;
- client revisions and pending-answer detection;
- resumable active sync batches;
- offline reconciliation, invigilation, review, scoring, marking and result readiness;
- result synchronization into school assessment workflows.

The historical branch should not be merged because doing so would replace later attempt, security and browser-runtime work with an older V0.8 foundation.

## PR #6 — Governed CBT V0.8A and public-exam access

**Disposition: Functionally superseded by PR #19.**

The current branch preserves and extends the important governance model:

- `cbt_public_exam` remains the central feature key;
- independent `catalog`, `assign`, `host`, `launch`, `results` and `author` capabilities remain enforced;
- public-exam authoring remains role + capability governed and fails closed away from the authority site;
- school CBT remains distinct from centrally governed public exams;
- current question/template/schedule lifecycle and permissions are stricter than the historical foundation.

The branch's final unique manual-entry behavior is also already present in current `eduedge_question_batch.bundle.js`: a newly added manual question is moved to the top and focused through Vue `$nextTick`, without MutationObserver/remount hacks.

## PR #15 — CBT Schedule Operations EdgeSuite UI

**Disposition: Functionally superseded by PR #19.**

Although the historical branch has divergent commits, the current integration branch contains the evolved schedule workbench and governance architecture:

- `eduedge/api/cbt_schedule_operations_hardened.py`;
- `eduedge/cbt/schedule_governance.py` with serialized schedule mutations;
- Branch/public-exam capability enforcement;
- schedule, candidate, intervention and lifecycle records;
- confirmed-candidate mutation protection;
- candidate uniqueness and lifecycle controls;
- current EdgeSuite CBT Schedules page/bundle and permissions.

Do not replay the older schedule branch onto PR #19.

## PR #17 — Schedule Operations integration branch

**Disposition: Functionally superseded by PR #19.**

PR #17 was an integration-only bridge for the older PR #15/#16 QA line. The current #19 branch now carries a later academic + CBT integration architecture. PR #17 remains useful as review history but should not become a second release line.

## PR #16 — Profiles and audited native academic hierarchy

**Disposition: ACTIVE RECOVERY SOURCE — DO NOT CLOSE YET.**

PR #16 still contains substantive shared-site academic identity and progression work that is not fully represented in PR #19. It remains protected until those capabilities are reconciled or explicitly rejected after review.

### Recovered during cleanup

Two release blockers from #16 were confirmed missing from #19 and have now been restored on the canonical branch:

1. **Genuine profile-image byte validation**
   - profile uploads now verify JPEG, PNG and WebP signatures in addition to extension/MIME/size;
   - renamed non-image files are rejected;
   - the recovery is self-contained and does not introduce the undeclared `filetype` dependency used by the historical branch.
   - commits: `d8e5ea9aea296d5cd5f9ed30c8b41d9298f645bb`, `5353b6e7973f578fca9a006878a505633dfe02ef`.

2. **Exact Course Schedule resolution for direct attendance**
   - direct attendance without a selected Course Schedule now auto-binds when exactly one schedule exists for the Student Group/date;
   - multiple matching schedules fail closed and require the exact session;
   - unscheduled attendance remains possible only where no matching schedule exists;
   - newer Branch, calendar, hierarchy, permission and duplicate-locking protections remain authoritative.
   - commits: `79e8b7130ec929e8cf36583949f2a3cadd77a644`, `39bf0d4d35c47e2954d85eb59f132cdb86bb15f5`.

### Still requiring reconciliation

The following #16 areas must not disappear during cleanup:

- institution-safe friendly native identities such as `eduedge_display_name` for Department, Program, Course, Student Group and Student Batch Name;
- deterministic technical names when multiple Institutions legitimately use the same friendly labels;
- friendly-name display helpers/forms without rewriting existing native identities;
- academic progression services, fields, workflow and terminology;
- enrollment progression and progression audit/status logging;
- tertiary-level migration/classification behavior;
- any additional native-hierarchy release blockers documented in PR #16 that are not already covered by current PR #19's newer institution-root and collision-safe migration logic.

The current branch already has stronger institution-owned Department roots and collision-safe legacy Section migration, so reconciliation must compare behavior—not copy old files wholesale.

## Canonical QA rule

Do not treat historical implementation as completed merely because its PR existed. Browser/database QA must run against the current PR #19 head after the active PR #16 recovery work is reconciled.
