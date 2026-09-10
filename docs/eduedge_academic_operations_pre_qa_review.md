# EduEdge Academic Operations Pages — Pre-QA Engineering Review

**Review date:** 2026-07-29  
**Branch:** `agent/eduedge-academic-operations-pages`  
**Pull request:** #14  
**Reviewed code head:** `fbf57b9985f51e39056de0b2b2131e7a9d23b362`  
**Status:** Conditional pass for local QA; not approved for merge or production release.

## 1. Review scope

This review examined the completed Academic Operations page batch and the shared controls the pages depend on:

- Academic Foundation;
- Programmes / Classes;
- Programme Offerings;
- daily Academic Operations;
- Institution and Branch permission queries;
- Teacher / Instructor ownership;
- attendance creation, editing and submission;
- native Student, Guardian, Enrollment, Student Group, Course Schedule and Student Attendance access;
- Programme Offering identity, capacity and calendar context;
- dependent-field behaviour;
- list-query performance;
- upgrade and backward-compatibility risks.

The review was performed as a release gate. Clear defects were fixed on the feature branch instead of being deferred to browser QA.

## 2. Critical and high-risk findings fixed

### 2.1 Unclassified academic masters could leak across tenants

Restricted Institution users could previously see legacy Program, Course and related masters whose Institution field was blank. On a shared-hosted site, blank records are not safely attributable to a tenant.

**Fix:** Restricted users now fail closed. Only privileged EduEdge administrators can see and classify blank legacy academic masters.

### 2.2 Attendance API bypassed Role Permission Manager

The inherited attendance save path used `ignore_permissions`, allowing the API to create or submit records based mainly on role-name checks.

**Fix:**

- the public attendance endpoints now route through secure overrides;
- Student Attendance read, create, write and submit permissions are checked separately;
- document-level write and submit permission checks are enforced;
- the UI receives the effective permission matrix and hides or disables unavailable actions;
- no secure attendance path uses `ignore_permissions`.

### 2.3 Teacher accounts could inherit branch-wide personal and academic access

A Teacher or Instructor account combined with Frappe Education permissions could see more branch data than the assigned timetable required.

**Fix:** EduEdge resolves the logged-in User through active Employee and Instructor records. Limited Teacher / Instructor users are now scoped to:

- their Course Schedules;
- Student Groups used by their schedules;
- Students in those groups;
- Guardians linked to those students;
- Program Enrollments for those students;
- Student Attendance linked to their schedules.

Student Admission and Student Applicant records are denied to limited Teacher / Instructor users. Administrative roles remain explicit bypasses.

### 2.4 Attendance could be attached to a mismatched schedule

Native Student Attendance could carry a Course Schedule while retaining another Student Group or date.

**Fix:** Native validation now derives and validates Student Group, date and Branch from the Course Schedule and rejects mismatches.

### 2.5 Concurrent duplicate attendance creation was not serialised

Two users could attempt to create the same Student Attendance identity at nearly the same time.

**Fix:** Attendance validation now locks the Course Schedule or Student Group identity and rejects another non-cancelled record for the same Student, Class, date and scheduled session.

### 2.6 Multiple sessions for one Class could share misleading readiness

Attendance readiness was originally calculated at Student Group level. One completed session could make another session for the same Class appear complete.

**Fix:** Readiness is calculated and opened per Course Schedule.

### 2.7 Programme Offering accepted weakly validated linked context

The quick editor and controller did not fully reject unclassified or cross-Institution linked records.

**Fix:** New or re-contextualised Offerings now validate:

- readable Programme;
- Programme Institution;
- enabled Academic Section;
- enabled and Section-compatible Academic Level;
- readable Academic Year and Period;
- Institution-calendar ownership of the Period;
- readable and Institution-owned Student Batch / Cohort;
- Branch access;
- identity immutability after operational usage.

Legacy Offerings are not blocked when only non-identity fields are edited.

### 2.8 Programme Department options were global

Department autocomplete could offer another Institution Company's Department.

**Fix:** Department lookup and save validation now follow the selected Institution's Company. Institution changes clear stale Section and Department values.

### 2.9 Programme Offering capacity page used an N+1 query pattern

The Offering catalogue could run one lifecycle capacity query for every visible Offering.

**Fix:** Occupied-seat counts are grouped and fetched in one batched query for the visible page.

### 2.10 UI actions did not consistently reflect backend permission

The page could display New Class, Add Schedule, Save Draft or Submit buttons to users who lacked the corresponding DocType permission.

**Fix:** Actions, editable controls and read-only messages now follow backend create, write, read and submit permissions. The page also uses the Frappe/site date instead of a UTC browser date.

### 2.11 Programme Offering Academic Level did not cascade by Programme

The quick editor could display every enabled Level in the Institution even when the selected Programme belonged to a specific Academic Section.

**Fix:** Programme selection now filters both catalogue and quick-editor Level options to Levels valid for the Programme's Academic Section and clears an invalid selected Level.

## 3. Remaining risks and decisions

These items are not currently classified as critical blockers to starting local QA, but they must remain visible.

### 3.1 Academic Foundation list caps — medium scale risk

Academic Foundation currently uses bounded global reads for Institutions, Sections, Levels, Calendars and Calendar Periods. A very large shared-hosted site can reach those caps and produce incomplete readiness summaries.

**Required direction:** Before large shared-hosted rollout, change the page to load one selected Institution at a time or return explicit truncation metadata and warnings.

### 3.2 Teacher identity is an operational dependency

Teacher ownership depends on a valid chain:

`User → active Employee → active Instructor → Course Schedule`

A Teacher without this chain is denied rather than granted broad fallback access. Setup and staff-onboarding QA must verify the chain and provide a clear administrative correction path.

### 3.3 Assessment ownership is outside this page batch

This review closes Teacher scope for class, student, guardian, enrollment, schedule and attendance records used by the Academic Operations pages. Assessment Plan, Assessment Result, report-card review and publication ownership require their own focused review during the Assessment Operations phase.

### 3.4 Automated checks are not Frappe runtime acceptance

Current CI covers Python compilation, JSON validation, JavaScript entry syntax and pure contract tests. It does not replace:

- migration on a real site;
- Frappe permission evaluation with actual users and roles;
- MariaDB query execution;
- asset build;
- browser rendering;
- concurrent requests;
- real workflow data.

### 3.5 Rapid filter changes may produce stale UI responses

The Vue pages do not yet cancel or sequence overlapping requests. A user changing filters rapidly could briefly see an older response replace a newer one.

**Required direction:** Observe during browser QA. Add request sequence guards if reproducible.

## 4. Mandatory local QA matrix

### 4.1 User profiles

Test all pages as:

1. System Manager / EduEdge Administrator;
2. School Administrator;
3. Academic Administrator;
4. Teacher + Instructor + required Frappe Education role, with valid Employee and Instructor linkage;
5. Teacher with no Employee / Instructor linkage;
6. read-only academic user;
7. user restricted to one Branch;
8. user with two permitted Branches;
9. user from another Institution on the same site.

### 4.2 Permission and isolation tests

Verify that:

- one Institution cannot see another Institution's classified Programmes or masters;
- restricted users cannot see blank/unclassified legacy masters;
- Teachers see only assigned Student Groups, Students, Guardians and Enrollments;
- Teachers cannot open unassigned Course Schedules or Attendance records by direct URL;
- Teachers cannot view Applicant or Admission records;
- administrators retain intended broader access;
- Branch switching never expands permission beyond configured access.

### 4.3 Attendance workflow tests

Verify:

- one Class with two schedules on the same date produces two readiness rows;
- each readiness row opens the exact session;
- loading attendance without a schedule is blocked when multiple sessions exist;
- a Teacher can update only an assigned session;
- draft attendance can be edited by a permitted user;
- submitted attendance remains immutable;
- a user without submit permission can save draft but cannot submit;
- concurrent creation attempts produce one record and one duplicate error;
- native Student Attendance rejects mismatched Student Group, date or Branch.

### 4.4 Programme and Offering tests

Verify:

- Institution change clears invalid Academic Section and Department;
- Department options follow Institution Company;
- Branch and Programme changes refresh valid Programme, Level, Cohort and Period options;
- Programme selection filters Levels by Academic Section and clears an invalid Level;
- Periods come only from the Institution Academic Calendar;
- disabled or cross-Institution links are rejected;
- Offering identity becomes locked after Applicant, Student Group or submitted Enrollment usage;
- capacity reflects Active and Suspended lifecycle states;
- Full, Closed and Disabled Offerings do not show misleading enrollment availability.

### 4.5 UI and terminology tests

Verify:

- actions disappear or become read-only when permission is missing;
- no hidden action remains callable through an exposed button;
- Primary, Secondary, Tertiary and Training Centre labels remain correct;
- empty, loading and error states are useful;
- mobile and tablet layouts remain usable;
- rapid filter changes do not leave stale context visible.

## 5. Automated validation

The reviewed code head passed EduEdge CI run 2101:

- Python compilation;
- JSON validation;
- all registered frontend entry-script checks, including the Level cascade module;
- 321 pure contract tests.

## 6. Release gate

PR #14 must remain draft.

It may proceed to local QA because the reviewed code head passed CI. It must not be merged into `agent/eduedge-integrated-foundation` until:

- local build and migration pass;
- the mandatory role and isolation matrix passes;
- any runtime permission or SQL defects are fixed;
- browser acceptance is recorded.

## 7. Safety preserved

The review did not introduce a schema migration and did not alter submitted accounting documents, submitted enrollments, CBT attempt truth or result-publication truth. Existing controller validation and native full forms remain authoritative.
