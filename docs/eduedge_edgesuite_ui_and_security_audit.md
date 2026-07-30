# EduEdge EdgeSuite UI and Security Audit

## Scope

This audit covers the consolidated Academic Operations and CBT integration branch after the first clean-site smoke test. It focuses on custom EduEdge pages, quick create/edit dialogs, Institution/Branch context, and permission-sensitive CBT operations.

## EdgeSuite UI status

### Custom pages

The principal EduEdge custom Desk pages use the shared EdgeSuite shell, page layout, headers, filters, states, cards, and navigation. Native ERPNext/Education DocType forms remain available as advanced full forms.

### Resource Center quick editors

The following pages share the Resource Center and now use the EdgeSuite form-dialog surface for create and edit actions:

- School Branches
- Admissions
- Applicants
- Students
- Programmes
- Programme Offerings

The previous shared path opened a native `frappe.ui.Dialog`. The shared modal service now mounts `EdgeFormDialogFallback`, uses the EdgeSuite modal and link-field controls, preserves dependent-field clearing and option refresh, and keeps backend permission validation as the source of truth.

The School Branch editor retains the Company → Institution → Branch cascade. Selecting Company refreshes the permitted Institution options; the Branch controller still derives Institution Type and validates Company/Institution consistency.

### Intentional native surfaces

The following are not treated as EdgeSuite UI defects in this phase:

- Native Frappe full forms opened for advanced or complete DocType maintenance.
- Small confirmation prompts and one-field operational prompts where no product form workflow is required.
- Role Permission Manager, standard reports, and other framework administration screens.

These native surfaces must not replace the main product workflow, and any future custom multi-field popup should use the EdgeSuite form-dialog pattern.

## QA defects corrected

### Academic Foundation calendar failure

Academic calendar periods were converted into ordinary dictionaries and later accessed through attribute notation. The hardened endpoint consistently uses mapping access and remains Institution-wide; it does not require a Branch merely to load academic masters and calendars.

### Branch context guidance

Branch-scoped Academic Operations now resolves, in order:

1. An explicitly selected permitted Branch.
2. The current active permitted Branch.
3. The default permitted Branch for the active Institution.
4. The only permitted Branch when exactly one exists.

When no Branch exists, the user receives setup guidance. When several valid Branches exist without a selected/default Branch, the user receives a selection instruction. Backend branch validation remains mandatory.

### CBT Attempt Review loading

The Attempt Review page now loads the canonical EdgeSuite runtime asset and displays a visible timeout error instead of leaving an indefinite loading state when assets fail to register.

## Security and integrity review

### Corrected loopholes

- CBT Invigilation Branch filtering now fails closed: a supplied Branch is rejected unless it is in the user’s permitted Branch set, including when that set is empty.
- Attempt Review validates the selected Schedule and Branch explicitly before querying or resolving review records.
- Review resolution validates the Attempt’s School Branch before delegating to the existing locked, append-only review service.
- Public-examination review remains restricted to the central signed-result workflow.
- Resource Center saves continue to use allow-listed fields, DocType permission checks, platform access guards, and submitted-document mutation blocks.

### Preserved controls

- No submitted accounting or academic result document is mutated by these changes.
- CBT answer content and scoring keys are not added to invigilation or review list responses.
- Attempt lifecycle locking, pending-sync blocking, review evidence, and append-only audit records remain in place.
- Institution and Branch permission hooks remain the final record-level authority.

## Remaining QA

The disposable combined-QA site should still validate:

- School Branch create/edit in the EdgeSuite dialog, including Company/Institution cascades.
- Academic Foundation with current, gap, and empty calendar states.
- Academic Operations with no Branch, one Branch, default Branch, and multiple Branches.
- Attempt Review empty state, flagged queue, pending-sync block, accept, keep flagged, and disqualify paths.
- Cross-Institution and cross-Branch negative access.
- Offline answer reconciliation and concurrent Attempt locking.
- Draft/submitted Assessment Result behaviour and result-sync immutability.
