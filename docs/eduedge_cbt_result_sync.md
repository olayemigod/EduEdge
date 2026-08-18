# EduEdge School CBT Result Sync V1.1

## Status

Implemented on the stacked branch `agent/eduedge-cbt-result-sync`.

This phase connects **approved school CBT results** to Frappe Education Assessment Results. It does not handle EduEdge public-examination results, publish report cards, or replace the existing academic result-approval workflow.

## Business goal

Allow a school to conduct an examination in EduEdge CBT and safely reuse the approved score in its normal academic results without double entry.

The flow preserves three separate truths:

1. **CBT operational truth** — attempt, answer sync, integrity review, scoring and CBT result approval.
2. **Frappe Education academic truth** — Assessment Plan and submitted Assessment Result.
3. **EduEdge publication truth** — result approval, publication and report-card readiness.

No step silently collapses these boundaries.

## School examination mapping

Each School Examination schedule must be linked to one submitted Frappe Education `Assessment Plan` before the schedule becomes Ready.

The linked plan must match:

- School Branch / Campus;
- Student Group / Class;
- Subject / Course;
- Academic Year where the template defines one;
- Academic Term where the template defines one;
- Assessment Group where the template defines one.

For V1.1 the plan must contain exactly one Assessment Criterion. The plan maximum score, its single criterion maximum score and the approved CBT Template total marks must be equal.

EduEdge deliberately does not guess how to distribute one CBT score across several assessment criteria. Multi-criterion mapping is a later governed enhancement.

## Candidate eligibility

Candidate Assignments now use the Student Group snapshot stored on the Examination Schedule rather than re-reading the current template.

This protects an activated sitting from later template retirement or revision. The student must remain an active member of that Student Group and must belong to the same Branch as the schedule.

## Result-sync workflow

### 1. Complete CBT governance

Before academic sync:

- the Examination Schedule must be `Completed`;
- all browser answers must be synchronised;
- all attempt-review requirements must be resolved;
- all relevant attempts must be scored;
- every CBT Result must be `Approved`;
- no active candidate may be missing a latest attempt or approved result.

The existing server-side CBT result-readiness gate is called again during sync.

### 2. Prepare Assessment Result drafts

From the completed School Examination Schedule, select:

**CBT Results → Prepare Assessment Result Drafts**

EduEdge creates one draft Frappe Education `Assessment Result` per approved CBT Result.

Each draft contains:

- the linked submitted Assessment Plan;
- the candidate Student;
- the Assessment Plan's single criterion;
- the approved CBT score, floored at zero where negative marking produced a negative raw total;
- the source CBT Result;
- the source CBT Examination Schedule;
- the normal EduEdge School Branch field populated by existing academic validation.

Preparation does not submit or publish the academic result.

### 3. Review drafts

Academic staff may inspect the prepared drafts before submission.

EduEdge will not overwrite a draft whose criterion or score was manually changed. A changed draft blocks submission and must be resolved explicitly.

If another Assessment Result already exists for the same Student and Assessment Plan but was not created from the selected CBT Result, EduEdge blocks the sync instead of replacing it.

### 4. Submit prepared results

From the schedule, select:

**CBT Results → Submit Prepared Assessment Results**

Only unchanged, source-linked drafts are submitted. Submitted Assessment Results are never mutated, cancelled or replaced automatically.

Re-running the submit action is idempotent: already submitted source-linked records are reported as existing and are not submitted again.

### 5. Use the existing publication workflow

Submitting Assessment Results does not publish them.

Schools continue with the existing EduEdge academic workflow:

1. refresh result readiness;
2. request result approval;
3. approve results;
4. publish results;
5. prepare report cards.

This ensures CBT scores follow the same management controls as manually entered assessment scores.

## Traceability and audit

Frappe Education `Assessment Result` receives two EduEdge custom fields:

- `Source CBT Result`;
- `CBT Examination Schedule`.

`EduEdge CBT Result` records the linked Assessment Plan, Assessment Result and preparation/submission audit actors and times.

`EduEdge CBT Result Sync Log` is an append-only audit record for:

- draft preparation;
- academic-result submission.

The log stores the Branch, Student, Assessment Plan, CBT Result, Assessment Result, approved score snapshot, actor and time.

## Idempotency and conflict behaviour

The service is safe to retry.

- Existing source-linked draft: returned without duplication.
- Existing source-linked submitted result: returned without mutation.
- Existing unrelated result for the same Student and Assessment Plan: blocked.
- Cancelled source-linked result: blocked pending a governed replacement decision.
- Manually changed source-linked draft: blocked rather than overwritten.
- Changed or cancelled Assessment Plan: blocked.
- Public Examination Schedule: blocked before any local result is created.

The request transaction rolls back if any candidate fails validation, preventing a partially prepared or partially submitted schedule batch.

## Roles

Preparation and submission are restricted to:

- Administrator;
- System Manager;
- EduEdge Super Administrator;
- EduEdge Administrator;
- School Administrator;
- Academic Administrator.

Normal Teachers, Instructors, Students, Parents and CBT Invigilators are not granted result-sync actions.

## Public examination boundary

Tenant sites cannot create Frappe Education Assessment Results from EduEdge Public Examinations.

Public-examination results remain reserved for the future central signed-result service. No public candidate reference, protected public answer key or centrally governed public result is copied into a local school's academic records by this phase.

## Migration and deployment

Do not migrate the existing `eduedge.local` Branch Access QA site while the stacked CBT work remains under acceptance.

Use an isolated CBT test site:

```bash
cd ~/frappe-bench-cbt
git -C apps/eduedge checkout agent/eduedge-cbt-result-sync
bench --site eduedge-cbt.local migrate
bench build --app eduedge
bench --site eduedge-cbt.local clear-cache
bench restart
```

Migration adds:

- School Assessment Result Integration fields to CBT Examination Schedule;
- Frappe Education source-link custom fields on Assessment Result;
- academic sync fields on EduEdge CBT Result;
- EduEdge CBT Result Sync Log.

No existing Assessment Result is backfilled or modified.

## Manual QA

### Mapping and activation

1. Create a submitted Assessment Plan for one Branch, Student Group and Course.
2. Give the plan exactly one Assessment Criterion.
3. Set the plan and criterion maximum score equal to the approved CBT Template total marks.
4. Create a School Examination Schedule from that template.
5. Confirm the Assessment Plan field shows only context-relevant submitted plans.
6. Confirm a mismatched Branch, Class, Course, academic period or score is rejected server-side.
7. Confirm the schedule cannot become Ready without an Assessment Plan.
8. Confirm a Public Examination Schedule clears and rejects local academic mapping.

### Candidate eligibility

9. Assign an active Student from the schedule's Student Group.
10. Confirm a Student outside the locked group is rejected.
11. Revise or retire the template after activation and confirm the Candidate Assignment still uses the schedule snapshot.

### Preparation

12. Complete attempts, pending-sync reconciliation, attempt review, scoring and CBT result approval.
13. Mark the schedule Completed.
14. Prepare Assessment Result drafts.
15. Confirm one draft exists per approved CBT Result.
16. Confirm each draft contains the correct Student, plan, criterion, score and CBT source links.
17. Repeat preparation and confirm no duplicate is created.
18. Create an unrelated Assessment Result for one Student and plan, then confirm preparation blocks without overwriting it.

### Submission

19. Submit the prepared Assessment Results.
20. Confirm all records are submitted and CBT Results show `Submitted` sync status.
21. Repeat submission and confirm it is idempotent.
22. Change a prepared draft score before submission and confirm the batch is blocked.
23. Confirm submitted Assessment Results are never edited, cancelled or replaced by the service.

### Publication boundary

24. Confirm preparation and submission do not create or publish an `EduEdge Result Publication`.
25. Use the existing Assessments & Results workspace to request approval and publish.
26. Confirm report-card readiness follows the existing publication rules.

### Branch and security

27. Confirm a user assigned only to another Branch cannot prepare, submit or view sync logs for this schedule.
28. Confirm Teacher, Instructor, CBT Invigilator, Student and Parent roles cannot run result sync.
29. Confirm a public schedule cannot call either sync action.
30. Confirm sync logs cannot be edited or deleted.

## Deferred enhancements

- explicit mapping of CBT sections or questions to multiple Assessment Criteria;
- governed replacement after a source-linked Assessment Result is cancelled;
- automatic draft-review assignment;
- bulk dashboard for several schedules;
- signed public-examination result return;
- candidate result portal and result notifications;
- analytics and school-intelligence aggregation after publication.
