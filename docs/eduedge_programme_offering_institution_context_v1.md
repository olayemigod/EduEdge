# EduEdge Programme Offering Institution Context V1

## Goal

Make Programme Offering setup follow the accepted EduEdge academic context:

```text
Institution
→ Branch / Campus
→ Class / Programme
→ Academic Session
→ Term / Semester
→ Resolved Institution Calendar
```

The native `EduEdge Program Offering` DocType remains the source of truth. No duplicate Session, Term, Programme, Department, Branch, or Calendar record type is introduced.

## Route

```text
/app/eduedge-program-offerings
```

## Context behaviour

- The first page load may inherit the user's active School Branch and its Institution.
- After the user explicitly selects or clears filters, the active Branch is not silently reapplied.
- Selecting an Institution with no Branch selected gives an Institution-wide view across permitted Branches.
- Branch options are limited to permitted Branches belonging to the selected Institution.
- Programme and Department options are limited to the selected Institution.
- Academic Session options are limited to enabled Institution Academic Calendars.
- Academic Term options are limited to periods configured on the selected Institution Calendar and Session.
- Student Batch options remain permission-aware and Institution-scoped where the native DocType supports Institution ownership.

## Smart-form cascade

Changing Institution clears:

- Branch
- Programme
- Department
- Academic Session
- Academic Term
- Student Batch

Changing Branch clears:

- Programme
- Department
- Academic Session
- Academic Term
- Student Batch

Changing Academic Session clears Academic Term and reloads Calendar-backed periods.

Department remains derived from the selected native Program record and is not manually editable.

## Calendar visibility

The page does not store a redundant Calendar Link on Programme Offering. It resolves and displays:

- Institution Calendar name
- Academic Session
- Calendar start and end dates
- Current/configured status

Server validation still calls `assert_institution_calendar_context` during save.

## Permission and safety rules

- Institution, Programme, Academic Year, Academic Term, and Student Batch links are read-permission checked.
- Branch access is checked using EduEdge's permitted Branch logic.
- A Branch and submitted Institution mismatch is rejected server-side.
- Save remains POST-only.
- No `ignore_permissions`, direct `frappe.db.set_value`, or broad role grant is used.
- Existing Offering Code immutability and identity locking remain unchanged.
- Applicants, Student Groups, and submitted Program Enrollments continue to prevent identity reassignment.

## Deployment

The change updates Python, Vue, and contract-test files only.

```bash
bench build --app eduedge
bench --site eduedge-integration.local clear-cache
bench --site eduedge-integration.local clear-website-cache
```

No schema migration is required.

## Manual QA focus

1. Initial active Branch default.
2. Institution-wide view when Branch is blank.
3. Institution-to-Branch filtering.
4. Institution-to-Programme and Department filtering.
5. Session-to-Calendar resolution.
6. Session-to-Term filtering.
7. Parent-field cascade clearing.
8. Cross-Institution Branch rejection.
9. Permission-limited Branch visibility.
10. Identity locking on referenced Offerings.
