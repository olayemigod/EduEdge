# EduEdge CBT Schedule Operations EdgeSuite UI

## Goal

Provide one permission-aware EdgeSuite workbench for the operational layer after Question Bank and Exam Templates:

- CBT examination schedules;
- candidate assignments and eligibility;
- candidate check-in and release;
- schedule lifecycle controls; and
- append-only intervention evidence.

The native Frappe forms remain available for advanced record inspection, but they are no longer the primary operational route.

## Page

Route: `/app/eduedge-cbt-schedules`

The page provides:

1. Examination Scope, Branch, status and search filters.
2. Schedule counts and selected-schedule candidate metrics.
3. Schedule create/edit dialogs with smart Template, Subject, Centre and Invigilator searches.
4. Draft, Ready, Active, Suspended, Completed and Cancelled lifecycle actions.
5. Selected template-policy snapshot visibility.
6. Single candidate assignment and Student Group / Class bulk assignment.
7. Candidate eligibility, check-in, release, withdrawal, disqualification and completion actions.
8. Append-only intervention entry and history.
9. A deliberate `Open Full Record` fallback for advanced native inspection.

## Safety rules

- All list reads use Frappe permission-aware APIs.
- Direct record reads and writes call `check_permission`.
- School records are filtered and validated by permitted Branch.
- Public-examination operations retain CoreEdge capability checks.
- Every mutation passes through `require_eduedge_access(feature_key="cbt")`.
- Schedule and Candidate DocType controllers remain authoritative for lifecycle, scope, eligibility, duplicate and immutability rules.
- Intervention Logs remain append-only and require a reason.
- The workbench does not read or mutate candidate answers, answer keys, marking guides, scores, submitted academic records or accounting documents.
- Activated schedules are not edited; candidate-specific exceptions are recorded as interventions.

## Migration

The page introduces a standard Frappe Page record and access-manifest registrations. Run:

```bash
bench --site eduedge.local migrate
bench build --app eduedge --force
bench --site eduedge.local clear-cache
bench --site eduedge.local clear-website-cache
bench restart
```

## Focused manual QA

1. Open `/app/eduedge-cbt-schedules` from the EduEdge menu and workspace.
2. Confirm Branch-filtered schedule visibility.
3. Create a Draft schedule from an approved template.
4. Confirm Template context, Subject, Centre and policy snapshot population.
5. Move Draft to Ready and Ready to Active.
6. Confirm activation locks schedule identity and policy.
7. Assign one eligible Student.
8. Bulk assign a template Student Group / Class and confirm duplicates are skipped.
9. Check in an Eligible candidate only when the schedule policy permits it.
10. Release a Checked In candidate only when the schedule is Active.
11. Record Time Extension and Force Submission interventions and confirm schedule-policy validation.
12. Confirm intervention records cannot be edited or deleted.
13. Repeat with a restricted Branch user and a read-only user.
14. Confirm no candidate answer, marking, submitted academic or accounting data is displayed or changed.

## Out of scope

- candidate browser attempt runtime;
- answer persistence or offline synchronisation;
- invigilator live-monitor actions;
- scoring and manual marking;
- result approval and publication;
- public-examination signed launch and result return.
