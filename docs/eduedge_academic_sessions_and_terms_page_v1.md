# EduEdge Academic Sessions and Terms Page V1

## Business goal

Provide one EdgeSuite setup page for configuring the native Frappe Education Academic Year and Academic Term masters before an Institution Academic Calendar is created.

## Route

`/app/eduedge-academic-sessions`

The route appears under **Academic Setup** between Academic Foundation and Programmes.

## Source-of-truth model

EduEdge does not introduce duplicate Session or Term DocTypes.

- Academic Session uses native `Academic Year`.
- Academic Term/Semester uses native `Academic Term`.
- Institution-specific mapping remains `EduEdge Institution Academic Calendar`.

The setup sequence is:

1. Create the shared Academic Session.
2. Add its Terms/Semesters.
3. Open Academic Foundation and create the Institution Calendar.

## Smart form behaviour

- Selecting a Session refreshes the Term list for that Session only.
- Creating a Session selects it automatically.
- New Terms inherit the selected Session.
- Existing Session and Term identities are read-only in quick edit.
- Term dates must remain inside the selected Session.
- Terms in one Session cannot overlap.
- Session date changes cannot exclude existing Terms.
- Advanced native forms remain available for exceptional maintenance.

## Security and safety

- Reads use permission-aware `frappe.get_list` queries.
- Mutations are POST-only whitelisted methods.
- Session and Term create/write permissions are checked separately.
- CoreEdge/EduEdge academic access is enforced before reads or writes.
- No `ignore_permissions` path is used.
- No simplified delete action is exposed.
- Institution calendars and other operational records are not mutated by this page.

## Files

- `eduedge/api/academic_sessions.py`
- `eduedge/public/js/eduedge_academic_sessions.bundle.js`
- `eduedge/public/js/eduedge_academic_sessions/EduEdgeAcademicSessions.vue`
- `eduedge/eduedge/page/eduedge_academic_sessions/`
- `eduedge/public/js/eduedge_ui/navigation.js`
- `eduedge/tests/test_academic_sessions_page_contract.py`

## Manual QA

1. Confirm the new route appears in sidebar and product menu.
2. Create a Session and verify it becomes selected.
3. Add multiple non-overlapping Terms.
4. Confirm Terms from another Session do not appear in the selected list.
5. Confirm out-of-range and overlapping dates are blocked.
6. Confirm identity fields are locked during quick edit.
7. Confirm advanced native forms open correctly.
8. Confirm Academic Foundation can create an Institution Calendar from the configured Session and Terms.
