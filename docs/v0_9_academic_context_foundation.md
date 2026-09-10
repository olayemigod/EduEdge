# EduEdge V0.9 — Academic Context Foundation

## Business goal

EduEdge V0.9 makes one Frappe site capable of supporting Primary Schools, Secondary Schools, Tertiary Institutions, and Training Centres without changing the underlying Frappe Education DocType identities.

The implementation separates legal/accounting ownership from academic and operational context:

- **ERPNext Company** remains the legal and accounting owner.
- **EduEdge Institution** represents a school, college, university, academy, or training organisation.
- **EduEdge School Branch / Campus** represents the operational campus or centre.
- **Programme Offering** represents the exact intake and delivery context used by admissions, enrollment, classes, fees, and academic operations.

## Core hierarchy

```text
ERPNext Company
└── EduEdge Institution
    └── EduEdge School Branch / Campus
        └── Programme Offering
            ├── Academic Year / Period
            ├── Programme / Class
            ├── Academic Section
            ├── Academic Level
            ├── Cohort / Batch
            ├── Study Mode
            └── Delivery Mode
```

Institution Type is owned by EduEdge Institution and inherited by its Branches. Company Institution Type remains only a migration and no-context fallback.

## Institution terminology

The seeded Institution Types remain system-managed:

- Primary School
- Secondary School
- Tertiary Institution
- Training Centre

Examples of visible terminology:

| Canonical key | Primary | Secondary | Tertiary | Training Centre |
|---|---|---|---|---|
| Programme | Class | Class | Programme | Programme |
| Enrollment | Class Enrollment | Class Enrollment | Programme Enrollment | Trainee Enrollment |
| Student | Pupil | Student | Student | Trainee |
| Academic Section | School Section | School Section | Faculty / School | Training Category |
| Academic Level | Class | Class | Level | Training Level |
| Course | Subject | Subject | Course | Module |
| Instructor | Teacher | Teacher | Lecturer | Trainer |

The database identities, API fieldnames, DocType names, and routes stay canonical and upgrade-safe.

## New EduEdge masters

### EduEdge Academic Section

Institution-owned structure for examples such as:

- Primary
- Junior Secondary
- Senior Secondary
- Faculty of Engineering
- School of Business
- Professional Training

Rules:

- Section Code is normalized and immutable after creation.
- Section Code is unique within one Institution.
- Institution cannot change after creation.
- Duplicate checks are serialized per Institution.

### EduEdge Academic Level

Institution-owned progression level for examples such as:

- Primary 1
- JSS 2
- SS 3
- 100 Level
- Year 2
- Intermediate

Rules:

- Level Code is normalized and immutable after creation.
- Level Code is unique within one Institution.
- Optional Academic Section must belong to the same Institution.
- Optional Next Academic Level must belong to the same Institution.
- Progression cycles are blocked.
- Academic Section cannot change after Programme Offerings use the Level.

### EduEdge Institution Academic Calendar

Institution-specific calendar containing one Academic Year and its periods.

Rules:

- One calendar per Institution and Academic Year.
- Institution and Academic Year are immutable after creation.
- One current calendar per Institution.
- Calendar/current-record operations are serialized per Institution.
- Periods must belong to the selected Academic Year.
- Period dates must fall inside the calendar dates.
- Periods cannot overlap.
- Result Publication Date cannot precede period end.

Academic Operations resolves the year and period from the selected Branch's Institution calendar. When the selected date falls inside an Institution calendar but outside all configured periods, the Academic Term is intentionally blank rather than inherited from global Education Settings.

## Programme Offering

Programme Offering is the authoritative operational academic identity.

It contains:

- School Branch / Campus
- Institution
- Programme
- Academic Section
- Academic Level
- Academic Year
- optional Academic Term
- optional Student Batch / Cohort
- Offering Title
- immutable Offering Code
- Study Mode
- Delivery Mode
- Start and End Dates
- Application Window
- Admission and Enrollment availability
- Capacity

### Identity safety

The following fields form the Offering identity:

- Branch
- Programme
- Academic Year
- Academic Term
- Cohort / Batch
- Study Mode
- Delivery Mode
- Academic Level

Once Applicants, Student Groups, or submitted Program Enrollments reference the Offering, these identity fields cannot change. A new Offering must be created instead.

Duplicate Offering checks use nullable-safe comparisons and a Branch row lock so concurrent requests cannot create the same academic identity.

### Capacity

Capacity `0` means no configured limit.

Only enrollments with current lifecycle status **Active** or **Suspended** consume seats. Completed, Promoted, Withdrawn, Transferred, Graduated, and Cancelled enrollments release capacity.

Program Enrollment submission locks the Offering row and rechecks:

- duplicate submitted Enrollment for the same Student and Offering;
- current capacity-consuming seat count.

This prevents concurrent submissions from oversubscribing the Offering.

## Student and operational Branch model

The Student `eduedge_school_branch` field represents the Student's primary or home responsibility Branch. It does not permanently own every academic activity.

Operational records use the Programme Offering and operational Branch:

- Student Applicant
- Program Enrollment
- Student Group
- Course Schedule
- Student Attendance
- Fees and Fee Schedule context

A Student may enroll at another Branch or Campus inside the same Institution. Enrollment into another Institution is blocked by backend validation even when a crafted API request bypasses the UI.

## Applicant and enrollment flow

### Student Applicant

The exact Programme Offering can be selected. It derives:

- Branch
- Institution
- Programme
- Academic Year
- Academic Term
- Academic Level

The Offering's application window is checked against the Applicant's Application Date.

### Program Enrollment

The user can select a target Branch before selecting the Offering. After an Offering is selected:

- Branch becomes authoritative and read-only in the UI;
- Programme, year, period, level, and cohort are derived;
- the Student may come from another Campus in the same Institution;
- duplicate Enrollment for the same Student and Offering is blocked;
- final capacity is checked during submission.

Existing submitted legacy Enrollments without exact Offering linkage are not silently rewritten.

### Student Group

Student Group can link to the exact Offering. Group context derives Branch, Institution, Programme, year, period, level, and cohort.

Eligible Student options come from submitted Program Enrollments. Exact Offering linkage is preferred; legacy contextual matching remains available for older Enrollments.

### Attendance

Attendance follows Course Schedule and Student Group context rather than Student home Branch.

Backend validation confirms:

- Schedule and Group Branch agreement;
- the Student is an active member of the Group;
- the operational Branch is accessible to the user.

## Enrollment lifecycle

EduEdge Enrollment Status Log is the append-only lifecycle truth.

Supported statuses:

- Active
- Completed
- Promoted
- Withdrawn
- Suspended
- Transferred
- Graduated
- Cancelled

Rules:

- only submitted Program Enrollments can receive lifecycle logs;
- logs cannot be edited or deleted;
- submitted Program Enrollment is never mutated to store status;
- future-dated and out-of-order changes are blocked;
- lifecycle changes are serialized on the Enrollment row;
- invalid transitions are blocked;
- Promotion and Transfer require a target Programme Offering;
- Promotion remains in the same Institution;
- when Next Academic Level is configured, Promotion must use that Level.

Submitted Program Enrollment exposes actions for changing status and viewing status history.

## Institution-scoped masters

Custom Institution fields are added to:

- Program
- Course
- Student Batch Name
- Student House
- Instructor
- Assessment Group
- Grading Scale
- Fee Structure

New records require Institution. Existing blank legacy records remain visible and reviewable during rollout.

Once a legacy record has been classified, it cannot be silently moved to another Institution.

Permission queries scope classified records to the user's permitted Institutions. Legacy blank records remain visible only to support controlled classification and backward compatibility.

## Fee and operational context

Institution, Branch, Offering, and Level context is added where available to:

- Fee Structure
- Fee Schedule
- Fees
- Student Leave Application
- Student Log

Context is derived from the selected Offering, Program Enrollment, Fee Structure, Course Schedule, Student Group, or Student.

Conflicting Institution, Branch, or Offering combinations are rejected. The explicit Fee Schedule Offering is preserved after derived context is rebuilt.

No submitted accounting document is edited, cancelled, recreated, or otherwise mutated by V0.9.

## Permissions and API safety

- Branch access remains permission-aware.
- Institution-owned records are scoped to permitted Institutions when branch enforcement is enabled.
- Programme Offering reads require record permission and Branch access.
- Generic academic lookup is restricted to an explicit DocType allowlist.
- Cross-campus Student lookup is limited to academic/administrative roles and one Institution.
- Student Group member lookup requires an academic operator role and Branch access.
- Enrollment lifecycle records are scoped through the source Enrollment Branch.

## EdgeSuite UI

### Academic Foundation page

Provides Institution-scoped management of:

- Academic Sections
- Academic Levels
- progression order
- navigation to Institution Academic Calendars

### Program quick editor

Supports:

- Institution
- Academic Section
- Program Name and Abbreviation
- Department

Academic Section options filter by Institution.

### Programme Offering quick editor

Supports:

- Branch
- Institution-filtered Programme
- year and period
- Academic Level
- Cohort
- Offering identity
- study and delivery modes
- dates, capacity, and availability

Dependent fields clear and refresh when parent context changes.

## Migration and backward compatibility

The installation and migration flow is idempotent.

### Deterministic backfill

Existing Offering records receive deterministic values for:

- Offering Code
- Offering Title
- Institution from Branch
- Academic Section from Program

Master Institution backfill is applied only when all source evidence resolves to exactly one Institution:

- Program from its Offerings;
- Course from classified Programs;
- Cohort from Offerings;
- Instructor from enabled Branch Assignments.

Ambiguous records remain blank for manual review. EduEdge does not infer Institution from names, addresses, Programme names, or Branch labels.

### Legacy behavior retained

- Existing submitted academic records are not rewritten.
- Existing submitted accounting records are not mutated.
- Legacy Program Enrollments without Offering linkage remain usable through contextual fallback.
- Standard Frappe Education DocType names, APIs, routes, and field identities remain unchanged.
- Lifecycle capacity helpers fall back safely during a partial migration before the new lifecycle table is synchronized.

## Automated validation

The branch CI validates:

- Python compilation;
- JSON parsing;
- frontend entry-script syntax;
- pure contract tests covering hierarchy, context resolution, permissions, migration, Offering identity, capacity, lifecycle, calendar behavior, fee context, and EdgeSuite wiring.

Automated checks do not replace bench migration and browser QA.

## Bench QA checklist

1. Pull the feature branch.
2. Run `bench build --app eduedge`.
3. Run `bench --site <site> migrate`.
4. Run `bench --site <site> clear-cache`.
5. Confirm no migration error around Program Course, Student Batch Name, Instructor Branch Assignment, or Custom Field updates.
6. Verify Company → Institution → Branch hierarchy and active context switching.
7. Create Primary, Secondary, Tertiary, and Training Centre Institutions and verify visible terminology.
8. Configure Academic Sections, Levels, Next Level progression, and calendars.
9. Verify a progression cycle is rejected.
10. Create year-wide and period-specific Programme Offerings with different study/delivery modes.
11. Verify duplicate Offering identity is rejected.
12. Create Applicants using Offering application dates inside and outside the window.
13. Enroll a Student at the home Campus and another Campus in the same Institution.
14. Verify cross-Institution enrollment is rejected.
15. Verify the target Branch is selectable before Offering and locks after Offering selection.
16. Verify duplicate Enrollment and full-capacity submission are blocked.
17. Withdraw or Transfer an Enrollment and confirm the seat becomes available.
18. Verify Offering identity and capacity cannot be changed unsafely after use.
19. Build a Student Group from exact Offering Enrollments.
20. Verify cross-campus Students appear when they hold the correct submitted Enrollment.
21. Create a Schedule and Attendance record and confirm Student home Branch does not block valid operational context.
22. Create lifecycle status changes and verify chronology, transition, next-level, and append-only rules.
23. Confirm submitted Program Enrollment remains unchanged after lifecycle updates.
24. Verify Institution Academic Calendar drives Academic Operations for the selected date.
25. Verify year-wide Groups remain visible during a configured period.
26. Verify a calendar gap shows no Academic Term rather than an unrelated global term.
27. Verify Fee Structure, Fee Schedule, and Fees reject mixed Institution/Branch/Offering context.
28. Confirm submitted accounting documents are untouched.
29. Test restricted users against multiple Institutions and Branches.
30. Review all legacy blank masters and classify only those with confirmed ownership.

## Known constraints

- V0.9 does not automatically create a new Enrollment after Promotion or Transfer. The status log records the approved destination; the destination Enrollment remains a deliberate operational action.
- Legacy Enrollments without exact Offering linkage remain contextual and should be reviewed gradually rather than rewritten automatically.
- Database/schema assumptions must be confirmed on the target Frappe Education v16 bench through `migrate` and manual QA.
- Institution terminology changes visible labels only; canonical DocType and database identities remain unchanged.
