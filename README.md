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

### V0.6

- EdgeSuite UI Report Cards and Progression page
- report cards generated only from Published Result Publications
- student course, grade, average, and attendance summaries
- PDF report cards with branch identity and optional letterhead
- class teacher and principal comments
- manual progression recommendation and approval
- no automatic enrollment, class movement, or submitted-result mutation

### V0.7

- explicit EduEdge User Branch Access assignments
- settings-gated backend branch enforcement with safe legacy fallback
- company-scoped HQ / All-Branch access
- active branch and authorised all-branch context on EduEdge Home
- branch-scoped native lists, Link queries, APIs, reports, and operational permissions
- expanded School Branch/Campus identity, contact, academic coverage, cost-centre, income, payment, adjustment, and stock defaults
- company-, ledger-, account-type-, and root-type validation for accounting defaults
- read-only branch accounting resolvers for future EduEdge and EdgePay transactions
- no accounting documents are created or modified by V0.7

### V0.7.1

- dedicated EdgeSuite UI Branch Governance and Accounting Center
- company-scoped branch coverage and assignment readiness dashboard
- guided User Branch Access creation and maintenance using permission-aware APIs
- server-blocked enforcement activation until every enabled campus is covered
- branch-by-branch accounting readiness and missing-default visibility
- direct navigation from EduEdge Home, Setup Center, product menu, and Workspace
- accounting configuration remains on the validated School Branch master
- no accounting documents or submitted academic records are created or mutated

### V0.7.2

- adoption of the EdgeSuite UI 0.2 professional product shell
- grouped business navigation for Overview, School Operations, Academics and Outcomes, and Administration
- semantic SVG icons instead of emoji and single-letter menu placeholders
- searchable global waffle product menu with descriptions, profile context, role hints, and active-route styling
- responsive persistent desktop sidebar and mobile off-canvas navigation
- EduEdge blue and green brand palette applied through shared product tokens
- consistent page padding, section gaps, card gaps, content width, focus states, and native Frappe sidebar styling
- menu visibility remains a usability layer; backend roles and branch permissions remain authoritative

## Development installation

```bash
cd ~/frappe-bench
bench get-app https://github.com/frappe/education --branch version-16
bench get-app https://github.com/olayemigod/processedge-edge-suite-ui.git --branch agent/fix-waffle-product-menu
bench get-app https://github.com/olayemigod/EduEdge.git --branch agent/eduedge-v0-1-foundation

bench --site eduedge.local install-app erpnext
bench --site eduedge.local install-app education
bench --site eduedge.local install-app edgesuite_ui
bench --site eduedge.local install-app eduedge

bench build --app edgesuite_ui --app eduedge
bench --site eduedge.local migrate
```

See the architecture and versioned implementation notes in `docs/`.
