# EduEdge CBT Schedule Operations — EdgeSuite UI and Governance

## Goal

Provide a first-class EdgeSuite workbench for examination Schedules, Candidate Assignments and operational interventions without weakening EduEdge Branch isolation, approved-template governance, candidate identity, timing controls or audit truth.

## EdgeSuite route

`/app/eduedge-cbt-schedules`

The workbench is available from the EduEdge sidebar, Product Menu and Workspace.

## Implemented operational areas

### CBT Schedules

- Branch, examination-scope, status and text filters.
- Create and edit Draft/Ready Schedules.
- Approved Fixed Question Set selection only.
- Actual Schedule Student Group/Class and academic context.
- Active Centre and Branch-aware Primary Invigilator selection.
- Template policy snapshot visibility.
- Draft → Ready → Active → Suspended/Completed/Cancelled lifecycle.
- Controlled reasons for exceptional lifecycle transitions.
- Append-only lifecycle history.
- Advanced native record access for technical inspection.

### Candidate Assignments

- Single Student or public-candidate assignment.
- Schedule Class bulk assignment.
- Branch/Class eligibility validation.
- Database-backed duplicate prevention.
- Eligibility, check-in, release, completion, withdrawal and disqualification.
- Check-in opening and closing boundaries.
- Late-entry grace enforcement.
- Candidate identity and access-window locking after eligibility.
- Append-only lifecycle evidence.

### Interventions

- Append-only Intervention History.
- Server-derived outcomes and audit values.
- Time Extension is currently the only immediately executable intervention.
- Time Extension updates Candidate access atomically, respects cumulative maximum policy and serialises concurrent requests.
- Device Change, Force Submission, Attempt Unlock/Suspension, Reconnection Approval, Manual Sync Resolution and Candidate Reassignment are recorded as **Recorded for Review** until the attempt engine supports the operational action.

## Audit hardening completed before browser QA

A second code and workflow audit was performed after the first local migration run. The audit found and corrected loopholes that static page-presence tests did not cover.

### Controlled entry points

- Direct native or generic API changes to Schedule status are rejected.
- Direct native or generic API changes to Candidate status are rejected.
- All public calls to the internal hardened Schedule Operations module are rerouted through the controlled wrapper.
- Controller-level CoreEdge/EduEdge access checks still protect native Draft record creation and editing.
- Schedule and Candidate imports are disabled because governed state cannot be safely reconstructed through bulk import.
- Status, lifecycle reason and Candidate extra-time fields are read-only in native forms.

### Audit-record preservation

- A Schedule can be deleted only while Draft and only when it has no Candidate, Intervention or Lifecycle evidence.
- A Candidate Assignment can be deleted only while Draft, before Schedule activation, and only when it has no Intervention or Lifecycle evidence.
- Withdrawn, Cancelled, Completed and other audited records are retained rather than deleted.
- Lifecycle Logs and Intervention Logs remain append-only.

### Cancellation and completion truth

- Cancelling an unstarted Schedule automatically withdraws Draft and Eligible candidates using the cancellation reason.
- Cancellation is rejected once any candidate has Checked In, been Released or Completed the sitting.
- Completing a Schedule requires every Candidate Assignment to be terminal: Completed, Withdrawn or Disqualified.
- At least one candidate must be Completed before the Schedule can be marked Completed.
- The EdgeSuite UI hides Cancel once a sitting has started, while the backend independently enforces the rule.

### Reservation and concurrency safety

- Centre, Primary Invigilator and candidate collisions are rejected when a Schedule becomes Ready, rather than being discovered only at activation.
- Confirmed candidates cannot occupy overlapping Ready, Active or Suspended sittings.
- Ready/Active Schedule reservations and Candidate eligibility reservations use one shared database row lock that remains held until Frappe commits the request.
- A filesystem lock is retained for process-level coordination, but database locking is the transaction-authoritative control.
- Schedule-specific mutations also lock the Schedule row.
- Class candidate collision checks are batched rather than running one query per Student.

### Smart academic context

- Programme and Assessment Group options are filtered by the selected Branch Institution before pagination.
- The backend independently rejects Programme or Assessment Group values outside the Schedule Institution context.
- Invigilator search requires Schedule-management permission.
- School Invigilator search requires a selected Branch and returns only users authorised for that Branch.

### Extra-time truth

- Candidate creation no longer displays or accepts direct approved extra time.
- Approved extra time can change only through an Applied Time Extension intervention.
- Time Extension cannot reopen a candidate whose access window has already closed.
- Applied Time Extension does not create a false pending-attempt-review flag; unsupported attempt actions remain Recorded for Review.

## Hardened business rules

### Branch and public-examination isolation

Public-examination capability does not widen access to School Examination records. Query conditions combine:

- school records in permitted Branches; and
- Branch-null public records allowed by the exact public capability.

Schedule lifecycle evidence requires public authoring capability. Candidate lifecycle evidence requires public assignment capability.

### Schedule integrity

- Policy Blueprint scheduling is blocked until rule-based question generation and an immutable generated-question snapshot are implemented.
- A Retired Template may be retained only by a Schedule already linked to that exact version.
- Schedule Class/academic context is stored on the Schedule; Candidate Assignment no longer consumes a live Template default.
- Subject/Course, Programme and Assessment Group ownership must match the Schedule Institution context.
- Invigilator must hold an authorised role and have access to the Schedule Branch.
- Template, Branch, Class, Subject, Centre, timing and policy fields lock once confirmed candidates exist.
- Activated/Suspended/Completed/Cancelled Schedule operational fields are immutable.

### Activation readiness

Activation and resume validate:

- Schedule has not ended;
- at least one non-terminal candidate exists;
- initial activation has no Draft candidates;
- initial candidates are Eligible or Checked In;
- Centre capacity is positive and not exceeded;
- no overlapping Centre booking;
- no overlapping Primary Invigilator booking;
- no overlapping Student or Public Candidate Reference booking.

### Candidate entry and release

- Check-in cannot occur before `check_in_opens_at` or after the late-entry boundary.
- Manual Release is available only for `Invigilator Releases Candidates`.
- Manual Release cannot occur before Scheduled Start or after Scheduled End.
- Candidate/automatic start modes remain attempt-engine actions and are not falsely simulated by the workbench.

### Audit integrity

- Schedule and Candidate lifecycle reasons are read-only outside controlled status actions.
- Lifecycle Logs are server-created only; users have read/report access but no create, edit or delete access.
- Intervention outcome, previous value, new value and attempt reference are server-derived.
- No answer, score, marking-guide, submitted academic or accounting record is mutated.

### Concurrency and idempotency

- Unique database indexes enforce Schedule + Student and Schedule + Public Candidate Reference.
- Migration checks existing duplicates before creating indexes.
- Class bulk assignment retries database uniqueness races once and recalculates existing assignments.
- Time Extensions lock the Candidate Assignment row before calculating cumulative extra time.
- Reservation checks are serialised through transaction-persistent governance locking.

## Migration

`bench --site <site> migrate` is required because this change adds or changes:

- EduEdge CBT Lifecycle Log DocType;
- Schedule Class/academic and lifecycle fields;
- Candidate lifecycle field;
- Schedule/Candidate governed-field metadata;
- composite Candidate Assignment unique indexes.

The uniqueness patch is idempotent and stops with a clear validation error when pre-existing duplicates must be resolved. Do not apply raw `ALTER TABLE` commands.

The Profile objects from the separate profile branch are not part of PR #15. Do not alternate one migrated QA site between sibling feature branches because Frappe orphan cleanup will remove objects absent from the checked-out branch.

## Out of scope

- Policy Blueprint question generation and generated-question snapshots.
- Candidate attempt browser.
- Offline-resilient answer saving and pending-sync processing.
- Automatic or candidate-driven attempt start execution.
- Device binding/change execution.
- Force submission, attempt unlock/suspension and reconnection execution.
- Scoring, marking, result approval and publication.
- Central public-examination signed launch and result return.

## Automated verification

Use PR #15 as the source of truth for the exact branch head and latest passing CI run before deployment. The audit contract suite checks controlled routes, read-only/import-disabled metadata, transaction locks, early reservations, cancellation/completion truth, Institution-safe options, extra-time restrictions and supported migration-query syntax.

## Deployment

```bash
cd ~/frappe-bench/apps/eduedge
git fetch origin
git switch agent/eduedge-cbt-schedule-operations-ui
git pull --ff-only origin agent/eduedge-cbt-schedule-operations-ui

cd ~/frappe-bench
bench --site eduedge.local migrate
bench build --app eduedge --force
bench --site eduedge.local clear-cache
bench --site eduedge.local clear-website-cache
bench restart
```

## Focused acceptance order

1. Page/navigation/runtime load.
2. Branch/public isolation.
3. Fixed-set Schedule creation and actual Class context.
4. Programme, Assessment Group and Invigilator cascading filters.
5. Direct status, import and direct-extra-time rejection.
6. Candidate confirmation lock.
7. Ready-stage Centre, Invigilator and candidate reservation failures.
8. Readiness/capacity/collision failures at activation.
9. Successful activation and lifecycle audit.
10. Check-in/late-entry/release boundaries.
11. Clean cancellation with automatic withdrawal of unstarted candidates.
12. Cancellation rejection after Check-in, Release or Completion.
13. Schedule completion terminal-candidate gate.
14. Single and concurrent bulk assignment behaviour.
15. Time Extension application, expiry block and cumulative maximum.
16. Recorded-for-review interventions.
17. Restricted and read-only roles.
18. No answer, academic-result or accounting mutation.
