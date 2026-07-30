# EduEdge Native Academic Hierarchy and Progression

## Decision

EduEdge extends Frappe Education instead of replacing its academic masters.

The shared authoritative hierarchy is:

`EduEdge Institution → EduEdge School Branch → Department → Program`

The layers below Program depend on the Institution type:

- Primary/Secondary: `Program/Class → Student Group/Class Arm`;
- Tertiary/Training: `Program/Qualification → EduEdge Academic Level/Stage → Student Group/Lecture or Training Group`.

Native Frappe records remain authoritative for Department, Program, Course, Academic Year, Academic Term, Program Enrollment, Student Group, Course Schedule, Student Attendance and assessment records.

EduEdge adds Institution, Branch, Programme Offering, formal progression, calendar, access and terminology controls around those records.

## Master records versus period records

### Reusable masters

These are configured once and reused:

- Department: School Section, Faculty, School or Academic Department;
- Program: Class/Grade or qualification curriculum;
- Course: Subject, Course or Module;
- EduEdge Academic Level: formal tertiary/training progression stage;
- Student Batch: admission cohort or entry set.

A Primary/Secondary Institution should have one reusable `JSS 1` Program, not one Program per Academic Session. A tertiary Institution should have one reusable `BSc Agriculture` Program and formal Levels such as `100 Level`, `200 Level` and `300 Level` beneath it.

### Period-specific operational records

These are created for a delivery period:

- Programme Offering;
- Program Enrollment;
- Student Group;
- Course Schedule;
- Student Attendance;
- Assessment Plan and Result Publication.

A Student Group is a roster, not a permanent academic Level. `JSS 1A` may be created again for the next Academic Session, while another `JSS 1A` in the same Branch, Program, Session and Term context is blocked.

## Institution-type mappings

### Primary School

- Department: School Section, for example `Nursery Section` or `Primary Section`;
- Program: Class, for example `Nursery 1` or `Primary 4`;
- Student Group: Class Arm, for example `Nursery 1A` or `Primary 4B`;
- Course: Subject;
- Academic Year: Academic Session;
- Academic Term: Term.

Example:

`Nursery Section → Nursery 1 → Nursery 1A`

The Class Arm is Academic-Session-wide. It is not recreated separately for First, Second and Third Term.

### Secondary School

- Department: School Section, for example `Junior Secondary School` or `Senior Secondary School`;
- Program: Class, for example `JSS 1` or `SSS 2`;
- Student Group: Class Arm, for example `JSS 1A`, `JSS 1B` or `SSS 2 Science`;
- Course: Subject;
- Academic Year: Academic Session;
- Academic Term: Term.

Example:

`Junior Secondary School → JSS 1 → JSS 1A`

### Tertiary Institution

- Department tree: Faculty, School and optional child Academic Department;
- Program: qualification curriculum, for example `BSc Agriculture`;
- EduEdge Academic Level: formal progression stage, for example `100 Level` or `200 Level`;
- Student Group: Lecture, practical or administrative group, for example `200L Group A` or `AGR 201 Lecture Group A`;
- Course: Course or Module, for example `AGR 201`;
- Academic Year: Academic Session;
- Academic Term: Semester.

Example:

`School of Agriculture → BSc Agriculture → 200 Level → 200L Group A`

A more detailed Department tree may be:

`Faculty of Agriculture → Department of Animal Science → BSc Animal Science → 300 Level → ANS 301 Lecture Group A`

`BSc`, `MSc` and `PhD` are separate Programs. Moving from BSc to MSc or MSc to PhD is a new admission/enrollment, not ordinary Level promotion.

### Training Centre

- Department: Training Department;
- Program: Programme;
- EduEdge Academic Level: Training Stage;
- Student Group: Training Group;
- Course: Module;
- Academic Year: Training Year;
- Academic Term: Training Session.

## Program progression modes

Every Program has one progression mode.

### Program Promotion

Used for Primary and Secondary Classes.

Example:

`JSS 1 → JSS 2 → JSS 3 → SSS 1`

Program fields include:

- progression sequence;
- next Program/Class;
- terminal Program flag;
- allow repetition.

A promotion creates a new Program Enrollment for the next Class and later Academic Session. The submitted source enrollment is not edited.

### Level Progression

Used for tertiary and training Programs.

Example:

`BSc Agriculture: 100 Level → 200 Level → 300 Level → 400 Level`

Each Level belongs to exactly one Program and Institution. Level fields include:

- sequence;
- next Level;
- terminal Level flag;
- enabled status.

A promotion retains the Program and creates a new enrollment for the next Level and later Academic Session.

### No Automatic Progression

Used where progression requires manual review or does not follow a fixed chain.

## Programme Offering identity

`EduEdge Program Offering` is the Branch- and period-specific delivery identity for a native Program.

### Program Promotion Offering

Identity:

`Branch + Program/Class + Academic Session`

Academic Level and Academic Term must be blank. The Class Offering covers the full Academic Session.

Example:

`Main Campus + JSS 1 + 2026/2027`

Student Groups beneath it may be `JSS 1A` and `JSS 1B`.

### Level Progression Offering

Identity:

`Branch + Program + Academic Level + Academic Session + Academic Term`

Example:

`Main Campus + BSc Agriculture + 200 Level + 2026/2027 + First Semester`

Student Groups beneath it may be `200L Group A` or `AGR 201 Lecture Group A`.

Institution is derived from Branch. Department is derived from Program. An Offering identity cannot be changed after an Applicant, Student Group or submitted Program Enrollment references it; a replacement Offering must be created.

## Level-aware curriculum

Native `Program Course` remains authoritative but EduEdge extends each row with:

- Academic Level;
- curriculum period number;
- course type: Core, Elective or Optional;
- credit units.

Primary/Secondary Programs normally leave Academic Level and period number blank. Tertiary/training Programs use them to filter valid Courses for a Level and Semester.

Generic legacy Program Course rows with no Level remain available across Levels for backward compatibility.

## Enrollment progression workflow

The guided workflow supports:

- Promote;
- Repeat;
- Transfer within the same Institution;
- Complete;
- Graduate;
- Withdraw;
- Hold for Review;
- Suspend and Reactivate.

Promotion, repetition and transfer create a new draft Program Enrollment from an exact target Programme Offering. The target draft records:

- source Program Enrollment;
- planned outcome;
- reason or approval note.

After the target enrollment is reviewed and submitted, EduEdge creates an append-only Enrollment Status Log against the source. Submitted historical enrollments are never mutated.

A transfer to another Institution requires a new admission rather than automatic internal progression.

## Student Group rollover

A Student Group is rolled over to an eligible target Offering.

Examples:

- `JSS 1A → JSS 2A` in the next Academic Session;
- `200L Group A → 300L Group A` in the next Academic Session.

The new group inherits the target Program, Level, Branch, Session, Term, Batch and valid Course context. Students and instructors are deliberately not copied; membership and teaching assignments must be confirmed for the new period.

## Institution Academic Calendar

The Institution Academic Calendar is an EduEdge isolation wrapper, not a replacement Academic Session master.

- Native `Academic Year` is shown as Academic Session or Training Year;
- Native `Academic Term` is shown as Term, Semester or Training Session;
- the Calendar binds one Institution to one native Academic Year and its dated native Terms.

The first enabled calendar becomes Current automatically. Existing enabled calendars without a Current row are repaired by an idempotent patch.

Academic Operations fails closed when:

- no enabled Institution calendar covers the selected date;
- the selected date is inside the Academic Session but outside all configured Terms;
- the requested Academic Year or Term does not belong to the selected Institution calendar.

Site-wide Education Settings are retained only as a legacy fallback where no EduEdge Institution context exists.

## Cascading filters

### Program catalogue

`Institution → Department/School Section → Program/Class → Progression Mode`

### Programme Offering

- Program Promotion: `Branch → Program/Class → Academic Session`;
- Level Progression: `Branch → Program → Academic Level → Academic Session → Academic Term`.

### Student Group

`Programme Offering → Program → Academic Level where applicable → Academic Session → Academic Term where applicable → Batch → Course → Students and Instructors`

Changing any parent clears invalid dependent values and student rows.

### Course Schedule

`Date → Student Group → Branch/Program/Level → Course → Instructor → Room`

The selected Student Group determines the Branch, Program and formal Level. Course, Instructor and Room are validated on the server.

### Assessment and report cards

Assessment Plan, Assessment Result and Result Publication derive formal Academic Level from the selected Student Group. Report cards display Level only where a Level is present.

## Migration and backward compatibility

The migration is idempotent and non-destructive.

- Legacy Academic Sections are preserved and mapped to native Departments;
- Primary/Secondary legacy Levels continue to map to native Programs/Classes;
- existing native document identities are not renamed;
- blank tertiary/training Levels are attached to a Program only when existing Offering or Student Group history resolves exactly one Program in the same Institution;
- ambiguous Levels remain preserved for administrator review;
- existing legacy Offerings, Student Groups and Course Schedules remain editable for non-context changes;
- once academic identity/context is deliberately changed, the corrected progression rules apply;
- submitted enrollment, attendance, assessment, fee, payroll and accounting documents are not rewritten.

## Required audit and QA

1. Run migration twice and confirm idempotency.
2. Confirm one reusable `JSS 1` Program per Institution and session-specific `JSS 1A` groups.
3. Confirm `JSS 1 → JSS 2` promotion creates a new target enrollment.
4. Confirm `BSc Agriculture · 200 Level → 300 Level` retains the Program and changes Level.
5. Confirm Program Promotion Offerings reject Level and Term.
6. Confirm Level Progression Offerings require valid Program-owned Level and Term.
7. Confirm Course queries honour Program, Level and curriculum period.
8. Confirm group rollover does not copy students or instructors.
9. Confirm source submitted enrollment is unchanged after progression.
10. Confirm target enrollment must be submitted before progression finalisation.
11. Confirm ambiguous legacy Levels are not guessed.
12. Confirm Primary/Secondary report cards omit a separate Level and tertiary report cards show it.
