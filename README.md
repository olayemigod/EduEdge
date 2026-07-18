# EduEdge

EduEdge is ProcessEdge Solutions Limited's education management product for Nigerian and African schools.

It is built on:

- Frappe v16
- ERPNext v16
- Frappe Education v16
- the standalone EdgeSuite UI runtime

CoreEdge is a central platform service and is **not** installed as a dependency of EduEdge.

## UI foundation

EdgeSuite UI is the default foundation for EduEdge-owned homes, dashboards, wizards, dialogs, and operational workflow pages.

Native Frappe forms remain available for upgrade-safe master-data and administrative work, while daily operational experiences are implemented inside the EduEdge product shell.

## Implemented foundation

### V0.1

- Frappe application and dependency contract
- standalone and remote platform modes
- CoreEdge HTTP adapter boundary without importing CoreEdge
- EduEdge School Branch/Campus management
- branch-aware user context
- EduEdge Settings and Setup Center
- initial roles, workspace, tests, and documentation

### V0.2

- branch context on Student Applicant, Student, and Program Enrollment
- backend branch propagation and validation
- branch-scoped lists, Link queries, and Guardian visibility
- safe migration backfill without modifying Frappe Education source

### V0.3

- EduEdge Program Offering by branch, programme, academic year, and optional term
- branch-aware Student Admission
- programme filtering for admissions and enrollment
- backend enforcement of branch/programme/year/term combinations
- Setup Center programme-offering readiness

### V0.4

- EdgeSuite UI Academic Operations page
- branch-aware Student Groups, Rooms, Course Schedules, and Student Attendance
- many-to-many Instructor Branch Assignments
- schedule and instructor/room filtering
- safe attendance draft and submission workflow
- immutable submitted-attendance protection

### V0.5

- branch-aware Assessment Plan and Assessment Result records
- smart examiner, supervisor, room, class, and student filtering
- EdgeSuite UI Assessment Operations page
- result completeness calculation by class and assessment group
- approval, rejection, and publication workflow
- append-only result publication audit logs
- report-card readiness blocked until approved results are published

## Development installation

```bash
cd ~/frappe-bench
bench get-app https://github.com/frappe/education --branch version-16
bench get-app https://github.com/olayemigod/processedge-edge-suite-ui.git
bench get-app https://github.com/olayemigod/EduEdge.git --branch agent/eduedge-v0-1-foundation

bench --site eduedge.local install-app erpnext
bench --site eduedge.local install-app education
bench --site eduedge.local install-app edgesuite_ui
bench --site eduedge.local install-app eduedge

bench build --app edgesuite_ui --app eduedge
bench --site eduedge.local migrate
```

See the architecture and versioned implementation notes in `docs/`.
