# EduEdge Academic Operations Pages — Implementation Slice 1

## Business goal

Strengthen the existing Academic Operations page into the daily control centre for classes, schedules, rooms, instructors, and attendance while preserving Frappe Education records and submitted-document safety.

This slice does not introduce new DocTypes or mutate submitted academic or accounting documents.

## Implemented scope

### Academic context

The page now displays the selected:

- Institution;
- Branch / Campus;
- Academic Year;
- Academic Period; and
- source of the resolved academic calendar context.

Where a selected date is inside an Institution Academic Calendar but outside every configured period, EduEdge displays a calendar-gap warning and intentionally leaves the Academic Period blank. It does not inherit an unrelated site-wide Academic Term.

### Daily readiness metrics

The Academic Operations context now provides:

- active Student Group or Class count;
- enabled Instructor Branch Assignment count;
- schedules for the selected date;
- rooms used;
- sessions without a Room;
- complete attendance registers;
- partially completed attendance registers; and
- scheduled groups with no submitted attendance.

### Attendance coverage

Attendance readiness is calculated only from:

- the selected Branch;
- the selected date;
- scheduled Student Groups; and
- submitted Student Attendance records.

Each scheduled Student Group returns:

- expected active learners;
- submitted records;
- Present, Absent, and Leave counts;
- missing records;
- whether attendance has started; and
- whether the register is complete.

The existing draft attendance workflow remains unchanged. Submitted attendance remains immutable.

### Room usage

Room usage is summarised from the selected date's Course Schedules. The page shows:

- each allocated Room;
- number of sessions;
- first start and last end time; and
- a separate Unassigned entry for schedules without a Room.

### User experience

The EdgeSuite page now includes:

- Institution-aware terminology;
- academic calendar context;
- schedule selection details;
- attendance-readiness cards;
- room-usage cards;
- calendar-gap warning;
- quick navigation to Academic Foundation, Programmes, Programme Offerings, Course Schedule, Rooms, and Instructor Assignments; and
- responsive layouts for smaller screens.

## Safety preserved

- Standard Frappe Education DocTypes are not renamed or duplicated.
- Branch access remains server-authoritative.
- Attendance coverage uses submitted records only.
- Draft attendance remains editable.
- Submitted attendance is not changed or recreated.
- No accounting records are created or modified.
- No migration or schema patch is required.
- Existing Institution Academic Calendar resolution remains authoritative.

## Files changed

- `eduedge/api/academic_operations_safe.py`
- `eduedge/public/js/eduedge_academic_operations/EduEdgeAcademicOperations.vue`
- `eduedge/tests/test_academic_operations_contract.py`

## Focused validation required

Automated validation should include:

```bash
python -m compileall eduedge
python -m unittest eduedge.tests.test_academic_operations_contract
node --check eduedge/eduedge/page/eduedge_academic_operations/eduedge_academic_operations.js
node --check eduedge/public/js/eduedge_academic_operations.bundle.js
```

Local Frappe validation should include:

```bash
bench build --app eduedge
bench --site eduedge.local migrate
bench --site eduedge.local clear-cache
```

## Manual QA checklist

1. Open `/app/eduedge-academic-operations` as an authorised academic user.
2. Confirm Institution and Branch / Campus match the active context.
3. Change Branch and confirm all counts and lists refresh.
4. Select a date inside a configured academic period and confirm the correct year and period.
5. Select a date inside a calendar gap and confirm no unrelated global term appears.
6. Confirm year-wide Student Groups remain visible during a configured period.
7. Confirm schedule cards show Course, Student Group, Instructor, time, and Room.
8. Confirm schedules without Rooms appear in the unassigned-room count.
9. Confirm attendance readiness distinguishes Complete, Partial, and Not Started registers.
10. Open a scheduled register and save draft attendance.
11. Submit attendance and confirm the readiness metrics refresh.
12. Attempt to change submitted attendance and confirm it remains blocked.
13. Test Primary, Secondary, Tertiary, and Training Centre terminology.
14. Test a restricted Teacher against permitted and non-permitted Branches.
15. Confirm no submitted accounting or academic document outside attendance is changed.

## Next implementation slices

1. Complete Academic Foundation calendar and progression readiness.
2. Replace the generic Programmes resource page with a dedicated Institution-aware page.
3. Replace the generic Programme Offerings resource page with a dedicated capacity and operational-status page.
4. Run combined academic workflow QA after all four page areas are complete.
