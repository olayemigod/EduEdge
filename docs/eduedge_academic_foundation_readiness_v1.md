# EduEdge Academic Foundation Readiness — Implementation Slice 2

## Business goal

Complete the Academic Foundation page as the setup and readiness centre for Institution-owned academic structure, progression, and calendars.

This slice improves visibility and guidance. It does not introduce a parallel calendar editor, new DocTypes, or submitted-document mutations.

## Implemented scope

### Institution readiness

For each permitted Institution, the API now evaluates:

- enabled Academic Sections;
- enabled Academic Levels;
- enabled Institution Academic Calendars;
- existence of an enabled current calendar;
- whether the current calendar has Academic Periods;
- whether today falls into an intentional calendar gap;
- enabled Levels without a Section where Sections exist; and
- progression links pointing to missing or disabled Levels.

The page distinguishes required setup gaps from items that need review.

### Academic calendar visibility

The page now shows:

- every permitted calendar for the selected Institution;
- Academic Year;
- start and end dates;
- enabled and current status;
- configured Academic Periods;
- current period;
- result-publication date data returned by the API; and
- a clear warning when today falls inside a calendar but outside all configured periods.

Calendar creation and editing continue through the validated native `EduEdge Institution Academic Calendar` form. This preserves child-table validation, period-overlap protection, current-calendar switching, and Institution/Academic Year immutability.

### Progression pathways

Enabled Academic Levels are organised into visible progression pathways.

Each pathway shows:

- Section or pathway heading;
- ordered Level name and code;
- Next Level relationships; and
- missing or disabled progression targets.

The existing controller remains authoritative for cycle prevention and same-Institution validation.

### Smart structure editing

The existing Section and Level quick editors remain available.

The page API now returns descriptions so editing a record no longer clears its existing description from the quick editor.

Dependent Section and Next Level choices remain restricted to the selected Institution.

## Safety preserved

- No standard Frappe Education DocType is renamed or duplicated.
- No new schema or migration patch is required.
- Calendar validation remains in the native DocType controller.
- Progression-cycle prevention remains authoritative on the backend.
- No submitted academic or accounting record is changed.
- No global Academic Term is substituted into an Institution calendar gap.
- API reads remain permission-aware.
- Calendar editing requires normal Frappe create/write permission.

## Files changed

- `eduedge/api/academic_foundation.py`
- `eduedge/public/js/eduedge_academic_foundation/EduEdgeAcademicFoundation.vue`
- `eduedge/tests/test_academic_foundation_readiness_contract.py`
- `docs/eduedge_academic_foundation_readiness_v1.md`

## Focused validation

```bash
python -m compileall eduedge
python -m unittest eduedge.tests.test_academic_foundation_readiness_contract
python -m unittest eduedge.tests.test_academic_context_foundation_contract
node --check eduedge/eduedge/page/eduedge_academic_foundation/eduedge_academic_foundation.js
node --check eduedge/public/js/eduedge_academic_foundation.bundle.js
```

Local Frappe validation:

```bash
bench build --app eduedge
bench --site eduedge.local migrate
bench --site eduedge.local clear-cache
```

## Manual QA checklist

1. Open `/app/eduedge-academic-foundation`.
2. Select each configured Institution.
3. Confirm enabled Section, Level, and calendar totals.
4. Confirm an Institution with no current calendar shows a required warning.
5. Confirm a current calendar without periods shows a required warning.
6. Confirm a date gap inside the current calendar is shown without a global term fallback.
7. Confirm every period displays its dates and the current period is highlighted.
8. Create a calendar and confirm the native form opens with the selected Institution.
9. Open an existing calendar and verify normal Frappe permissions apply.
10. Confirm progression pathways follow configured Next Level links.
11. Disable a target Level and confirm the progression gap warning appears.
12. Attempt to create a progression cycle and confirm backend validation blocks it.
13. Edit a Section or Level and confirm its description remains populated.
14. Test Primary, Secondary, Tertiary, and Training Centre terminology.
15. Test a restricted Teacher and confirm the page is read-only where appropriate.
16. Confirm no submitted academic or accounting record changes.

## Next slices

1. Replace the generic Programmes resource page with a dedicated Institution-aware page.
2. Replace the generic Programme Offerings resource page with a dedicated capacity and operational-status page.
3. Run combined academic workflow QA after all four page areas are complete.
