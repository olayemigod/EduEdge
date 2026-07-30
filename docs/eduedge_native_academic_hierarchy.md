# EduEdge Native Academic Hierarchy

## Decision

EduEdge extends Frappe Education instead of replacing its academic masters.

The authoritative hierarchy is:

`EduEdge Institution → EduEdge School Branch → Department → Program → Student Group`

Native Frappe Education records remain authoritative for Academic Year, Academic Term, Course, Student Batch, Student Group, Course Schedule, Student Attendance, Program Enrollment and assessment records.

EduEdge adds Institution, Branch, Programme Offering, calendar, access and terminology controls around those native records.

## Institution-type mappings

### Primary School

- Department: School Section, for example `Nursery Section` or `Primary Section`.
- Program: Class, for example `Nursery 1` or `Primary 4`.
- Student Group: Class Arm, for example `Nursery 1A` or `Primary 4B`.
- Course: Subject.
- Academic Year: Academic Session.
- Academic Term: Term.

Example:

`Nursery Section → Nursery 1 → Nursery 1A`

### Secondary School

- Department: School Section, for example `Junior Secondary School` or `Senior Secondary School`.
- Program: Class, for example `JSS 1` or `SSS 2`.
- Student Group: Class Arm, for example `JSS 1A`, `JSS 1B`, or `SSS 2 Science`.
- Course: Subject.
- Academic Year: Academic Session.
- Academic Term: Term.

Example:

`Junior Secondary School → JSS 1 → JSS 1A`

### Tertiary Institution

- Department tree: Faculty, School and optional child Department.
- Program: Degree, diploma or certificate programme, for example `BSc Agriculture`.
- Student Group: Level or Lecture Group, for example `100 Level`, `100L Group A`, or `AGR 101 Lecture Group A`.
- Course: Course or module, for example `AGR 101`.
- Academic Year: Academic Session.
- Academic Term: Semester.

Example:

`School of Agriculture → BSc Agriculture → 100 Level`

A more detailed Department tree may be:

`School of Agriculture → Department of Animal Science → BSc Animal Science → 200 Level`

EduEdge does not auto-create tertiary Student Groups from legacy Academic Levels because a valid tertiary group requires Branch, Academic Session and Semester context.

### Training Centre

- Department: Training Department.
- Program: Programme.
- Student Group: Training Class.
- Course: Module.
- Academic Year: Training Year.
- Academic Term: Training Session.

## Programme Offering

`EduEdge Program Offering` is the Branch- and period-specific delivery identity for a native Program.

Its authoritative identity is:

- Institution, derived from Branch;
- School Branch / Campus;
- native Program;
- native Department, derived from Program;
- native Academic Year;
- optional native Academic Term;
- optional Student Batch / Cohort;
- study mode;
- delivery mode.

Department is read-only on the Offering. Legacy Academic Section and Academic Level fields remain hidden and read-only only for migration traceability.

An Offering identity cannot be changed after an Applicant, Student Group or submitted Program Enrollment references it. A replacement Offering must be created instead.

## Institution Academic Calendar

The Institution Academic Calendar is an EduEdge isolation wrapper, not a replacement Academic Session master.

- Native `Academic Year` is shown as Academic Session, Training Year or the configured Institution label.
- Native `Academic Term` is shown as Term, Semester, Training Session or the configured Institution label.
- `EduEdge Institution Academic Calendar` binds one Institution to one native Academic Year and its dated native Academic Terms.

The first enabled calendar for an Institution becomes Current automatically. Existing enabled calendars without a Current row are repaired by an idempotent patch.

Academic Operations fails closed when:

- no enabled Institution calendar covers the selected date;
- the selected date is inside the Academic Session but outside all configured Terms or Semesters;
- the requested Academic Year or Term does not belong to the selected Institution calendar.

Site-wide Education Settings are retained only as a legacy fallback where no EduEdge Institution context exists.

## Cascading filters

### Programme catalogue

`Institution → Department / School Section → Program / Class`

Changing Institution clears an invalid Department. Changing Department clears an invalid Program filter.

### Programme Offering

`Branch → Institution → Department filter → Program → Academic Year → Academic Term → Student Batch`

Institution and Department are derived where appropriate. The backend repeats all ownership and calendar checks.

### Student Group

`Branch / Offering → Program → Academic Year → Academic Term → Batch → Course → Students and Instructors`

Changing any parent clears invalid dependent values and student rows. Courses are limited to Program Course rows belonging to the same Institution.

### Course Schedule

`Date → Student Group → Branch / Program → Course → Instructor → Room`

The selected Student Group determines the Branch and Program. A Course Schedule date must fall inside the Student Group's Institution calendar. The Course must belong to the Program, and the Instructor and Room must belong to the Branch.

### Attendance

Attendance requires the exact Course Schedule and Student Group context. Submitted attendance is immutable. Duplicate creation is serialised and rejected.

## Migration and backward compatibility

The migration is idempotent and non-destructive.

- Legacy `EduEdge Academic Section` records are preserved and mapped to native Departments.
- Same-name Sections in a shared Company are mapped collision-safely using Institution ownership and, only when needed, an Institution-code suffix.
- Primary and Secondary legacy Academic Levels are migrated to native Programs because they represent Classes such as `JSS 1` or `Nursery 1`.
- Blank Student Group Program links are filled only where the legacy mapping is unambiguous.
- Tertiary legacy Levels are preserved for review and are not guessed into Student Groups.
- Legacy Section and Level custom fields remain hidden/read-only for traceability.
- Existing submitted enrollment, attendance, assessment, fee and accounting documents are not rewritten.

## Required QA

1. Run migration twice and confirm the second run creates no duplicate Departments, Programs or calendars.
2. Primary: `Nursery Section → Nursery 1 → Nursery 1A/Nursery 1B`.
3. Secondary: `Junior Secondary School → JSS 1 → JSS 1A/JSS 1B`.
4. Tertiary: `School of Agriculture → BSc Agriculture → 100 Level/200 Level`.
5. Verify Institution and Branch changes clear invalid dependent fields.
6. Verify Programs cannot use another Institution's Department.
7. Verify Offerings cannot use another Institution's Program, Batch, Session or Term.
8. Verify Student Groups cannot use a Course outside their Program.
9. Verify Course Schedules cannot use another Branch's Room or Instructor.
10. Verify Academic Operations blocks dates outside the Institution calendar or its Terms.
11. Verify limited Teachers see only their assigned schedules, groups, students and attendance.
12. Verify submitted attendance remains immutable and duplicate attendance is rejected.
