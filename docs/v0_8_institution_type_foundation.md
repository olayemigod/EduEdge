# EduEdge V0.8 Institution Type and Terminology Foundation

## Decision

EduEdge owns a controlled registry of institution types and their user-facing academic terminology. Tenants select from EduEdge-provided types; they do not create or edit the registry.

Seeded types:

- Primary School (`PRIMARY`)
- Secondary School (`SECONDARY`)
- Tertiary Institution (`TERTIARY`)
- Training Centre (`TRAINING_CENTRE`)

## Company and branch model

ERPNext Company remains the legal and accounting institution owner. Its optional `eduedge_institution_type` field provides a Company-wide fallback. A blank Company value resolves to Secondary School.

`EduEdge School Branch` remains the operational campus and branch model. Every School Branch requires an Institution Type. Branch type overrides the Company fallback.

Resolution order:

1. Branch on the current document.
2. Explicitly selected School Branch.
3. Active user School Branch.
4. Company fallback.
5. Secondary School system fallback.

Existing School Branches are backfilled deterministically from their Company value or Secondary School. The migration does not guess from branch names.

## EdgeSuite UI

Institution configuration is available on the dedicated **Institution Structure** product page using the EdgeSuite UI shell. The page is linked from EduEdge Administration navigation.

The page provides:

- Company fallback selection;
- required branch institution-type assignment;
- seeded terminology preview;
- permission-aware Company and School Branch updates;
- immediate client terminology-context refresh where the changed record is active.

Native Company and School Branch forms remain administrative fallbacks. Product-owned setup and daily operations should consume the EdgeSuite UI terminology helper from the beginning.

## Stable internal contracts

Frappe DocType names, API field names, and database schemas remain canonical. Dynamic labels use stable keys such as:

- `academic_year`
- `academic_term`
- `programme`
- `programme_offering`
- `course`
- `student_batch`
- `student_group`
- `class_level`
- `class_session`
- `instructor`
- `room`

Client code uses `frappe.eduedge.term(key)` and server code uses `get_term(...)` or `get_effective_institution_context(...)`.

## Safety

- System-managed institution types cannot be manually created, changed, renamed, or deleted.
- Branch institution type changes are permission-controlled and audited; they change terminology context without mutating academic records.
- Company type remains optional and does not override an explicit Branch type.
- No submitted academic, accounting, or assessment document is modified.
- Existing branch and Company records are preserved.
