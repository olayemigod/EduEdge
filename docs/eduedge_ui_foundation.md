# EduEdge EdgeSuite UI foundation

## Decision

EdgeSuite UI is the visual and runtime foundation for every **product-owned EduEdge page, dashboard, wizard, operational dialog, and workflow screen** from the beginning.

The EdgeSuite UI Frappe app is installed locally on the EduEdge site. Its JS and CSS are available even when CoreEdge is unreachable.

## Professional product design

EduEdge adopts the EdgeSuite UI 0.2 professional shell rather than maintaining a separate product-local design system.

The required design qualities are:

- simple, clean, and memorable rather than visually crowded;
- close to the strongest VetEdge operational design patterns while retaining EduEdge identity;
- consistent page padding, section gaps, card gaps, maximum content width, radius, and shadows;
- responsive layouts aligned with Frappe and common Bootstrap breakpoints;
- EduEdge blue `#1f6feb` with green `#22a06b` as a restrained accent;
- SVG icons that inherit active, hover, and muted colours through `currentColor`;
- clear hover, active, disabled, loading, empty, and error states;
- mobile off-canvas navigation rather than a compressed unusable desktop sidebar.

Do not use emoji, single-letter placeholders, or raw icon names as visible menu icons.

## Product shell

The EduEdge launcher opens `eduedge-home`, not the native Workspace. EduEdge product pages use:

- `EdgeAppShell`;
- `EdgeIcon`;
- `EdgePageLayout`;
- `EdgePageHeader`;
- `EdgeDashboardLayout`;
- `EdgeStatCard`;
- `EdgeActionBar`;
- `EdgeFilterBar`;
- `EdgeStatusBadge`;
- EdgeSuite loading, empty, and error states.

The shell exposes branch, company, and user context and provides grouped product navigation.

## Menu structure

The persistent EdgeSuite sidebar and the global waffle product menu follow the same business hierarchy:

1. **Overview** — EduEdge Home.
2. **School Operations** — Academic Operations, Admissions, Applicants, and Students.
3. **Academics and Outcomes** — Program Offerings, Assessments and Results, and Report Cards.
4. **Administration** — Branch Governance, School Branches, User Branch Access, and Setup Center.

Sidebar entries must provide:

- a clear label;
- a semantic SVG icon name;
- a short description where space permits;
- the business section;
- a permission-safe destination.

The product menu additionally supports search keywords, roles, badges, profile context, section descriptions, and active-route highlighting.

The EduEdge bundle registers the global menu through `window.EdgeSuiteUI.registerProductMenu`. Menu role visibility improves usability but does not replace Frappe roles, backend permission conditions, or API checks.

## Native Frappe sidebar

The shared professional stylesheet also applies the product menu visual language to the native EduEdge Workspace sidebar:

- compact section headings;
- consistent padding and item height;
- rounded hover and active states;
- SVG icon tiles;
- brand-coloured active indicator;
- visible keyboard focus;
- responsive text wrapping where required.

Native Frappe behaviour and permission handling remain intact.

## Native Frappe forms

Standard Frappe Education DocType forms remain native Frappe forms during the foundation phase. This protects upgrade compatibility, permissions, workflow behavior, Data Import, and standard ERPNext links.

This is not permission to create inconsistent product UI. The rule is:

- setup/master data may continue to use smart native forms;
- product-owned operational experiences must use EdgeSuite UI;
- native forms must still use cascading queries, backend validation, branch context, clear product wording, and the shared spacing/sidebar layer;
- high-frequency workflows should later receive EdgeSuite UI operational pages instead of forcing users through raw administrative forms.

Rewriting every standard DocType form as a custom Vue application is out of scope unless a workflow clearly needs it.

## Loading contract

Every product-owned Frappe Page must:

1. load `edgeui.bundle.js`;
2. validate `window.EdgeSuiteUI.createEdgeApp` and required components;
3. load its EduEdge product bundle;
4. mount through the EdgeSuite UI runtime;
5. show a controlled error state if the runtime or product bundle is unavailable.

The global product menu bundle must:

1. load from `app_include_js`;
2. request `edgeui.bundle.js` before registration;
3. use `window.EdgeSuiteUI` with the temporary `window.EdgeUI` compatibility alias;
4. provide grouped, role-aware menu data;
5. avoid importing CoreEdge or EdgeSuite UI source files directly.

## Enforcement

Repository contract tests must fail when:

- the launcher points to the native workspace instead of EduEdge Home;
- a product Page bundle loads before EdgeSuite UI;
- an EduEdge root Vue page does not use `EdgeAppShell`;
- product code imports EdgeSuite UI or CoreEdge source files directly;
- product navigation returns to emoji or single-letter icon placeholders;
- the global product menu is removed from EduEdge hooks;
- professional menu role hints are treated as a replacement for backend permissions.

## Runtime QA

Every significant UI phase must be checked at desktop, tablet, and mobile widths. Confirm:

- topbar and sidebar spacing;
- product menu positioning and scrolling;
- mobile sidebar open/close behaviour;
- active-route highlighting;
- SVG icon visibility in light and dark Frappe themes;
- keyboard focus and Escape dismissal;
- branch/company context truncation;
- long menu labels;
- controlled failure when EdgeSuite UI assets are unavailable.
