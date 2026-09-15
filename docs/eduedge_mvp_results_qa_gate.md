# EduEdge MVP Results and Report Cards QA Gate

This gate covers the Result Profile, terminal/yearly result engine, publication snapshots, issued report cards and progression handoff introduced for the EduEdge MVP.

## Governing architecture

Frappe Education remains the academic source of truth:

`Assessment Group -> Assessment Plan -> Assessment Result -> EduEdge Result Profile -> Result Engine -> Result Publication -> Published Result Snapshot -> Report Card Review -> Issued Report Card`.

Do not create or edit a parallel marks ledger during QA.

## Reference QA setup

Create an Institution and enabled Branch / Campus with one Academic Year and an Institution Academic Calendar containing three result periods. The display labels may be `Alpha`, `Rapha`, `Omega`, but these labels must come from calendar configuration and must not be hardcoded.

Use one sessional Student Group / Class Arm across the three periods for annual-result QA.

Create a Result Profile with:

- Continuous Assessment component, target maximum 40.
- Examination component, target maximum 60.
- Both components required.
- Native Frappe Assessment Groups mapped to the two components.
- A configured Grading Scale with Report Remarks.
- Equal Average of Eligible Terms for the baseline annual case.
- Average of Subject Percentages for the baseline overall percentage case.

Configure presentation options and verify they are snapshotted at publication.

## Calculation acceptance fixtures

### Terminal result

For one subject:

- CA = 30 / 40
- Examination = 47 / 60
- Expected Total = 77 / 100
- Expected Percentage = 77.00

The report must preserve the two configured components and must not collapse them into an opaque total.

### Annual equal-average result

For one subject:

- Alpha: 30 + 47 = 77
- Rapha: 33 + 41 = 74
- Omega: 36 + 39 = 75
- Expected cumulative Total = 226
- Expected annual Average = 75.33

### Not Offered is not a zero

For one subject:

- Alpha: 35 + 50 = 85
- Rapha: 31 + 47 = 78
- Omega: Not Offered
- Expected cumulative Total = 163
- Expected eligible periods = 2
- Expected annual Average = 81.50

A genuine scored zero must remain a numeric zero. `Absent`, `Exempt` and `Not Offered` must remain distinguishable from zero and from missing/pending data.

## Configurable class metrics

Test at least these two profiles.

### Raw-score statistics

Configure:

- Class Highest, display label `CHS`, basis `Annual Cumulative Raw Score`, display as Raw Score.
- Class Lowest, display label `CLS`, basis `Annual Cumulative Raw Score`, display as Raw Score.
- Class Average, display label `CAS`, basis `Annual Cumulative Raw Score`, display as Raw Score.

Verify that CHS / CLS / CAS are only display labels. No schema or report template may require those exact labels.

### Percentage statistics

Configure:

- Class Highest, display label `Highest %`, basis `Annual Average Percentage`, display as Percentage.
- Class Lowest, display label `Lowest %`, basis `Annual Average Percentage`, display as Percentage.
- Class Average, display label `Average %`, basis `Annual Average Percentage`, display as Percentage.

The report must render the percentage labels and values without CHS / CLS / CAS appearing.

Also test a profile with all class metrics hidden.

## Attendance

For Terminal mode:

- attendance scope must use the selected Academic Term;
- Present is the Student's submitted Present count;
- School Opened is the count of distinct submitted attendance dates for the governed class/scope;
- attendance percentage is Present / School Opened.

For Annual mode, the attendance window must cover the configured result periods in the Academic Year.

Do not use raw Student Attendance record count as School Opened.

## Result Profile presentation

Verify that Result Profile settings can independently control:

- Terminal report title;
- Annual report title;
- Student photo;
- Attendance section;
- Teacher / Principal comments;
- Progression section;
- Grading legend;
- Next academic period date.

Change these settings after a publication is issued and confirm that the old immutable publication/issue continues to render its frozen configuration.

## Publication governance

1. Incomplete results must block approval.
2. Draft Assessment Results must block approval.
3. Missing required components must block approval when the profile policy says so.
4. Annual publication must use a Result Profile.
5. Annual publication must fail closed for a legacy term-bound Student Group.
6. Publication scope, mode and Result Profile must become immutable after approval begins.
7. Publishing must create one immutable Published Result Snapshot per Student.
8. Cancelling/amending source Assessment Results after publication must not rewrite the old snapshot.
9. A correction must create a new Result Publication version.
10. Old publication versions must remain readable.

## Report Card review and issue governance

1. Class Teacher Comment is editable only in Draft review according to permissions.
2. Principal Comment is restricted to the authorized academic approver.
3. Report-card approval must create an immutable `EduEdge Report Card Issue`.
4. PDF before review approval must visibly show `DRAFT / UNISSUED REPORT CARD`.
5. PDF after approval must show the issued report-card version.
6. Reopening an approved review must not delete or mutate the previous issue.
7. Re-approval must create Issue Version 2 and link it to the previous issue.
8. Branding and Institution identity used by an issued report card must remain frozen for that issue.

## Progression

Terminal publication must not auto-promote a Student.

For Annual mode:

1. the calculated result may suggest Promote / Repeat according to configured policy;
2. teacher review must remain explicit;
3. authorized approval must remain explicit;
4. only an approved Annual review may be handed to Student Progression;
5. the progression workflow, not the report engine, performs the actual enrolment/class movement;
6. the immutable result snapshot must be re-verified before progression evidence is accepted.

## Permissions and isolation

Test at least:

- System Manager / EduEdge Administrator;
- School Administrator;
- Academic Administrator;
- Teacher;
- user restricted to another Branch.

Verify Result Profiles, Result Publications, Published Result Snapshots, Report Card Reviews and Report Card Issues are Branch/Institution safe.

A user restricted to Branch A must not read, create, approve, publish or issue Branch B results.

## PDF / visual QA

Terminal:

- A4 portrait.
- Dynamic component columns.
- Dynamic class metric columns.
- no clipped subject, grade, remark or statistic values.
- student identity, attendance, comments and grade legend follow profile settings.

Annual:

- A4 landscape.
- each configured academic period displays its configured label;
- each period retains its configured component columns;
- cumulative Total, Average, Grade, Remark and configured class metrics fit without clipping;
- long Subject names wrap cleanly.

Test both light and dark EdgeSuite UI for the browser pages. Printed/PDF output must remain print-safe and independent of the active desk theme.

## Migration / compatibility gate

Before QA freeze:

1. clean Frappe/ERPNext/Education/EduEdge install passes;
2. migrate passes;
3. a second migrate is idempotent;
4. existing V0.6 legacy result publications still open and print;
5. existing CBT result sync still writes native Assessment Results;
6. existing Assessment Result entry and submission continue to work;
7. existing Student Progression regression suite remains green;
8. EdgeSuite UI candidate compatibility passes.

## QA freeze rule

Do not freeze `qa/eduedge-mvp-results-v1` until the exact Result Engine and Report Cards V2 heads have all required CI, integration and EdgeSuite compatibility checks green.

Once frozen, browser QA is performed only on that exact QA head. Corrections after freeze are blocker-only and must be revalidated before the QA head advances.
