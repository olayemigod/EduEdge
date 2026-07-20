# EduEdge V0.4 — Academic Operations and Attendance

## Business goal

Give Nigerian and African schools a branch-safe daily operations screen for classes, schedules, instructors, rooms, and attendance.

## EdgeSuite UI experience

`Academic Operations` is an EduEdge-owned EdgeSuite UI page. It provides:

- School Branch / Campus context;
- date and class filters;
- class and instructor counts;
- daily Course Schedule cards;
- a Student Group attendance register;
- draft and submitted attendance actions;
- clear submitted-record locking.

The page loads the locally installed EdgeSuite UI runtime before the EduEdge bundle.

## Branch model

EduEdge adds School Branch / Campus context to:

- Student Group;
- Room;
- Course Schedule;
- Student Attendance.

Course Schedule inherits its branch from Student Group. Student Attendance inherits it from Course Schedule or Student Group and verifies that the Student belongs to the same branch.

## Instructor model

An Instructor can serve more than one campus. EduEdge therefore does not force one branch field onto Instructor.

`EduEdge Instructor Branch Assignment` stores the many-to-many relationship, optional validity dates, and primary-branch indicator.

## Attendance safety

Student Attendance is submittable. Submitted attendance is never silently mutated.

The register:

- reuses matching drafts;
- creates missing drafts;
- may submit drafts in one action;
- treats matching submitted records as unchanged;
- blocks changes that conflict with submitted records;
- requires cancellation or amendment before a submitted status can change.

## Migration

Migration creates Custom Fields idempotently and backfills only deterministic branch values:

- Student Group from unanimous linked Student branches, otherwise the deterministic default;
- Course Schedule from Student Group;
- Student Attendance from Course Schedule, Student Group, or Student;
- Room only from the deterministic default branch.

Instructor assignments are not guessed.

## Deferred live QA

1. Create instructors and branch assignments.
2. Create branch-specific rooms.
3. Create a Student Group and verify Student branch validation.
4. Create a Course Schedule and confirm instructor/room filtering.
5. Open Academic Operations through EduEdge Home.
6. Load a class register and save drafts.
7. Submit attendance and confirm the rows become locked.
8. Attempt a conflicting submitted change and confirm it is blocked.
9. Switch branches and confirm counts, classes, schedules, and attendance change safely.
