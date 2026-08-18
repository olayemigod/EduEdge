# EduEdge Programmes Page — Implementation Slice 3

## Business goal

Replace the generic Programmes Resource Center presentation with a dedicated Institution-aware academic catalogue while retaining the standard Frappe Education `Program` DocType.

## Implemented scope

### Dedicated EdgeSuite page

Route:

`/app/eduedge-programs`

The page now provides:

- Institution filter;
- Academic Section filter;
- bounded Department search;
- Programme/Class search;
- permission-aware pagination;
- course-row counts;
- active Programme Offering counts;
- visible legacy records without Institution classification;
- quick create and edit; and
- direct access to the standard Program list and full form.

### Smart quick editor

The quick editor supports:

- Programme/Class name;
- abbreviation;
- Institution;
- Institution-filtered Academic Section; and
- optional Department.

Changing Institution clears an Academic Section that is no longer valid.

Course child rows, portal configuration, and advanced fields remain in the full Program form. The quick editor does not clear or rebuild the `Program Course` child table.

### Permission and isolation controls

- Program list reads use normal Frappe permission-aware queries.
- Institution and Academic Section records are checked on the backend.
- An Academic Section must belong to the selected Institution.
- Department suggestions are bounded to 30 permission-aware results.
- Programme pages are bounded to 50 records per request, with a default of 25.
- Programme mutations use the existing CoreEdge/EduEdge academic action guard.

### Context and terminology

The page uses the active Institution context for visible terminology:

- Primary and Secondary schools can display Class/Classes.
- Tertiary Institutions display Programme/Programmes.
- Training Centres display Programme/Programmes.
- Academic Section labels continue to follow the selected Institution Type.

Internal DocType, API, and database field identities remain unchanged.

## Safety preserved

- The standard Frappe Education Program DocType is retained.
- Program Course rows are not rewritten by quick edit.
- Existing Institution ownership validation remains authoritative.
- No submitted academic or accounting record is changed.
- No schema or migration patch is required.
- No records are loaded without bounded page or option limits.

## Files changed

- `eduedge/api/programmes.py`
- `eduedge/public/js/eduedge_programmes/EduEdgeProgrammes.vue`
- `eduedge/public/js/eduedge_programmes.bundle.js`
- `eduedge/eduedge/page/eduedge_programs/eduedge_programs.js`
- `eduedge/tests/test_programmes_page_contract.py`
- `.github/workflows/ci.yml`
- `docs/eduedge_programmes_page_v1.md`

## Focused validation

```bash
python -m compileall eduedge
python -m unittest eduedge.tests.test_programmes_page_contract
python -m unittest eduedge.tests.test_academic_context_foundation_contract
node --check eduedge/public/js/eduedge_programmes.bundle.js
node --check eduedge/eduedge/page/eduedge_programs/eduedge_programs.js
```

Local Frappe validation:

```bash
bench build --app eduedge
bench --site eduedge.local migrate
bench --site eduedge.local clear-cache
```

## Manual QA checklist

1. Open `/app/eduedge-programs` as an academic administrator.
2. Confirm visible terminology matches the active Institution Type.
3. Filter by Institution and confirm only permitted Programmes/Classes appear.
4. Filter by Academic Section and confirm it belongs to the selected Institution.
5. Search by name, abbreviation, and Department.
6. Confirm only 25 records load by default and pagination works.
7. Confirm course-row and active-Offering counts match source records.
8. Create a Programme/Class using the quick editor.
9. Change Institution and confirm an invalid Academic Section clears.
10. Edit Programme name, abbreviation, Section, or Department.
11. Confirm existing Program Course rows remain unchanged.
12. Open the full form and maintain Course rows normally.
13. Test a read-only Teacher and confirm quick-edit controls are unavailable.
14. Test a user with access to multiple Institutions and confirm no cross-Institution leakage.
15. Confirm no submitted academic or accounting document changes.

## Next slice

Replace the generic Programme Offerings page with a dedicated Branch-first capacity and operational-status page, then run the combined academic workflow QA.
