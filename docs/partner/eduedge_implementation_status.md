# EduEdge Partner Implementation Status

**Product:** EduEdge Education Management and School Intelligence Platform  
**Publisher:** ProcessEdge Solutions Limited  
**Audience:** ProcessEdge partners, implementation collaborators, pilot institutions, advisers, and authorised stakeholders  
**Current implementation stage:** Foundation and core school operations  
**Last updated:** 22 July 2026  
**Repository status:** V0.9 implemented on the active development branch; bench migration and browser acceptance remain required before merge or production rollout.

## 1. Purpose of this document

This is the partner-facing record of what has actually been implemented in EduEdge.

It is intentionally different from the detailed engineering notes. It explains delivered business capabilities, current validation status, known limitations, and the next areas of work without exposing unnecessary source-code detail.

The document must be updated whenever a material EduEdge feature is completed, materially changed, deferred, or removed.

## 2. Status definitions

- **Implemented:** The capability exists in the EduEdge codebase and has automated verification.
- **Acceptance QA pending:** The capability is implemented but still requires migration, browser, role, or real-workflow testing on a Frappe site.
- **Planned:** The capability is part of the approved product direction but is not represented as delivered.

## 3. Current overall position

EduEdge has moved beyond a basic Frappe Education extension. The implemented foundation now supports multi-institution and multi-campus education operations, branch-aware access, admissions, enrollment, classes, schedules, attendance, assessments, controlled result publication, report cards, progression review, institutional terminology, and academic context governance.

The current V0.9 work is **implemented with automated CI passed**, but remains **Acceptance QA pending** until the target bench is built, migrated, and tested in the browser with realistic users and data.

## 4. Implemented capabilities

### 4.1 Platform and deployment foundation — Implemented

- EduEdge Frappe application and dependency contract.
- Compatibility with ERPNext and Frappe Education.
- Standalone and remote platform operating modes.
- CoreEdge HTTP service boundary without requiring CoreEdge to be installed inside the EduEdge site.
- EdgeSuite UI as the product-shell foundation for EduEdge-owned operational pages.
- EduEdge Settings, Setup Center, roles, workspace, tests, and implementation documentation.

### 4.2 Institution and campus management — Implemented

- Explicit hierarchy of **ERPNext Company → EduEdge Institution → School Branch / Campus**.
- ERPNext Company retained as the legal and accounting owner.
- Multiple Institutions of different types can operate under one Company.
- Multiple Branches or Campuses can operate under each Institution.
- Seeded Institution Types:
  - Primary School
  - Secondary School
  - Tertiary Institution
  - Training Centre
- Institution Type is controlled by EduEdge and inherited by Branches.
- Migration does not guess Institution identity from Branch names or addresses.
- Dedicated Institution Structure interface for Institution creation, Branch assignment, hierarchy review, and terminology preview.

### 4.3 Institution-aware terminology — Implemented

EduEdge can present appropriate education terminology according to the resolved Institution and Branch context.

Examples include:

- Primary and Secondary contexts using Class, Subject, Teacher, Classroom, and Period.
- Tertiary contexts using Programme, Course, Lecturer, Lecture Hall, Level, and Semester.
- Training Centre contexts using Programme, Module, Trainer, Training Room, Training Level, and Intake.

The underlying Frappe Education DocType and database identities remain stable. EduEdge changes visible product wording rather than performing unsafe global renames.

### 4.4 Branch access and governance — Implemented

- Explicit user-to-Branch access assignments.
- Settings-controlled backend Branch enforcement.
- Company-level headquarters or all-Branch access where authorised.
- Branch-scoped lists, Link-field queries, reports, operational APIs, and permissions.
- Active Branch context displayed in the EduEdge product shell.
- Branch Governance and Accounting Center for coverage, assignments, and setup readiness.
- Enforcement cannot be enabled until all enabled Branches have valid access coverage.

### 4.5 Admissions and programme intake — Implemented

- Branch-aware Student Admission.
- Branch-aware Student Applicant processing.
- Programme filtering by Branch, academic year, period, and purpose.
- Exact Programme Offering selection for admission and enrollment.
- Application opening and closing dates on Programme Offerings.
- Admission and enrollment availability controls.
- Backend validation prevents invalid Branch, Programme, year, term, and Offering combinations.

### 4.6 Programme Offering as the delivery identity — Implemented

Programme Offering now represents the exact academic intake or delivery instance, rather than only a loose Programme and year combination.

It supports:

- Institution and Branch/Campus.
- Programme and Academic Section.
- Academic Level.
- Academic Year and optional Academic Term.
- Student Batch or Cohort.
- Study mode and delivery mode.
- Offering and application dates.
- Admission and enrollment availability.
- Capacity control.
- Stable Offering title and code.

An Offering that is already used by Applicants, Student Groups, or submitted Enrollments cannot be silently repurposed into another Branch, Programme, period, Level, Cohort, or delivery mode.

### 4.7 Student and enrollment context — Implemented

- Student Branch represents the learner's primary or home responsibility Branch.
- Operational Enrollment, Student Group, Schedule, Attendance, and fee context follow the selected Programme Offering and operational Branch.
- A Student can enroll at another Campus within the same Institution.
- Cross-Institution enrollment is blocked by the user interface and backend validation.
- Duplicate Enrollment for the same Student and Programme Offering is blocked.
- Final capacity checks are protected against simultaneous submissions.

### 4.8 Enrollment lifecycle — Implemented

EduEdge provides an append-only Enrollment Status Log supporting:

- Active
- Completed
- Promoted
- Withdrawn
- Suspended
- Transferred
- Graduated
- Cancelled

Lifecycle changes do not mutate the submitted Program Enrollment document.

Additional controls include:

- Chronological status changes.
- No future-dated lifecycle changes.
- Valid transition enforcement.
- Promotion remaining inside the same Institution.
- Next Academic Level validation where progression is configured.
- Transfer to another valid Programme Offering.
- Status history visibility from submitted Enrollment.

Only Active and Suspended Enrollments consume Offering capacity. Terminal statuses release the seat.

### 4.9 Academic structure and calendar — Implemented

- Institution-owned Academic Sections, such as Primary Section, Junior Secondary, Faculty, School, or Training Category.
- Institution-owned Academic Levels, such as Class, Year, Level, or Training Level.
- Ordered progression between Levels.
- Prevention of invalid progression cycles.
- Institution-specific Academic Calendars.
- Academic period rows with start dates, end dates, ordering, and result publication dates.
- Prevention of overlapping academic periods.
- Academic Operations resolves the year and period from the selected Institution calendar.
- Year-wide Student Groups remain usable during a particular term or semester.

### 4.10 Daily academic operations — Implemented

- EdgeSuite Academic Operations page.
- Branch-aware Student Groups or Classes.
- Branch-aware Rooms.
- Course Schedules.
- Many-to-many Instructor Branch Assignments.
- Instructor, Room, Group, Programme, year, period, and Branch filtering.
- Class register and Student Attendance workflow.
- Draft attendance saving.
- Submitted attendance protection; submitted records are not silently changed.
- Cross-campus Students can be included where their submitted Enrollment matches the operational Programme Offering and Student Group.

### 4.11 Assessment and results — Implemented

- Branch-aware Assessment Plans.
- Branch-aware Assessment Results.
- Smart filtering for examiner, supervisor, room, class, and student selection.
- Assessment Operations page.
- Result completeness calculation by class and assessment group.
- Result approval and rejection workflow.
- Controlled publication workflow.
- Append-only result publication audit logs.
- Report-card readiness blocked until the required results are approved and published.

### 4.12 Report cards and progression review — Implemented

- Report Cards and Progression page.
- Report cards generated from published result records.
- Student course, grade, average, and attendance summaries.
- PDF report cards with Branch identity and optional letterhead.
- Class teacher and principal comments.
- Manual progression recommendation and approval.
- No automatic class movement, enrollment creation, or submitted-result mutation.

### 4.13 Fee and operational context foundation — Implemented

- Institution, Branch, Programme Offering, and Academic Level context added to Fee Structure, Fee Schedule, and Fees workflows.
- Context can be derived from the selected Offering, Enrollment, or Fee Structure.
- Conflicting Institution, Branch, and Offering combinations are rejected.
- Leave and Student Log records derive relevant academic context.
- Submitted accounting documents are not changed by this foundation work.
- No claim is made that the complete EduEdge billing and EdgePay integration is finished.

### 4.14 EdgeSuite user experience — Implemented

- Professional EduEdge product shell.
- Grouped product navigation.
- Responsive desktop and mobile navigation.
- Searchable EdgeSuite product menu.
- EduEdge brand palette and shared spacing standards.
- Academic Foundation page for Academic Section and Academic Level setup.
- Institution-aware Programme and Programme Offering quick editors.
- Context-aware field filtering and backend validation.
- Native Frappe forms retained for advanced administrative work.

## 5. Engineering and data-safety commitments already enforced

- Standard Frappe Education DocType identities remain unchanged.
- Submitted Program Enrollment is not mutated to store lifecycle status.
- Submitted Attendance is protected from silent editing.
- Submitted result and accounting documents are not rewritten by the academic foundation.
- Ambiguous legacy records are left for review rather than guessed.
- Branch and Institution access is enforced on the backend, not only in the browser.
- Dependent fields are filtered and also validated server-side.
- Concurrent Enrollment capacity and lifecycle changes use transactional protection.

## 6. Automated validation status

The reviewed V0.9 development head passed EduEdge GitHub CI run 1140, including:

- Python compilation.
- JSON validation.
- Frontend entry-script syntax checks.
- The complete pure contract test suite.

Automated success does not replace target-site migration, browser acceptance, permission testing, or real operational workflow QA.

## 7. Acceptance QA still required

Before V0.9 is merged or represented as production-ready, ProcessEdge must complete:

- EduEdge and EdgeSuite UI build on the target bench.
- Site migration and cache clearing.
- Institution and Branch hierarchy tests.
- Institution terminology tests for all four seeded types.
- Academic Section, Level, progression, and calendar tests.
- Programme Offering and capacity tests.
- Same-Institution cross-campus Enrollment tests.
- Cross-Institution rejection tests.
- Student Group membership and Attendance tests.
- Enrollment lifecycle and append-only protection tests.
- Fee-context and submitted-accounting safety tests.
- Restricted-role and Branch-permission tests.
- Browser acceptance for EduEdge-owned EdgeSuite pages.

## 8. Known current limitations

- Promotion and Transfer can record the approved destination Programme Offering, but do not automatically create the destination Enrollment.
- Legacy submitted Enrollments without exact Programme Offering linkage remain supported through controlled contextual fallback and require gradual review.
- Complete EduEdge billing, collections, payment allocation, EdgePay integration, parent billing experience, and debt management are not represented as complete.
- Offline-Resilient CBT, Student Pickup Management, broader parent/student portals, LMS expansion, Examination Bank commerce, and EdgeFinder publication remain separate planned workstreams unless a later implementation note marks them delivered.
- Production readiness depends on the remaining target-site QA.

## 9. Approved next implementation direction

The next delivery stages should build on this foundation rather than bypass it. Approved future work includes:

- completing bench and browser acceptance for V0.9;
- expanding fee, billing, payment, and receivables workflows safely;
- implementing Offline-Resilient CBT;
- extending student, parent, teacher, and management operational experiences;
- implementing Student Pickup Management, including School Bus release flows;
- preparing EdgeFinder publication and inquiry data;
- connecting appropriate services to CoreEdge and EdgePay through stable service APIs.

These items remain **Planned** until implemented and recorded in this document.

## 10. Maintenance rule

For every material EduEdge implementation:

1. Update the technical version note.
2. Update this partner implementation status.
3. Record what was implemented, what remains QA pending, and what is still planned.
4. Do not describe partially implemented or planned work as delivered.
5. Keep known limitations and migration requirements visible.
6. Reference the automated and manual validation completed for the release.

This document is the primary partner-facing source of truth for EduEdge implementation status.