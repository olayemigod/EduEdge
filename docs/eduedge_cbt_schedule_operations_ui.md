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
- Subject/Course ownership must match the Schedule Institution/Company context.
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

## Migration

`bench --site <site> migrate` is required because this change adds:

- EduEdge CBT Lifecycle Log DocType;
- Schedule Class/academic and lifecycle fields;
- Candidate lifecycle field;
- composite Candidate Assignment unique indexes.

The uniqueness patch is idempotent and stops with a clear validation error when pre-existing duplicates must be resolved. Do not apply raw `ALTER TABLE` commands.

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

Use PR #15 as the source of truth for the exact branch head and latest passing CI run before deployment.

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
4. Candidate confirmation lock.
5. Readiness/capacity/collision failures.
6. Successful activation and lifecycle audit.
7. Check-in/late-entry/release boundaries.
8. Single and concurrent bulk assignment behaviour.
9. Time Extension application and cumulative maximum.
10. Recorded-for-review interventions.
11. Restricted and read-only roles.
12. No answer, academic-result or accounting mutation.
