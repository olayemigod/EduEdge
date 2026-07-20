# EduEdge V0.3 — Branch Programme Offerings and Admissions

## Business goal

Ensure each school branch or campus can publish and enroll only the programmes it actually offers for a given academic year or term.

## Model

`EduEdge Program Offering` links:

- School Branch / Campus
- Program
- Academic Year
- optional Academic Term
- admission availability
- enrollment availability
- optional planning capacity
- optional application window

A blank Academic Term represents a year-wide offering. A term-specific offering applies only to that term, while year-wide offerings remain valid for every term in the year.

## Extended Education records

EduEdge adds `School Branch / Campus` to `Student Admission`.

Student Applicant and Program Enrollment already carry branch context from V0.2. Their selected programme is now checked against an active Program Offering.

## Behaviour

- Student Admission programme rows show only programmes offered by its branch and academic year.
- Student Applicants show only programmes offered by the selected branch, year, and term.
- Student Admission choices are filtered by branch, academic year, programme, and open dates.
- Program Enrollment shows only programmes enabled for enrollment.
- Backend validation rejects invalid combinations even when frontend filtering is bypassed.
- Academic Term must belong to Academic Year.
- Admission and application windows may start before the academic year; only date order is enforced.
- Duplicate Program Offerings for the same branch, programme, year, and term are rejected.
- Existing Frappe Education APIs and source files are not overridden.

## Migration

Migration creates the Student Admission branch Custom Field idempotently.

Existing Student Admissions receive a branch only when EduEdge has a deterministic default branch. Ambiguous records remain unassigned for manual review.

Program Offerings are not guessed or auto-created because programme availability is a business decision.

## Deferred QA

When the EduEdge site is reachable, validate:

1. Create a programme and academic year/term.
2. Create a Program Offering for one branch.
3. Confirm another branch cannot select that programme.
4. Confirm Student Admission programme rows are filtered.
5. Confirm Applicant programme and admission choices cascade.
6. Confirm Program Enrollment inherits the Student branch and filters programmes.
7. Confirm backend validation rejects an invalid programme submitted through API or Data Import.
8. Confirm branch User Permissions restrict Program Offering and Student Admission lists.
