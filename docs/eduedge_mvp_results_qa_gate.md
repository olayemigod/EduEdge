# EduEdge MVP Results, Report Cards and Result Operations QA Gate

This gate covers Smart Mark Entry, Result Profiles, terminal/yearly result processing, publication snapshots, issued report cards, Student/Guardian publishing, broadsheets, result intelligence and progression handoff introduced for the EduEdge MVP.

## Governing architecture

Frappe Education remains the academic source of truth:

`Assessment Group -> Assessment Plan -> Assessment Result -> EduEdge Result Profile -> Result Engine -> Result Publication -> Published Result Snapshot -> Report Card Review -> Issued Report Card -> Student/Guardian My Results`, with Broadsheet and Result Intelligence reading the immutable published snapshot rather than creating another result store.

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

## Smart Mark Entry

Use the native Frappe Education `Assessment Result Tool` enhanced by EduEdge.

Verify:

1. single-cell score edits autosave as Draft Assessment Results;
2. multi-cell spreadsheet paste maps across Student rows and configured assessment criteria;
3. pasted values are bounded by the native criterion maximum and rejected again on the server if invalid;
4. `Scored`, `Absent`, `Exempt`, and `Not Offered` remain distinct states;
5. a genuine scored zero remains `0`, not Missing or Absent;
6. submitted Assessment Results remain read-only and cannot be rewritten by autosave;
7. autosave never auto-submits results;
8. teacher assignment, Branch context and native Assessment Result permissions are still enforced;
9. refresh/resume shows saved Draft values rather than losing entered marks;
10. the native explicit Submit workflow still works after EduEdge enhancement.

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

## Result verification and school identity

For Result Profiles with the relevant presentation controls enabled:

1. issued PDFs may show the configured report signatory name/title/signature;
2. issued PDFs may show the Institution official stamp/seal;
3. issued PDFs may show a verification QR code;
4. the QR must resolve to the public `/eduedge-result-verify` page using an unguessable per-issue token;
5. verification must validate both the token and immutable payload SHA-256;
6. public verification must not reveal marks, teacher/principal comments or attendance;
7. current issues show `Current`;
8. an authentic older issue shows `Superseded` when a newer issue exists;
9. an authentic issue whose review was reopened shows `Review Reopened`;
10. report identity/presentation changes after issue must not rewrite the previous immutable issue.

## Student / Guardian My Results portal

Verify the authenticated `/eduedge-results` experience:

1. a Student account resolves through native `Student.user`;
2. Guardian access resolves through native `Guardian.user` plus the Student Guardian relationship;
3. a Guardian linked to multiple children sees only those children;
4. an unrelated logged-in user cannot fetch another Student by changing request parameters;
5. only effective immutable `EduEdge Report Card Issue` records are shown;
6. Draft reviews, unpublished snapshots and live Assessment Results are never exposed;
7. reopening an Approved review removes that issue from the current official portal view until re-approved;
8. re-approval exposes the newer issue version;
9. the official PDF download is generated from the frozen issued payload;
10. issued-result notifications contain no marks or result details and link back to the authenticated My Results portal.

## Result Broadsheet

Verify `/app/eduedge-result-broadsheet`:

1. Branch, Academic Year, Class, Result Type and Terminal Academic Term filters cascade correctly;
2. Annual mode uses the governed annual publication scope;
3. if multiple Result Profiles are published for the same class/period, the user must choose the exact Published Result;
4. the latest correction publication version is used for the exact selected scope;
5. subject columns are dynamic from the immutable published snapshot;
6. wide tables retain sticky Roll / Student identity columns and scroll safely;
7. CSV export values exactly match the same immutable snapshot displayed on screen;
8. Not Offered / Exempt subjects are not silently converted to scored zero;
9. ranking/position is not invented when no Institution ranking policy exists;
10. Branch isolation is enforced server-side.

## Result Intelligence

Verify `/app/eduedge-result-intelligence`:

1. only management/academic roles with Branch access can load the page/API;
2. latest Published Result Publication version wins per governed scope;
3. class/student/subject/trend figures come only from immutable Published Result Snapshots;
4. draft/live Assessment Results never appear in intelligence;
5. subject Average/Highest/Lowest/Spread calculations use the configured published percentages;
6. below-cohort-average is an action/review signal, not an inferred fail label;
7. pass rate is not inferred until an explicit Institution pass-policy contract exists;
8. corrected publication versions are not double-counted;
9. Terminal and Annual filters behave correctly;
10. light/dark mode, table overflow and Report Cards navigation are usable.

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

Do not freeze `qa/eduedge-mvp-results-v1` until the exact combined `integration/eduedge-mvp-results-v1` head contains Result Engine, Report Cards V2, Smart Mark Entry, My Results portal, Result Broadsheet and Result Intelligence and that exact combined head has CI, Integration and EdgeSuite compatibility green.

Once frozen, browser QA is performed only on that exact QA head. Corrections after freeze are blocker-only and must be revalidated before the QA head advances.
