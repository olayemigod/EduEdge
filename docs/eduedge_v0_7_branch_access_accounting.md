# EduEdge V0.7 — Branch Access and Accounting Governance

## Business goal

V0.7 completes the branch-governance foundation required before secure CBT, payments, pickup operations, transport, portals, and School Intelligence are expanded.

It provides explicit user-to-campus access, a controlled active-branch context, authorised company-scoped HQ visibility, and validated accounting defaults that future EduEdge transactions can resolve without bypassing ERPNext accounting rules.

## Product and platform boundary

- EduEdge owns education-specific School Branch/Campus records and operational user branch access.
- CoreEdge remains the central shared tenant, activation, communication, wallet, branding, and platform-governance service.
- CoreEdge is not installed inside the EduEdge site.
- `platform_branch_id` remains a lightweight reference for future CoreEdge branch-context mapping.
- ERPNext remains the accounting truth.
- EdgePay may later route and verify payments, while EduEdge resolves the education purpose, branch, company, account, and cost centre.

## User Branch Access

`EduEdge User Branch Access` records contain:

- User
- Role in Branch
- Company
- School Branch/Campus for branch-specific access
- HQ / All-Branch Access for company-wide visibility
- Default Branch
- Can Switch Branch
- Enabled status
- Valid From and Valid To

Only System Manager and EduEdge Administrator can create or change these records.

### HQ access

HQ access is company-scoped. It does not grant unrestricted access across unrelated companies or tenants.

An authorised HQ user can select an **All Branches** context for one permitted Company. EduEdge Home then aggregates only branches the user is authorised to access within that Company.

## Safe activation sequence

`Enforce User Branch Access` is disabled by default for backward compatibility.

Recommended rollout:

1. Migrate the site.
2. Create assignments for every operational staff user.
3. Configure one default branch where appropriate.
4. Confirm switching permissions.
5. Configure HQ access only for approved central users.
6. Test using non-administrator accounts.
7. Enable `Enforce User Branch Access` in EduEdge Settings.
8. Re-test native lists, Link fields, dashboards, APIs, reports, and branch switching.

When enforcement is enabled, a normal operational user without an active assignment receives no EduEdge branch access.

System Manager and EduEdge Administrator retain governance access so administrators cannot accidentally lock themselves out while repairing assignments.

## Active Branch Switcher

The active context supports:

- one permitted branch applied automatically;
- a configured default assignment;
- controlled switching among authorised branches;
- company-scoped All Branches view for approved HQ users;
- stale branch defaults cleared after access is removed, disabled, or expired.

The context is consumed by EduEdge Home, branch Link queries, backend validation, permission conditions, and future CBT, pickup, transport, payment, notification, and intelligence workflows.

## Expanded School Branch/Campus

V0.7 adds:

### Identity and contact

- School / Company
- Branch Name and Code
- expanded Branch Type
- Main Branch / Campus
- Default Operational Branch
- Contact Person
- Phone
- Email
- Address
- Academic Levels Offered

### Cost centre defaults

- Default Cost Center
- Default Income Cost Center
- Default Expense Cost Center

### Income accounts

- School Fees
- CBT / Examination Fees
- Admission / Registration
- Transport
- Hostel / Boarding
- Books and Learning Materials
- Uniform Sales
- Other Income

### Receivable and payment accounts

- Default Receivable
- Default Cash
- Default Bank
- Default Payment Gateway / Mobile Money

### Discounts and adjustments

- Discount
- Scholarship / Bursary
- Write-off

### Optional stock defaults

- Warehouse
- Inventory
- Cost of Goods Sold
- Stock Adjustment

## Accounting safety

The School Branch validator checks that selected Cost Centers, Accounts, and Warehouses:

- belong to the branch Company;
- are enabled;
- are ledger records rather than groups;
- match the required Account root or account type where applicable.

`eduedge.services.branch_accounting` only resolves configuration. V0.7 does not create, submit, cancel, amend, or mutate:

- Sales Invoices
- Fees
- Payment Entries
- Journal Entries
- Credit Notes
- submitted accounting records

Future transaction features must create or link proper ERPNext documents and use drafts, cancellation/amendment, credit notes, write-offs, or payment allocation for corrections.

## Setup readiness

Setup Center now reports:

- active User Branch Access count;
- whether enforcement is enabled;
- enabled branches missing core accounting defaults;
- a blocker when enforcement is active but no assignments exist;
- guided actions to configure assignments, enable enforcement, and complete accounting defaults.

## Backward compatibility

- Existing branches retain their previous fields and values.
- Existing active branch defaults remain valid when still authorised.
- Enforcement remains off after migration until an administrator enables it.
- No upstream ERPNext or Frappe Education source files are changed.
- No CoreEdge imports are added.
- No accounting documents are created or mutated.

## Required runtime QA

1. Build EdgeSuite UI and EduEdge assets.
2. Migrate `eduedge.local`.
3. Run the full EduEdge test suite.
4. Confirm a one-branch user receives the branch automatically.
5. Confirm a multi-branch user with switching enabled can switch only among assigned branches.
6. Confirm a user with switching disabled cannot activate a different branch.
7. Confirm a company-scoped HQ user can select All Branches for that Company only.
8. Confirm expired and disabled assignments remove access and clear stale context.
9. Confirm a user without assignments receives no branch records after enforcement is enabled.
10. Confirm Student, Applicant, Student Group, Attendance, Assessment, Result, and Report Card lists remain branch-scoped.
11. Confirm invalid Company, Cost Center, Account, Account Type, and Warehouse combinations are blocked.
12. Confirm branch accounting APIs are restricted to authorised administrative/accounting roles.
13. Confirm no accounting or submitted academic document changes occur during branch resolution.
