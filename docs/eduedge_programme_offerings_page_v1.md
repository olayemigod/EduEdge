# EduEdge Programme Offerings Page — Implementation Slice 4

## Business goal

Replace the generic Programme Offerings Resource Center view with a dedicated Branch-first operational page that makes delivery context, availability, capacity and identity safety clear before admissions, enrollment, classes and fees use the Offering.

## Implemented scope

### Dedicated EdgeSuite page

Route:

`/app/eduedge-program-offerings`

The page provides filters for:

- Branch / Campus;
- Programme / Class;
- Academic Year and Period;
- Academic Level;
- Study Mode;
- Delivery Mode;
- active status;
- admission availability;
- enrollment availability; and
- title, code or Programme search.

The default empty Branch selection resolves to the user's current active Branch. Other permitted Branches remain selectable.

### Operational status and capacity

Each visible Offering shows:

- Offering Title and immutable Offering Code;
- Branch and Programme;
- Academic Year and optional Period;
- Cohort / Batch;
- Study and Delivery Modes;
- start and end dates;
- occupied seats;
- configured capacity and seats remaining;
- application-window availability;
- enrollment availability; and
- derived operational status.

Operational status is derived at read time as:

- Active;
- Upcoming;
- Full;
- Closed; or
- Disabled.

No redundant operational-status field is added to the DocType.

Capacity uses the existing enrollment lifecycle truth. Only submitted Enrollments whose latest lifecycle status is Active or Suspended consume seats. A capacity of zero continues to mean no configured limit.

### Identity safety

The page indicates when an Offering identity is locked because it is already referenced by:

- a Student Applicant;
- a Student Group / Class; or
- a submitted Program Enrollment.

When locked, the quick editor disables Branch, Programme, Academic Level, Academic Year, Academic Period, Cohort, Study Mode and Delivery Mode. The backend controller remains authoritative and rejects crafted requests attempting to repurpose a used Offering.

### Smart quick editor

The editor is Branch-first:

1. Branch determines Institution.
2. Programme options are restricted to that Institution.
3. Academic Levels and Cohorts are restricted to that Institution.
4. Academic Period options refresh when Academic Year changes.
5. Changing Branch clears dependent Programme, Level and Cohort values.

The editor also supports dates, application window, availability controls, capacity and notes. The validated native full form remains available.

### Permissions and bounded reads

- Offering list reads use Frappe permission-aware queries.
- Branch access is checked on the backend.
- Lists are limited to 25 rows by default and 50 maximum.
- Option lists are bounded.
- Mutations use the EduEdge academic action guard.
- Save operations use normal document validation and do not bypass Offering identity, capacity, date or duplicate controls.

## Safety preserved

- No new DocType or schema patch is introduced.
- Programme Offering identity validation remains authoritative.
- Submitted Program Enrollments are not mutated.
- Enrollment lifecycle logs remain append-only.
- Submitted accounting documents are not changed.
- Capacity is not calculated from a naive enrollment count.
- No frontend-only rule is treated as sufficient for isolation or business correctness.

## Files changed

- `eduedge/api/programme_offerings.py`
- `eduedge/public/js/eduedge_programme_offerings/EduEdgeProgrammeOfferings.vue`
- `eduedge/public/js/eduedge_programme_offerings.bundle.js`
- `eduedge/eduedge/page/eduedge_program_offerings/eduedge_program_offerings.js`
- `eduedge/tests/test_programme_offerings_page_contract.py`
- `.github/workflows/ci.yml`
- `docs/eduedge_programme_offerings_page_v1.md`

## Focused validation

```bash
python -m compileall eduedge
python -m unittest eduedge.tests.test_programme_offerings_page_contract
python -m unittest eduedge.tests.test_academic_context_foundation_contract
node --check eduedge/public/js/eduedge_programme_offerings.bundle.js
node --check eduedge/eduedge/page/eduedge_program_offerings/eduedge_program_offerings.js
```

Local Frappe validation:

```bash
bench build --app eduedge
bench --site eduedge.local migrate
bench --site eduedge.local clear-cache
```

## Manual QA checklist

1. Open `/app/eduedge-program-offerings` as an academic administrator.
2. Confirm the page defaults to the current active Branch and permits switching to another authorised Branch.
3. Confirm changing Branch refreshes Programme, Level and Cohort options.
4. Confirm Programmes from another Institution do not appear.
5. Confirm Academic Period options refresh after Academic Year changes.
6. Create a year-wide Offering and a period-specific Offering.
7. Create Offerings with different Study and Delivery Modes and verify duplicate identity protection.
8. Confirm capacity zero displays as no configured limit.
9. Confirm Active and Suspended Enrollments consume capacity.
10. Withdraw or complete an Enrollment and confirm the seat is released.
11. Confirm an Offering becomes Full when occupied seats meet configured capacity.
12. Confirm Upcoming, Closed and Disabled statuses follow dates and the Active flag.
13. Confirm Admission Open follows the admission flag and application window.
14. Confirm Enrollment Open follows the enrollment flag.
15. Link an Applicant, Class/Student Group or submitted Enrollment and confirm identity-lock visibility.
16. Attempt to change a locked identity field through a crafted request and confirm backend validation blocks it.
17. Confirm capacity cannot be reduced below occupied seats.
18. Confirm the full native form remains available.
19. Test restricted roles and Branch permissions.
20. Confirm submitted academic and accounting documents remain unchanged.

## Combined QA next

The four Academic Operations page areas are now ready for combined local acceptance:

1. Academic Foundation;
2. Programmes;
3. Programme Offerings; and
4. Academic Operations for classes, schedules, rooms and attendance.
