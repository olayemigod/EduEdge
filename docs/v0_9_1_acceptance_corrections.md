# EduEdge V0.9.1 — Acceptance Corrections

## Business goal

Close acceptance issues found after the unified CBT and Institution/Academic Context branch migrated successfully on `eduedge.local`:

1. Current Institution and Branch were not displayed consistently on every EduEdge page.
2. Primary and Secondary school interfaces still showed generic **Assessment** wording where operational users expect **Examination**.
3. After switching from a Primary/Secondary Branch to a Tertiary or Training Centre Branch, already-rendered terminology did not reverse until the browser was manually refreshed.
4. Primary School surfaces retained visible **Student** wording instead of the approved **Pupil** terminology.
5. EdgeSuite quick-editor and confirmation dialogs stopped rendering after the document-wide terminology observer began mutating Vue-managed modal content.

The corrections preserve all standard Frappe Education DocType names and database identities.

## Implemented corrections

### Persistent Institution and Branch context

- Branch-switch responses include the resolved Institution context.
- The global EduEdge terminology bundle intercepts successful Branch switches and refreshes boot identity immediately.
- Route changes can refresh active Institution context from the server.
- The shared shell identity renderer no longer depends on one exact EdgeAppShell selector.
- Every EduEdge EdgeSuite top bar receives a side-by-side Institution and Branch context strip.
- Supported native Education forms receive a fallback context strip when an EdgeSuite top bar is not present.
- The context strip updates after Branch switching without requiring a full browser reload.

### Institution-aware examination terminology

The terminology registry includes:

- `assessment`
- `assessment_group`
- `assessment_plan`
- `assessment_result`
- `program_enrollment`
- `student`

Approved visible defaults are:

| Institution Type | Assessment family | Enrollment | Learner |
|---|---|---|---|
| Primary School | Examination | Class Enrollment | Pupil |
| Secondary School | Examination | Class Enrollment | Student |
| Tertiary Institution | Assessment | Programme Enrollment | Student |
| Training Centre | Evaluation | Trainee Enrollment | Trainee |

Primary and Secondary surfaces display labels such as:

- Examinations & Results
- Examination Operations
- Examination Group
- Examination Plan
- Examination Result

Internal Frappe names such as `Assessment Plan`, `Assessment Result`, and `Assessment Group` remain unchanged.

### Live examination terminology reversal

The visible terminology layer treats **Assessment**, **Examination**, and **Evaluation** as one reversible label family.

When the active Institution Type changes, already-rendered content moves in either direction without a manual refresh, including:

- Examination → Assessment
- Examination → Evaluation
- Assessment → Examination
- Assessment → Evaluation
- Evaluation → Assessment
- Evaluation → Examination

The same reversible handling applies to Group, Plan, Result, Operations, and “& Results” labels. Longest phrases are transformed before shorter words to prevent partial replacements.

### Live learner terminology reversal

The visible terminology layer also treats **Student**, **Pupil**, and **Trainee** as one reversible learner family.

This applies to singular and plural labels across:

- menu items;
- page headings and descriptions;
- Student/Pupil/Trainee records and profiles;
- admission, attendance, applicant, and learner-selection labels;
- cards, empty states, placeholders, titles, and accessible labels.

`Student Group` and `Student Batch` phrases are resolved through their own canonical terminology first, preventing incorrect labels such as “Pupil Group” where the approved Primary term is **Class Arm**, or “Pupil Batch” where the approved term is **Admission Set**.

### Dialog rendering safety

The global visible-label observer now excludes interactive overlay surfaces, including:

- EdgeSuite modals;
- native Frappe dialogs;
- elements with `role="dialog"`;
- dropdown menus and autocomplete overlays;
- popovers and tooltips.

This prevents external DOM mutation from interfering with Vue's modal lifecycle and teleported dialog content.

Quick-editor schemas are now translated before rendering:

- dialog title, subtitle, and submit label;
- field labels, descriptions, placeholders, and help text;
- display labels for object-based Link/search options.

Option values and raw Select values remain unchanged so terminology cannot alter stored business data or backend validation values.

## Files changed

- `eduedge/api/branch_context.py`
- `eduedge/education/institution_type_defaults.py`
- `eduedge/public/js/eduedge_terminology.bundle.js`
- `eduedge/public/js/eduedge_shell_identity.bundle.js`
- `eduedge/public/js/eduedge_ui/navigation.js`
- `eduedge/public/js/eduedge_ui/modal_records.js`
- `.github/workflows/ci.yml`
- `eduedge/tests/test_institution_type_foundation_contract.py`
- partner implementation status documentation

## Safety rules

- No standard Frappe DocType is renamed.
- No submitted academic or accounting document is changed.
- Branch switching remains permission-aware and server-authoritative.
- The browser terminology layer changes visible wording only; routes, API method names, fieldnames, option values, and database values remain stable.
- Institution context is resolved by Branch → Institution → Company fallback.
- The correction does not force a full browser reload or discard in-page state.
- Vue- and Frappe-managed dialog DOM is not mutated by the global observer.

## Automated validation

The dialog correction adds regression contracts for:

- protected modal and interactive-overlay surfaces;
- schema-level dialog terminology translation;
- preservation of option values;
- existing reversible Assessment/Examination/Evaluation labels;
- existing reversible Student/Pupil/Trainee labels; and
- Student Group and Student Batch terminology precedence.

A fresh CI run is required on the final correction head before browser retest.

## Browser acceptance completed

The following checks passed on `eduedge.local` before the dialog regression was reported:

1. Institution and Branch appear side by side on every tested EduEdge page.
2. Both values refresh immediately after Branch switching.
3. Primary and Secondary display Examination terminology.
4. The menu displays Examinations & Results.
5. Examination Operations, Examination Group, and Examination Plan display correctly.
6. Tertiary displays Assessment without requiring a browser refresh.
7. Training Centre displays Evaluation without requiring a browser refresh.
8. Switching back restores the appropriate terminology immediately.
9. Primary displays Pupil and Pupils instead of Student and Students.
10. Secondary and Tertiary retain Student and Students.
11. Training Centre displays Trainee and Trainees.
12. Primary Student Group-family labels resolve to Class Arm rather than Pupil Group.
13. Primary Student Batch-family labels resolve to Admission Set rather than Pupil Batch.
14. Institution and Branch remain correct throughout Institution Type switching.
15. CBT Operations, Question Builder, and Academic Foundation remain operational.

## Focused dialog retest required

After pulling and rebuilding, verify:

1. Add, Edit, Quick Edit, and confirmation dialogs open visibly.
2. Loading state appears while modal schema data is requested.
3. Dialog fields and Link/search options load.
4. Save, Cancel, close, validation, and confirmation actions work.
5. Primary dialog labels use Pupil/Class Arm/Admission Set where applicable.
6. Tertiary and Training Centre dialog labels use their resolved terminology.
7. Opening and closing dialogs does not break Institution/Branch display or page terminology.

## Remaining acceptance work

After the focused dialog retest, the unified branch still requires:

- restricted-role and Branch-permission testing;
- realistic admissions, enrollment, class, attendance, examination, result-publication, and report-card workflow QA;
- Programme Offering capacity and lifecycle QA;
- fee-context and submitted-accounting safety verification; and
- final merge readiness review.

## Status

**Institution context and terminology behaviour remain accepted. Dialog rendering correction is implemented and awaiting automated validation and focused browser retest.** The PR remains draft until the wider operational QA is completed.