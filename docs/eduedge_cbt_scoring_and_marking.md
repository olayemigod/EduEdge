# EduEdge CBT Scoring and Manual Marking

## Scope

This layer scores completed school-CBT attempts, queues written responses for authorised manual marking, records append-only marking audits, and approves results after the server-side readiness gate passes.

It does not publish results, create Frappe Assessment Result records, generate report cards, collect payments, or score public examinations on tenant sites.

## Result records

### EduEdge CBT Result

One Result is created per CBT Attempt. It stores:

- Examination Schedule, Exam Template, Branch, Course, Candidate Assignment, Student, and candidate identity;
- objective, manual, total, percentage, pass mark, and outcome summaries;
- question-level Result Items;
- manual-question pending count;
- result status;
- approval actor, time, and note.

The Attempt link is unique. Repeating scoring returns the existing Result instead of creating a duplicate.

### EduEdge CBT Result Item

Each Result Item snapshots:

- question identity and candidate-visible question text;
- available and negative marks;
- awarded mark;
- scoring method;
- marking status;
- marker, marked time, and marker comment.

### EduEdge CBT Marking Log

Every manual mark save creates an append-only audit row containing the previous and new mark, marker comment, actor, and time.

Result and Marking Log records cannot be edited through normal Desk saves or deleted. Only the governed scoring service may change them.

## Objective scoring policy

Objective question types are:

- Single Choice;
- Multiple Choice;
- True/False;
- Yes/No.

Scoring uses exact option-set matching. Multiple Choice does not receive partial credit in this MVP.

- Exact answer: full question mark.
- Unanswered: zero.
- Incorrect answer: configured negative mark, unless the Exam Template uses **Disable Negative Marking**.

Correct option IDs come only from the protected Attempt Scoring Key. They are not read from candidate-visible question snapshots.

## Manual marking policy

Short Answer, Essay, and Numeric questions enter the manual queue.

The queue shows only questions whose status is `Manual Required`. It provides authorised markers with:

- candidate name;
- question and question type;
- candidate response;
- answer key;
- marking guide;
- available mark;
- awarded mark field;
- marker comment field.

Awarded marks must remain between zero and the available mark. Revising a previously completed manual mark requires a Marker Comment.

Ordinary Teachers and Instructors do not receive Result or Marking Log access by default because the queue exposes answer keys and marking guides. Marker assignment by subject/class remains a future governed capability.

## Attempt transitions

After objective scoring:

- an objective-only attempt becomes `Scored`;
- an attempt with manual questions becomes `Under Review`.

After the final manual question is marked, the Attempt becomes `Scored` and the Result becomes `Ready for Review`.

## Approval gate

Schedule approval calls:

```python
assert_result_approval_ready(exam_schedule)
```

Approval remains blocked when the schedule has:

- no active candidates or attempts;
- missing candidate attempts;
- Prepared, In Progress, Pending Sync, or Timed Out attempts;
- unresolved browser answers;
- integrity-review flags;
- incomplete result-processing states;
- attempts that are not Scored.

When ready, authorised administrators can approve all schedule Results. Approval records the actor, time, and optional note.

Approval does not publish the result and does not create or mutate Frappe Assessment Result records.

## Permissions

Default marking access is limited to:

- System Manager;
- EduEdge Super Administrator;
- EduEdge Administrator;
- School Administrator;
- Academic Administrator;
- Education Manager.

Only the first five roles can run schedule objective scoring and approval. Education Manager can complete the manual marking queue but cannot approve schedule results.

All records remain subject to Branch permission hooks. Result Item visibility is resolved through the parent Result.

## Marking workspace

Route:

```text
/app/eduedge-cbt-marking
```

The EdgeSuite page supports:

- Branch and Schedule selection;
- schedule-level objective scoring;
- manual-response queue;
- candidate search;
- result-readiness blockers;
- manual mark saving;
- schedule result approval.

## QA checklist

1. Score an objective-only submitted attempt and confirm exact-match marks.
2. Submit a wrong objective answer with negative marking enabled and confirm deduction.
3. Repeat with negative marking disabled and confirm zero deduction.
4. Confirm unanswered objective questions score zero.
5. Score a Multiple Choice response containing extra or missing options and confirm no partial credit.
6. Score an attempt with Essay, Short Answer, and Numeric questions and confirm all enter manual marking.
7. Retry scoring and confirm the existing Result is returned without duplication.
8. Enter a mark below zero or above the available mark and confirm rejection.
9. Complete a manual mark and confirm an append-only Marking Log.
10. Revise the completed mark without a comment and confirm rejection.
11. Revise with a comment and confirm previous/new marks are audited.
12. Confirm the final manual question moves the Attempt to Scored and Result to Ready for Review.
13. Confirm approval is blocked while pending sync or integrity review exists.
14. Confirm approval succeeds only when every latest relevant Attempt is Scored.
15. Confirm approval does not create Frappe Assessment Result or publication records.
16. Confirm Teachers, Instructors, Students, Parents, and CBT Invigilators cannot access the marking queue by default.
17. Confirm Branch-restricted users cannot see Results or Marking Logs outside their permitted Branches.

## Deployment boundary

Do not migrate the current `eduedge.local` Branch Access QA site. Use a separate CBT bench/site or wait until that QA cycle is complete.
