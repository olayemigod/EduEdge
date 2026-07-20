# EduEdge V0.6 — Report Cards and Progression Review

## Business goal

Turn published assessment results into permission-safe student report cards, while keeping comments and promotion decisions separate from submitted Assessment Results and Program Enrollments.

## Scope

V0.6 adds:

- an EdgeSuite UI Report Cards page;
- student-level result and attendance summaries;
- PDF report-card generation;
- class teacher and principal comments;
- reviewable progression recommendations;
- recommendation and approval states;
- settings for marks, letterhead, pass-average suggestion, and required comments;
- branch-aware permissions and tracked review records.

## Source of truth

Report cards use only submitted Assessment Results, a V0.5 Result Publication in `Published` status, an active Student Group membership, and submitted Student Attendance inside the academic year or term.

Draft, cancelled, unapproved, or unpublished results are excluded.

## Report Card Review

`EduEdge Report Card Review` stores one record for each published result scope and student. It contains calculated performance and attendance fields, class teacher and principal comments, a progression recommendation, review status, and audit fields.

The result scope, student, branch, year, term, and assessment group are immutable after creation.

## Progression workflow

Statuses are Draft, Recommended, and Approved. Recommendations are Pending Review, Promote, Repeat, Graduate, Transfer, and Not Applicable.

The configured pass average only suggests Promote or Repeat. It does not make the final decision.

V0.6 does not submit a Program Enrollment, move a student to another class, cancel or amend an Assessment Result, or auto-promote a student.

## Permissions

Teachers and academic operators may prepare reviews, add class teacher comments, save a recommendation, and submit it for approval. Authorized academic approvers may add the principal comment, approve a recommendation, or reopen it with a reason.

Student and Guardian access relies on standard Student read permission and is read-only. PDFs remain unavailable until publication.

## Report-card PDF

The PDF includes school/company and branch identity, student/class/year/term scope, course marks and grades, overall average, attendance, comments, recommendation, review status, and the result publication reference. A configured Letter Head may be used, and marks may be hidden in EduEdge Settings.

## Safety rules

- Submitted Assessment Results are never mutated.
- Submitted attendance is never mutated.
- Program Enrollment is never created or changed.
- Calculated metrics are refreshed from submitted source records.
- Principal comments are protected by backend role checks.
- Review status changes only through EduEdge APIs.
- Branch permissions apply to pages, APIs, list views, and review records.

## Deferred runtime QA

1. Build EdgeSuite UI and EduEdge assets.
2. Confirm `eduedge_report_cards.bundle.js` in `sites/assets/assets.json`.
3. Migrate `eduedge.local`.
4. Run the complete EduEdge tests.
5. Prepare reviews from a Published Result Publication.
6. Verify draft comments and recommendation.
7. Verify a teacher cannot edit the principal comment.
8. Verify recommendation and approval gates.
9. Verify reopening requires a reason.
10. Print a PDF and confirm branch, results, attendance, comments, and publication reference.
11. Verify unpublished scopes cannot generate report cards.
