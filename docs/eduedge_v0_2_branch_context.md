# EduEdge V0.2 — Education Branch Context

## Purpose

This slice makes the upstream Frappe Education admission and enrollment flow branch-aware without modifying Education source files.

## Records extended

- Student Applicant stores the branch handling the application.
- Student inherits the applicant branch or the active/default EduEdge branch.
- Program Enrollment inherits and must match the Student branch.
- Guardian does not receive a single branch field because one guardian may have students in different campuses. Guardian visibility is derived from linked Students.

## Safety rules

- Branches must be enabled.
- Authenticated operational users may only select branches returned through permission-aware EduEdge branch services.
- Submitted Program Enrollments prevent unsafe Student branch changes.
- Existing records are backfilled only when the value is deterministic: from linked records, an explicit default branch, or a single enabled branch.
- No upstream Education DocType JSON or controller is changed.
- The standard `education.education.api.enroll_student` method is not overridden.

## Manual QA deferred

When `eduedge.local` becomes reachable, validate:

1. New Student Applicant defaults to the active branch.
2. Applicant enrollment creates a Student with the same branch.
3. Program Enrollment receives the Student branch and keeps it read-only.
4. A user restricted to Branch A cannot select or list Branch B records.
5. A Guardian linked to students in two campuses remains visible from either permitted campus.
6. A Student with a submitted enrollment cannot be moved to a conflicting branch.
