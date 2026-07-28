# EduEdge Partner Implementation Status

**Product:** EduEdge Education Management and School Intelligence Platform  
**Publisher:** ProcessEdge Solutions Limited  
**Audience:** ProcessEdge partners, implementation collaborators, pilot institutions, advisers, and authorised stakeholders  
**Current implementation stage:** Foundation, core school operations, academic operations pages, and CBT definition foundation  
**Last updated:** 28 July 2026  
**Repository status:** The unified Institution, academic-context, CBT and EdgeSuite foundation remains under draft acceptance. A dedicated Academic Operations page batch has now been implemented for Academic Foundation, Programmes, Programme Offerings, and daily classes/schedules/attendance. Automated repository validation is green; local build, migration and combined browser acceptance are pending.

## 1. Purpose of this document

This is the partner-facing record of what has actually been implemented in EduEdge.

It is intentionally different from detailed engineering notes. It explains delivered business capabilities, current validation status, known limitations, and next work without exposing unnecessary source-code detail.

This document must be updated whenever a material EduEdge capability is completed, materially changed, deferred, or removed.

## 2. Status definitions

- **Implemented:** The capability exists in the EduEdge codebase and has automated verification.
- **Acceptance QA pending:** The capability is implemented but still requires migration, browser, role, or real-workflow testing on a Frappe site.
- **Planned:** The capability is part of the approved product direction but is not represented as delivered.

## 3. Current overall position

EduEdge has moved beyond a basic Frappe Education extension. The implemented foundation supports multi-institution and multi-campus operations, Branch-aware access, admissions, enrollment, classes, schedules, attendance, examinations or assessments, controlled result publication, report cards, progression review, academic-context governance, and governed CBT question and examination-template preparation.

The current Academic Operations page batch adds professional EdgeSuite interfaces for:

- Institution Academic Sections, Levels, progression pathways, calendars and readiness;
- Institution-owned Programmes or Classes with bounded catalogue search and safe quick maintenance;
- Branch-specific Programme Offerings with capacity, availability and identity-lock visibility; and
- daily Class/Student Group schedules, Room use and attendance readiness.

The current branch has passed:

- Python compilation;
- JSON validation;
- all registered frontend entry-script checks; and
- the complete pure contract test suite.

The product remains **Acceptance QA pending** until the latest branch is built and migrated on `eduedge.local`, the four Academic Operations page areas are tested together, restricted-role and Branch-permission checks are accepted, and realistic academic workflows are completed.

## 4. Implemented capabilities

### 4.1 Platform and deployment foundation — Implemented

- EduEdge Frappe application and dependency contract.
- Compatibility with ERPNext and Frappe Education.
- Standalone and remote platform operating modes.
- CoreEdge HTTP service boundary without requiring CoreEdge inside the EduEdge site.
- EdgeSuite UI as the product-shell foundation for EduEdge-owned operational pages.
- EduEdge Settings, Setup Center, roles, workspace, tests, and implementation documentation.

### 4.2 Institution and campus management — Implemented

- Explicit hierarchy of **ERPNext Company → EduEdge Institution → School Branch / Campus**.
- ERPNext Company retained as the legal and accounting owner.
- Multiple Institutions of different types can operate under one Company.
- Multiple Branches or Campuses can operate under each Institution.
- Seeded Institution Types: Primary School, Secondary School, Tertiary Institution, and Training Centre.
- Institution Type is controlled by EduEdge and inherited by Branches.
- Migration does not guess Institution identity from Branch names or addresses.
- Dedicated Institution Structure interface for Institution creation, Branch assignment, hierarchy review, and terminology preview.

### 4.3 Institution-aware terminology — Implemented; earlier browser acceptance completed

EduEdge presents education terminology according to the resolved Institution and Branch context while preserving stable Frappe DocType and database identities.

Approved examples include:

- Primary School: Pupil, Class, Subject, Teacher, Classroom, Period, Examination, and Class Enrollment.
- Secondary School: Student, Class, Subject, Teacher, Classroom, Period, Examination, and Class Enrollment.
- Tertiary Institution: Student, Programme, Course, Lecturer, Lecture Hall, Level, Semester, Assessment, and Programme Enrollment.
- Training Centre: Trainee, Programme, Module, Trainer, Training Room, Training Level, Evaluation, and Trainee Enrollment.

The internal Frappe records remain canonical and upgrade-safe. Visible terminology does not rename routes, APIs, fieldnames, Select values, or database records.

### 4.4 Persistent Institution and Branch context — Implemented; earlier browser acceptance completed

- Current Institution and Branch are displayed side by side in the EduEdge product context.
- Branch switches return the newly resolved Institution context from the server.
- Shared browser context updates after Branch switching without requiring a full page reload.
- EduEdge EdgeSuite pages use a common top-bar context display.
- Supported native Education forms receive a fallback context display where an EdgeSuite top bar is absent.
- Context resolution follows Branch → Institution → Company fallback.

### 4.5 Dialog and quick-editor safety — Implemented; focused retest pending

- EdgeSuite and native Frappe dialog roots are excluded from document-wide terminology DOM mutation.
- Dropdowns, autocomplete overlays, popovers, and tooltips are protected.
- Quick-editor labels and help text are translated before rendering.
- Underlying values and database identities remain unchanged.

### 4.6 Branch access and governance — Implemented

- Explicit user-to-Branch access assignments.
- Settings-controlled backend Branch enforcement.
- Company-level headquarters or all-Branch access where authorised.
- Branch-scoped lists, Link-field queries, reports, operational APIs, and permissions.
- Branch Governance and Accounting Center for coverage, assignments, and setup readiness.
- Enforcement cannot be enabled until all enabled Branches have valid access coverage.

### 4.7 Admissions and programme intake — Implemented

- Branch-aware Student Admission.
- Branch-aware Student Applicant processing.
- Programme filtering by Branch, academic year, period, and purpose.
- Exact Programme Offering selection for admission and enrollment.
- Application opening and closing dates on Programme Offerings.
- Admission and enrollment availability controls.
- Backend validation prevents invalid Branch, Programme, year, term, and Offering combinations.

### 4.8 Programme Offering as the delivery identity — Implemented

Programme Offering represents the exact academic intake or delivery instance.

It supports:

- Institution and Branch/Campus;
- Programme and Academic Section;
- Academic Level;
- Academic Year and optional Academic Term;
- Student Batch or Cohort;
- Study and Delivery Modes;
- Offering and application dates;
- admission and enrollment availability;
- capacity control; and
- stable Offering title and code.

An Offering already used by Applicants, Student Groups, or submitted Enrollments cannot be silently repurposed.

### 4.9 Student and enrollment context — Implemented

- Student Branch represents the learner's primary or home responsibility Branch.
- Operational Enrollment, Student Group, Schedule, Attendance, and fee context follow the selected Programme Offering and operational Branch.
- A Student can enroll at another Campus within the same Institution.
- Cross-Institution enrollment is blocked.
- Duplicate Enrollment for the same Student and Programme Offering is blocked.
- Final capacity checks are protected against simultaneous submissions.

### 4.10 Enrollment lifecycle — Implemented

EduEdge provides an append-only Enrollment Status Log supporting Active, Completed, Promoted, Withdrawn, Suspended, Transferred, Graduated, and Cancelled statuses.

Lifecycle changes do not mutate the submitted Program Enrollment document. Only Active and Suspended Enrollments consume Offering capacity. Terminal statuses release the seat.

### 4.11 Academic Foundation page — Implemented; acceptance QA pending

The dedicated Academic Foundation page now provides:

- Institution-owned Academic Sections;
- Institution-owned Academic Levels;
- safe Section and Level quick maintenance;
- progression pathway visibility;
- missing or disabled progression-link warnings;
- Institution Academic Calendar summaries;
- current Academic Period visibility;
- intentional calendar-gap warnings;
- current-calendar and period readiness checks; and
- native validated calendar forms for period maintenance.

Progression-cycle prevention and calendar validation remain server-authoritative.

### 4.12 Dedicated Programmes or Classes page — Implemented; acceptance QA pending

The dedicated catalogue provides:

- Institution and Academic Section filters;
- Department and text search;
- bounded pagination;
- course-row counts;
- active Programme Offering counts;
- legacy classification visibility;
- safe quick create and edit; and
- direct access to the standard Program form for Course child rows and advanced settings.

The quick editor does not rebuild or clear Program Course rows.

### 4.13 Dedicated Programme Offerings page — Implemented; acceptance QA pending

The dedicated delivery page provides:

- Branch-first filtering and creation;
- Institution-filtered Programmes, Levels and Cohorts;
- Academic Year and Period cascading;
- Study and Delivery Mode filters;
- capacity, occupied-seat and remaining-seat visibility;
- Active, Upcoming, Full, Closed and Disabled operational status;
- admission-window and enrollment availability;
- identity-lock visibility for used Offerings; and
- safe quick create and edit backed by the existing Offering controller.

Capacity uses enrollment lifecycle truth rather than a simple raw enrollment count.

### 4.14 Daily Academic Operations page — Implemented; acceptance QA pending

The page provides:

- selected Institution and Branch context;
- Institution-calendar Academic Year and Period;
- calendar-gap visibility;
- Class/Student Group counts;
- Course Schedules;
- assigned Instructors;
- Room usage and unassigned sessions;
- attendance completion by scheduled Class/Group;
- Complete, Partial and Not Started register status;
- draft attendance saving; and
- submitted attendance protection.

Submitted attendance is not silently changed.

### 4.15 Examinations, assessments, and results — Implemented

- Branch-aware Frappe Assessment Plans and Results.
- Smart examiner, supervisor, room, class, and student filtering.
- Institution-aware Examination/Assessment Operations page.
- Result completeness calculation.
- Result approval, rejection, and controlled publication.
- Append-only publication audit logs.
- Report-card readiness blocked until required results are approved and published.

### 4.16 CBT examination-definition foundation — Implemented

EduEdge provides governed preparation of CBT centres, questions, responsibilities, examination templates, schedules, candidate assignments and append-only intervention logs.

This does not yet mean the Offline-Resilient CBT attempt engine is complete. Candidate browser answer saving, network sync, server-side timing, pending-sync control, live invigilation, scoring execution, and result approval blocking remain separate planned work.

### 4.17 Report cards and progression review — Implemented

- Report Cards and Progression page.
- Report cards generated from published result records.
- Student course, grade, average, and attendance summaries.
- PDF report cards with Branch identity and optional letterhead.
- Class teacher and principal comments.
- Manual progression recommendation and approval.
- No automatic class movement, enrollment creation, or submitted-result mutation.

### 4.18 Fee and operational context foundation — Implemented

- Institution, Branch, Programme Offering, and Academic Level context added to Fee Structure, Fee Schedule, and Fees workflows.
- Conflicting Institution, Branch, and Offering combinations are rejected.
- Submitted accounting documents are not changed by the academic foundation.
- Complete EduEdge billing and EdgePay integration are not represented as finished.

## 5. Engineering and data-safety commitments enforced

- Standard Frappe Education DocType identities remain unchanged.
- Submitted Program Enrollment is not mutated to store lifecycle status.
- Submitted Attendance is protected from silent editing.
- Submitted result and accounting documents are not rewritten.
- Ambiguous legacy records are left for review rather than guessed.
- Branch and Institution access is enforced on the backend.
- Dependent fields are filtered and validated server-side.
- Concurrent Enrollment capacity and lifecycle changes use transactional protection.
- Used Programme Offering identity cannot be changed in place.
- No Academic Operations page introduces a parallel source of truth.

## 6. Validation status

### Automated validation — Passed

The latest Academic Operations page branch passed:

- Python compilation;
- JSON validation;
- all registered frontend entry-script checks; and
- the complete pure contract suite.

### Local acceptance still required

The following must still be completed on `eduedge.local`:

1. pull the latest branch;
2. build EduEdge assets;
3. migrate the site;
4. clear cache;
5. verify Academic Foundation readiness and calendar display;
6. verify Programmes/Class catalogue filters and quick editor;
7. verify Programme Offering capacity, status and identity locks;
8. verify daily schedules, Rooms and attendance readiness;
9. test Primary, Secondary, Tertiary and Training Centre terminology;
10. test restricted roles and Branch access;
11. verify submitted academic and accounting safety; and
12. complete the previously pending dialog-rendering retest.

## 7. Current limitations and planned work

- The latest Academic Operations page batch has not yet completed local browser acceptance.
- Offline-Resilient CBT candidate attempt, answer-sync and live invigilation remain planned.
- Full EduEdge billing and EdgePay integration remain planned.
- Automatic progression and class movement remain intentionally excluded.
- Wider reports, dashboards, school transport, student pickup, parent services and later intelligence modules remain phased work.
