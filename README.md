# EduEdge

EduEdge is ProcessEdge Solutions Limited's education management product for Nigerian and African schools.

It is built on:

- Frappe v16
- ERPNext v16
- Frappe Education v16
- the standalone EdgeSuite UI runtime

CoreEdge is a central platform service and is **not** installed as a dependency of EduEdge.

## V0.1 foundation

The first implementation establishes:

- the EduEdge Frappe application contract;
- standalone and remote platform modes;
- a CoreEdge HTTP adapter boundary without importing CoreEdge;
- EduEdge School Branch/Campus management;
- branch-aware user context;
- EduEdge Settings;
- setup-readiness APIs;
- an EdgeSuite UI-based Setup Center;
- initial roles, workspace, tests, and documentation.

## V0.2 education branch context

The next implementation slice extends the upstream Frappe Education workflow without modifying its source files:

- Student Applicant stores the responsible branch/campus;
- Student inherits the applicant or active branch;
- Program Enrollment inherits and validates the Student branch;
- operational list and document access are branch-aware;
- Guardian visibility is derived from linked Students, allowing one Guardian to remain linked to children in different campuses;
- existing records are backfilled only when the branch is deterministic.

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

See `docs/architecture.md`, `docs/manual_qa_v0_1.md`, and `docs/eduedge_v0_2_branch_context.md`.
