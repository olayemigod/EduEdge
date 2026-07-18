# EduEdge V0.7.1 — EdgeSuite UI Branch Governance and Accounting Center

## Business goal

V0.7.1 turns the V0.7 branch-access and accounting foundation into a guided administrative workflow. School administrators should be able to see whether every campus is covered, create or maintain staff assignments, identify incomplete accounting defaults, and activate enforcement without navigating several raw DocType lists.

## Route

`/app/eduedge-branch-governance`

## EdgeSuite UI requirements

The page uses the local standalone EdgeSuite UI runtime and must remain usable when CoreEdge is unreachable. It uses:

- `EdgeAppShell`
- `EdgePageLayout`
- `EdgePageHeader`
- `EdgeFilterBar`
- `EdgeDashboardLayout`
- `EdgeStatCard`
- `EdgeStatusBadge`
- `EdgeActionBar`
- `EdgeLoadingState`
- `EdgeErrorState`
- `EdgeEmptyState`

The loader must load and validate `edgeui.bundle.js` before the EduEdge page bundle and must show a controlled failure state if either runtime is unavailable.

## Access model

### View access

- System Manager
- EduEdge Administrator
- School Administrator
- Bursar

### Access-assignment and enforcement changes

Only:

- System Manager
- EduEdge Administrator

School Administrators and Bursars can inspect readiness. School Administrators may open School Branch records according to existing DocType permissions.

## Guided assignment workflow

The EdgeSuite page provides a Frappe dialog for creating or editing `EduEdge User Branch Access` records. The dialog includes:

- User
- Role in Branch
- Company
- School Branch / Campus
- HQ / All-Branch Access
- Default Branch
- Can Switch Branch
- Enabled
- Valid From
- Valid To

The School Branch Link query is filtered by selected Company and enabled status. Backend DocType validation remains authoritative for company matching, enabled users and branches, duplicate scope, default assignment uniqueness, and validity dates.

Assignments are disabled rather than deleted from the guided page so the audit trail remains available.

## Enforcement activation gate

The page reports four checks:

1. At least one enabled campus exists.
2. At least one active User Branch Access assignment exists.
3. Every enabled campus is covered by a direct assignment or company-scoped HQ assignment.
4. Every enabled campus has core accounting defaults.

Checks 1–3 block enforcement activation. Accounting readiness is recommended but does not block branch access because branch permissions and accounting configuration are separate safety concerns.

The server re-runs all blocking checks before saving `enable_user_branch_access_enforcement`. The frontend confirmation is not treated as the security boundary.

## Accounting setup boundary

The page shows branch-level accounting readiness and missing core defaults:

- Default Cost Center
- School Fees Income Account
- Default Receivable Account
- at least one Cash, Bank, or Payment Gateway account

The page opens the appropriate `EduEdge School Branch` record for configuration. It does not duplicate account selection or validation logic inside Vue.

The existing School Branch controller remains responsible for:

- Company matching
- enabled ledger Cost Centers
- enabled ledger Accounts
- Account root and Account Type checks
- Warehouse company and ledger checks

V0.7.1 does not create, submit, cancel, amend, or mutate Sales Invoices, Fees, Payment Entries, Journal Entries, Credit Notes, or submitted academic records.

## Navigation

The center is linked from:

- EduEdge product navigation
- EduEdge Home branch-governance panel
- EduEdge Home module cards
- EduEdge Setup Center header and recommended actions
- EduEdge Workspace shortcut

## Migration and backward compatibility

- No database patch is required beyond normal Page synchronization during `bench migrate`.
- Existing User Branch Access and School Branch records are reused.
- Existing enforcement setting is preserved.
- CoreEdge remains a remote platform service and is not imported locally.
- Native forms remain available for Data Import, audit review, and advanced administration.

## Required tests

### Static and contract

- Python compilation
- JSON validation
- JS entry validation
- every product page loads EdgeSuite UI before its product bundle
- root Vue page uses `EdgeAppShell`
- new route appears in product navigation
- backend activation requires complete campus coverage
- no accounting-document creation or permission bypass appears in governance services

### Frappe integration

- governance context for each authorised role
- permission denial for unauthorised roles
- direct branch assignment creation
- company-scoped HQ assignment creation
- duplicate-assignment rejection
- disabled, expired, future-dated, disabled-user, and disabled-branch status handling
- enabling and disabling assignments clears stale user context
- enforcement activation blocked with uncovered campuses
- enforcement activation succeeds after coverage is complete
- School Branch accounting gap detection

### Manual browser QA

1. Open the page from Home, Setup Center, product menu, and Workspace.
2. Filter by Company.
3. Create a one-campus assignment.
4. Create a multi-campus user and verify switching controls.
5. Create a company-scoped HQ assignment.
6. Confirm coverage cards and assignment counts refresh.
7. Disable and re-enable an assignment.
8. Verify uncovered campuses block enforcement.
9. Complete coverage and enable enforcement.
10. Log in as one-branch, no-switch, multi-branch, HQ, School Administrator, and Bursar users.
11. Open an incomplete branch and configure accounting defaults.
12. Confirm invalid account, Cost Center, and Warehouse combinations remain blocked by the School Branch controller.
13. Confirm controlled error rendering when EdgeSuite UI or the product bundle is unavailable.
