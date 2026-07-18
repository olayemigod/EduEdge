# EduEdge V0.5 — Assessments, Results, Approval and Publication

## Business goal

Give schools a branch-safe assessment and result workflow that separates score entry from authorized publication. Teachers and academic staff can enter and submit results, while report-card availability remains blocked until completeness and approval rules are satisfied.

## Upstream Education records retained

EduEdge continues to use the standard Frappe Education records:

- Assessment Group
- Assessment Plan
- Assessment Result
- Assessment Criteria and Grading Scale

No upstream Education source file or whitelisted API is overridden.

## Branch context

EduEdge adds School Branch / Campus to Assessment Plan and Assessment Result through idempotent Custom Fields.

- Assessment Plan inherits branch from Student Group.
- Assessment Result inherits branch from Assessment Plan and Student.
- Student Group, room, examiner, supervisor, student, academic year and term combinations are validated at the backend.
- Branch permission conditions apply to lists, forms, APIs and result-publication records.

## Result publication control

`EduEdge Result Publication` defines one publication scope by:

- branch/campus;
- student group/class;
- academic year;
- optional academic term;
- assessment group.

Statuses are:

1. Draft
2. Pending Approval
3. Approved
4. Rejected
5. Published

The status can be changed only through the EduEdge assessment APIs. Every transition creates an append-only `EduEdge Result Publication Log`.

## Completeness calculation

For the selected scope, EduEdge calculates:

- submitted Assessment Plans;
- active students in the Student Group;
- expected result count (`plans × students`);
- submitted results;
- draft results;
- missing results.

Approval is blocked unless every expected result exists and is submitted. Publication repeats the completeness check so results cannot be published after the underlying scope becomes incomplete.

## Accounting and document safety

Assessment Plan and Assessment Result are submitted Education documents. EduEdge does not mutate submitted records. Corrections must use cancellation and amendment through the standard Frappe workflow.

The publication workflow updates only the EduEdge publication-control document and its append-only audit logs.

## EdgeSuite UI

The product-owned page `/app/eduedge-assessment-operations` provides:

- campus, year, term, class and assessment-group filters;
- plan and result-completeness cards;
- assessment-plan navigation;
- publication-control creation;
- approval request, approval, rejection and publication actions;
- report-card readiness status.

Standard Assessment Plan and Assessment Result forms remain available for upgrade-safe detailed setup and score entry.

## Deferred live QA

After pulling and migrating the local site, validate:

1. Assessment Plan branch inheritance and filtering.
2. Examiner, supervisor and room campus restrictions.
3. Assessment Result branch/student validation.
4. Result completeness with draft, missing and submitted records.
5. Approval blocked when any result is missing or draft.
6. Rejection reason and append-only status logs.
7. Publication only after approval.
8. Report-card readiness only after publication.
9. Branch switching and permissions in EdgeSuite UI.
