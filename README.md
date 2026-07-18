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

See `docs/architecture.md` and `docs/manual_qa_v0_1.md`.
