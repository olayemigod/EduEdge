# EduEdge EdgeSuite UI foundation

## Decision

EdgeSuite UI is the visual and runtime foundation for every **product-owned EduEdge page, dashboard, wizard, operational dialog, and workflow screen** from the beginning.

The EdgeSuite UI Frappe app is installed locally on the EduEdge site. Its JS and CSS are available even when CoreEdge is unreachable.

## Product shell

The EduEdge launcher opens `eduedge-home`, not the native Workspace. EduEdge Home uses:

- `EdgeAppShell`;
- `EdgePageLayout`;
- `EdgePageHeader`;
- `EdgeDashboardLayout`;
- `EdgeStatCard`;
- `EdgeActionBar`;
- `EdgeStatusBadge`;
- EdgeSuite loading and error states.

The shell exposes branch, company, and user context and provides product navigation.

## Native Frappe forms

Standard Frappe Education DocType forms remain native Frappe forms during the foundation phase. This protects upgrade compatibility, permissions, workflow behavior, Data Import, and standard ERPNext links.

This is not permission to create inconsistent product UI. The rule is:

- setup/master data may continue to use smart native forms;
- product-owned operational experiences must use EdgeSuite UI;
- native forms must still use cascading queries, backend validation, branch context, and clear product wording;
- high-frequency workflows should later receive EdgeSuite UI operational pages instead of forcing users through raw administrative forms.

Rewriting every standard DocType form as a custom Vue application is out of scope unless a workflow clearly needs it.

## Loading contract

Every product-owned Frappe Page must:

1. load `edgeui.bundle.js`;
2. validate `window.EdgeSuiteUI.createEdgeApp` and required components;
3. load its EduEdge product bundle;
4. mount through the EdgeSuite UI runtime;
5. show a controlled error state if the runtime or product bundle is unavailable.

## Enforcement

Repository contract tests must fail when:

- the launcher points to the native workspace instead of EduEdge Home;
- a product Page bundle loads before EdgeSuite UI;
- an EduEdge root Vue page does not use `EdgeAppShell`;
- product code imports EdgeSuite UI or CoreEdge source files directly.
