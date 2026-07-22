# EduEdge Partner Implementation Status

**Product:** EduEdge Education Management and School Intelligence Platform  
**Publisher:** ProcessEdge Solutions Limited  
**Audience:** ProcessEdge partners, implementation collaborators, pilot institutions, advisers, and authorised stakeholders  
**Current implementation stage:** Foundation, core school operations, and CBT definition foundation  
**Last updated:** 22 July 2026  
**Repository status:** Unified CBT and Institution/Academic Context branch built and migrated successfully on the development site. Institution/Branch display and all approved Primary, Secondary, Tertiary, and Training Centre terminology passed focused browser acceptance. The branch remains under acceptance QA for restricted roles, Branch permissions, and realistic business workflows before merge or production rollout.

## 1. Purpose of this document

This is the partner-facing record of what has actually been implemented in EduEdge.

It is intentionally different from detailed engineering notes. It explains delivered business capabilities, current validation status, known limitations, and next work without exposing unnecessary source-code detail.

This document must be updated whenever a material EduEdge capability is completed, materially changed, deferred, or removed.

## 2. Status definitions

- **Implemented:** The capability exists in the EduEdge codebase and has automated verification.
- **Acceptance QA pending:** The capability is implemented but still requires migration, browser, role, or real-workflow testing on a Frappe site.
- **Planned:** The capability is part of the approved product direction but is not represented as delivered.

## 3. Current overall position

EduEdge has moved beyond a basic Frappe Education extension. The implemented foundation now supports multi-institution and multi-campus operations, branch-aware access, admissions, enrollment, classes, schedules, attendance, examinations or assessments, controlled result publication, report cards, progression review, academic-context governance, and governed CBT question and examination-template preparation.

The unified development branch has:

- passed EduEdge automated validation;
- built successfully on the target bench;
- migrated successfully on `eduedge.local` without removing CBT or Institution records as orphans;
- passed smoke tests for EduEdge Home, CBT Operations, Question Builder, and Academic Foundation;
- passed browser acceptance for persistent Institution/Branch display;
- passed live Primary/Secondary Examination, Tertiary Assessment, and Training Centre Evaluation switching;
- passed Primary Pupil/Pupils, Secondary and Tertiary Student/Students, and Training Centre Trainee/Trainees terminology;
- passed Primary Class Arm and Admission Set terminology-precedence checks; and
- retained correct Institution and Branch context throughout Institution Type switching.

The product remains **Acceptance QA pending** until restricted-role testing, Branch-permission testing, and realistic business-workflow testing are accepted.

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

### 4.3 Institution-aware terminology — Implemented; browser accepted

EduEdge presents education terminology according to the resolved Institution and Branch context while preserving stable Frappe DocType and database identities.

Approved examples include:

- Primary School: Pupil, Class, Subject, Teacher, Classroom, Period, Examination, and Class Enrollment.
- Secondary School: Student, Class, Subject, Teacher, Classroom, Period, Examination, and Class Enrollment.
- Tertiary Institution: Student, Programme, Course, Lecturer, Lecture Hall, Level, Semester, Assessment, and Programme Enrollment.
- Training Centre: Trainee, Programme, Module, Trainer, Training Room, Training Level, Evaluation, and Trainee Enrollment.

Primary and Secondary interfaces show labels such as:

- Examinations & Results
- Examination Operations
- Examination Group
- Examination Plan
- Examination Result

The internal Frappe records remain `Assessment Group`, `Assessment Plan`, and `Assessment Result` for upgrade safety.

The visible terminology layer treats Assessment, Examination, and Evaluation as a reversible family. It also treats Student, Pupil, and Trainee as a reversible learner family. When users change Institution Type, already-rendered menu labels, headings, cards, filters, placeholders, and accessible labels are recalculated without requiring a manual browser refresh.

Special phrases such as Student Group and Student Batch are resolved through their own approved terms first. This prevents incorrect wording such as “Pupil Group” where Primary displays **Class Arm**, or “Pupil Batch” where Primary displays **Admission Set**.

### 4.4 Persistent Institution and Branch context — Implemented; browser accepted

- Current Institution and Branch are displayed side by side in the EduEdge product context.
- Branch switches return the newly resolved Institution context from the server.
- Shared browser context updates after Branch switching without requiring a full page reload.
- EduEdge EdgeSuite pages use a common top-bar context display.
- Supported native Education forms receive a fallback context display where an EdgeSuite top bar is absent.
- Context resolution follows Branch → Institution → Company fallback.

### 4.5 Branch access and governance — Implemented

- Explicit user-to-Branch access assignments.
- Settings-controlled backend Branch enforcement.
- Company-level headquarters or all-Branch access where authorised.
- Branch-scoped lists, Link-field queries, reports, operational APIs, and permissions.
- Branch Governance and Accounting Center for coverage, assignments, and setup readiness.
- Enforcement cannot be enabled until all enabled Branches have valid access coverage.

### 4.6 Admissions and programme intake — Implemented

- Branch-aware Student Admission.
- Branch-aware Student Applicant processing.
- Programme filtering by Branch, academic year, period, and purpose.
- Exact Programme Offering selection for admission and enrollment.
- Application opening and closing dates on Programme Offerings.
- Admission and enrollment availability controls.
- Backend validation prevents invalid Branch, Programme, year, term, and Offering combinations.

### 4.7 Programme Offering as the delivery identity — Implemented

Programme Offering represents the exact academic intake or delivery instance rather than only a loose Programme and year combination.

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

An Offering already used by Applicants, Student Groups, or submitted Enrollments cannot be silently repurposed into another Branch, Programme, period, Level, Cohort, or delivery mode.

### 4.8 Student and enrollment context — Implemented

- Student Branch represents the learner's primary or home responsibility Branch.
- Operational Enrollment, Student Group, Schedule, Attendance, and fee context follow the selected Programme Offering and operational Branch.
- A Student can enroll at another Campus within the same Institution.
- Cross-Institution enrollment is blocked by the user interface and backend validation.
- Duplicate Enrollment for the same Student and Programme Offering is blocked.
- Final capacity checks are protected against simultaneous submissions.

### 4.9 Enrollment lifecycle — Implemented

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

- chronological status changes;
- no future-dated lifecycle changes;
- valid transition enforcement;
- Promotion remaining inside the same Institution;
- Next Academic Level validation where progression is configured;
- Transfer to another valid Programme Offering; and
- status history visibility from submitted Enrollment.

Only Active and Suspended Enrollments consume Offering capacity. Terminal statuses release the seat.

### 4.10 Academic structure and calendar — Implemented

- Institution-owned Academic Sections, such as Primary Section, Junior Secondary, Faculty, School, or Training Category.
- Institution-owned Academic Levels, such as Class, Year, Level, or Training Level.
- Ordered progression between Levels.
- Prevention of invalid progression cycles.
- Institution-specific Academic Calendars.
- Academic period rows with start dates, end dates, ordering, and result-publication dates.
- Prevention of overlapping academic periods.
- Academic Operations resolves year and period from the selected Institution calendar.
- Year-wide Student Groups remain usable during a particular term or semester.

### 4.11 Daily academic operations — Implemented

- EdgeSuite Academic Operations page.
- Branch-aware Student Groups or Classes.
- Branch-aware Rooms.
- Course Schedules.
- Many-to-many Instructor Branch Assignments.
- Instructor, Room, Group, Programme, year, period, and Branch filtering.
- Class register and Student Attendance workflow.
- Draft attendance saving.
- Submitted attendance protection; submitted records are not silently changed.
- Cross-campus Students can be included where submitted Enrollment matches the operational Programme Offering and Student Group.

### 4.12 Examinations, assessments, and results — Implemented

- Branch-aware Frappe Assessment Plans, displayed as Examination Plans for Primary and Secondary institutions.
- Branch-aware Frappe Assessment Results, displayed as Examination Results for Primary and Secondary institutions.
- Smart filtering for examiner, supervisor, room, class, and student selection.
- Institution-aware Examination/Assessment Operations page.
- Result completeness calculation by class and examination or assessment group.
- Result approval and rejection workflow.
- Controlled publication workflow.
- Append-only result publication audit logs.
- Report-card readiness blocked until required results are approved and published.

### 4.13 CBT examination-definition foundation — Implemented

EduEdge V0.8A provides governed preparation of CBT examination content and templates.

Implemented capabilities include:

- School Examination Centres and centrally governed EduEdge Exam Centres.
- School Question Bank and protected EduEdge Examination Bank ownership models.
- Question types, answer options, marks, optional negative marking, topic, curriculum, exam body, and difficulty classification.
- Draft, Under Review, Approved, and Retired question governance.
- Approved-question immutability and versioning.
- Question Builder and batch question-intake interfaces.
- School Examination and EduEdge Public Examination templates.
- Duration, attempt, pass, navigation, timeout, resume, randomisation, marking, and result-release definitions.
- Selection of only approved questions from valid scope, Branch, and Course.
- CBT Operations readiness page.
- Permission controls protecting answer banks from Students, Parents, and Invigilators.

This does **not** yet mean the Offline-Resilient CBT attempt engine is complete. Candidate scheduling, browser answer saving, network sync, server-side timing, pending-sync control, invigilator live monitoring, scoring execution, and result approval blocking remain separate planned work.

### 4.14 Report cards and progression review — Implemented

- Report Cards and Progression page.
- Report cards generated from published result records.
- Student course, grade, average, and attendance summaries.
- PDF report cards with Branch identity and optional letterhead.
- Class teacher and principal comments.
- Manual progression recommendation and approval.
- No automatic class movement, enrollment creation, or submitted-result mutation.

### 4.15 Fee and operational context foundation — Implemented

- Institution, Branch, Programme Offering, and Academic Level context added to Fee Structure, Fee Schedule, and Fees workflows.
- Context can be derived from selected Offering, Enrollment, or Fee Structure.
- Conflicting Institution, Branch, and Offering combinations are rejected.
- Leave and Student Log records derive relevant academic context.
- Submitted accounting documents are not changed by this foundation work.
- Complete EduEdge billing and EdgePay integration are not represented as finished.

### 4.16 EdgeSuite user experience — Implemented

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
- Visible terminology does not rename routes, APIs, fieldnames, or database records.
- Submitted Program Enrollment is not mutated to store lifecycle status.
- Submitted Attendance is protected from silent editing.
- Submitted result and accounting documents are not rewritten by the academic foundation.
- Ambiguous legacy records are left for review rather than guessed.
- Branch and Institution access is enforced on the backend, not only in the browser.
- Dependent fields are filtered and also validated server-side.
- Concurrent Enrollment capacity and lifecycle changes use transactional protection.
- Approved CBT questions and templates cannot be edited in place.

## 6. Validation status

### Automated validation

EduEdge CI run **1204** passed for the completed terminology correction, including:

- Python compilation;
- JSON validation;
- frontend entry-script syntax checks, including shared shell identity and terminology bundles;
- the complete pure contract test suite;
- regression contracts for reversible Examination, Assessment, and Evaluation labels;
- regression contracts for reversible Student, Pupil, and Trainee labels; and
- Student Group and Student Batch terminology-precedence protection.

### Target-site validation completed

- EduEdge assets built successfully.
- Unified branch migrated successfully on `eduedge.local`.
- Migration did not report CBT or Institution DocTypes or Pages as orphans.
- No blank page was found during the smoke test.
- No Page Not Found error was found during the smoke test.
- Institution and Branch appeared side by side on every tested EduEdge page.
- Both values updated immediately after Branch switching.
- Primary and Secondary displayed Examination wording.
- The menu displayed Examinations & Results.
- Examination Operations, Examination Group, and Examination Plan displayed correctly.
- Tertiary displayed Assessment without requiring a refresh.
- Training Centre displayed Evaluation wording without requiring a refresh.
- Primary displayed Pupil and Pupils.
- Secondary and Tertiary retained Student and Students.
- Training Centre displayed Trainee and Trainees.
- Primary displayed Class Arm rather than Pupil Group.
- Primary displayed Admission Set rather than Pupil Batch.
- Institution and Branch remained correct throughout Institution Type switching.
- CBT Operations opened successfully.
- Question Builder opened successfully.
- Academic Foundation opened successfully.

### Remaining acceptance QA

- Test restricted users against Institution and Branch permission boundaries.
- Test realistic admissions, enrollment, class, attendance, examination, result-publication, and report-card workflows.
- Test Programme Offering duplicate protection, capacity, and lifecycle transitions with realistic records.
- Verify fee context and submitted-accounting safety on the target site.
- Complete final merge-readiness review.

Automated success and focused browser acceptance do not replace full target-site operational acceptance.

## 7. Known current limitations

- Promotion and Transfer can record the approved destination Programme Offering but do not automatically create the destination Enrollment.
- Legacy submitted Enrollments without exact Programme Offering linkage remain supported through controlled contextual fallback and require gradual review.
- Complete EduEdge billing, collections, payment allocation, EdgePay integration, parent billing experience, and debt management are not represented as complete.
- The CBT question and template foundation is implemented, but the Offline-Resilient CBT attempt and answer-sync engine is still planned.
- Student Pickup Management, broader parent/student portals, LMS expansion, Examination Bank commerce, and EdgeFinder publication remain separate planned workstreams unless a later implementation note marks them delivered.
- Production readiness depends on the remaining target-site QA.

## 8. Approved next implementation direction

The next delivery stages should build on this foundation rather than bypass it. Approved future work includes:

- completing restricted-role, Branch-permission, and realistic workflow acceptance for the unified branch;
- expanding fee, billing, payment, and receivables workflows safely;
- implementing Offline-Resilient CBT;
- extending student, parent, teacher, and management operational experiences;
- implementing Student Pickup Management, including School Bus release flows;
- preparing EdgeFinder publication and inquiry data; and
- connecting appropriate services to CoreEdge and EdgePay through stable service APIs.

These items remain **Planned** until implemented and recorded in this document.

## 9. Maintenance rule

For every material EduEdge implementation:

1. Update the technical version note.
2. Update this partner implementation status.
3. Record what was implemented, what remains QA pending, and what is still planned.
4. Do not describe partially implemented or planned work as delivered.
5. Keep known limitations and migration requirements visible.
6. Reference automated and manual validation completed for the release.

This document is the primary partner-facing source of truth for EduEdge implementation status.