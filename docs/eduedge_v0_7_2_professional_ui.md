# EduEdge V0.7.2 — Professional EdgeSuite UI and Product Navigation

## Business goal

V0.7.2 upgrades EduEdge from a technically consistent foundation UI to a professional product experience suitable for a high-rated education application.

The design is simple, clear, responsive, and memorable. It borrows the strongest spacing and interaction patterns already proven in VetEdge while preserving EduEdge's education identity and blue/green brand colours.

## Product and shared-app boundary

- The standalone `edgesuite_ui` app owns shared shell components, SVG icons, spacing tokens, responsive navigation, product-menu rendering, and native Frappe sidebar styling.
- EduEdge owns its menu structure, labels, routes, role hints, page workflows, backend permissions, and product data.
- CoreEdge remains a remote platform service and is not imported into either UI bundle.
- Menu visibility is a usability layer only. Frappe permissions, branch access, role checks, API validation, and accounting rules remain authoritative.

## Shared EdgeSuite UI 0.2 capabilities

EduEdge V0.7.2 depends on the companion EdgeSuite UI 0.2 branch, which provides:

- responsive `EdgeAppShell` professional override;
- grouped desktop sidebar;
- mobile off-canvas sidebar with accessible toggle and backdrop;
- searchable, sectioned global product menu;
- semantic SVG icon library with Frappe icon reuse and local fallback;
- product-brand CSS variables;
- consistent page, section, and card spacing;
- professional headers, filters, cards, buttons, forms, focus states, and empty/error/loading states;
- native Frappe Workspace sidebar styling for EduEdge and other EdgeSuite products.

## EduEdge navigation structure

### Overview

- EduEdge Home

### School Operations

- Academic Operations
- Admissions
- Applicants
- Students

### Academics and Outcomes

- Program Offerings
- Assessments and Results
- Report Cards

### Administration

- Branch Governance
- School Branches
- User Branch Access
- Setup Center

The persistent product sidebar uses a flat backward-compatible item list with `section`, `sectionIcon`, `description`, and semantic `icon` values. EdgeSuite UI 0.2 groups these entries automatically.

The global waffle product menu uses explicit sections with search keywords, descriptions, SVG icons, profile context, role hints, and active-route detection.

## Brand and visual rules

EduEdge uses:

- primary blue: `#1f6feb`;
- action blue: `#185fc8`;
- deep blue: `#174ea6`;
- accent green: `#22a06b`;
- pale blue and green surfaces for selected and contextual states.

The UI must avoid:

- emoji as navigation icons;
- single-letter icon placeholders;
- raw SVG names shown as text;
- unnecessary gradients or excessive shadows;
- cramped cards and filters;
- large empty gaps between menu sections;
- desktop-only sidebar behaviour on mobile.

## Spacing and responsive behaviour

The shared design uses:

- responsive page padding;
- consistent section and card gaps;
- maximum content width for wide displays;
- compact but readable navigation item height;
- persistent sidebar on desktop;
- narrower layout on smaller laptops;
- off-canvas sidebar on tablet and mobile;
- stacked page actions and one-column product menu on mobile.

Existing Bootstrap and Frappe controls remain valid. EdgeSuite UI standardises their spacing, radius, focus ring, and layout without rewriting every control.

## Native sidebar

The shared professional stylesheet applies matching styling to the native Frappe EduEdge Workspace sidebar while preserving Frappe's behaviour and permission model.

It adds:

- SVG icon tiles;
- compact uppercase section headings;
- rounded hover states;
- brand-coloured active state and left indicator;
- consistent padding and margins;
- visible keyboard focus;
- responsive label wrapping.

## Files added or changed

### EdgeSuite UI repository

- shared SVG icon library;
- professional shell component overrides;
- upgraded searchable product menu renderer;
- professional visual stylesheet;
- runtime and version updates;
- contract tests and integration documentation.

### EduEdge repository

- `eduedge/public/js/eduedge_ui/navigation.js`;
- `eduedge/public/js/eduedge_product_menu.bundle.js`;
- `eduedge/hooks.py`;
- `.github/workflows/ci.yml`;
- `eduedge/tests/test_professional_navigation_contract.py`;
- UI and phase documentation.

## Backward compatibility

- Existing EduEdge Vue pages continue using `EdgeAppShell` without business-logic rewrites.
- Existing flat `menuItems` remain valid.
- `window.EdgeUI` remains available as a compatibility alias.
- Native DocType forms and lists remain available.
- No database schema or migration patch is required specifically for V0.7.2.
- No academic or accounting documents are created or modified by the UI upgrade.

## Automated validation

Required shared EdgeSuite UI checks:

- Python compilation and Ruff;
- package and version consistency;
- frontend syntax and in-memory bundle compilation;
- product-import isolation;
- professional shell and SVG icon contracts;
- product-menu search and lifecycle contracts;
- shared asset-hook validation.

Required EduEdge checks:

- Python compilation;
- JSON validation;
- JavaScript entry-script validation;
- grouped navigation and SVG icon contract;
- global product-menu registration contract;
- EdgeSuite UI loader-order contract;
- backend branch-permission contract remains present.

## Manual browser QA

Validate on desktop, tablet, and mobile:

1. EduEdge Home opens with the professional shared shell.
2. Sidebar sections and item descriptions are correctly grouped.
3. Active route and SVG icons are visible and brand aligned.
4. Sidebar scrolls independently when menu content is long.
5. Mobile menu opens as an off-canvas panel and closes through the toggle, backdrop, route change, and Escape key.
6. Waffle product menu mounts in Frappe Desk and survives page changes.
7. Product-menu search filters by label, description, section, route, and keywords.
8. Role-restricted administration items are hidden where appropriate.
9. Native EduEdge Workspace sidebar receives the same visual treatment.
10. Branch and company context truncate cleanly without breaking the topbar.
11. Forms, cards, filters, buttons, loading, empty, and error states retain useful spacing.
12. Light and dark Frappe themes remain readable.
13. Keyboard focus is visible.
14. EdgeSuite UI asset failure produces the existing controlled page error rather than a broken blank page.

## Deployment order

1. Update and build EdgeSuite UI 0.2.
2. Update EduEdge.
3. Build both apps together.
4. Migrate the EduEdge site.
5. Clear Desk and website caches.
6. Run both app test suites.
7. Perform browser QA before merging or removing any older product-local fallback styling.
