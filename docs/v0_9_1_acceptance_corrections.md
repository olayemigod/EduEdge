# EduEdge V0.9.1 — Acceptance Corrections

## Business goal

Close acceptance issues found after the unified CBT and Institution/Academic Context branch migrated successfully on `eduedge.local`:

1. Current Institution and Branch were not displayed consistently on every EduEdge page.
2. Primary and Secondary school interfaces still showed generic **Assessment** wording where operational users expect **Examination**.
3. After switching from a Primary/Secondary Branch to a Tertiary or Training Centre Branch, already-rendered terminology did not reverse until the browser was manually refreshed.
4. Primary School surfaces retained visible **Student** wording instead of the approved **Pupil** terminology.

The correction preserves all standard Frappe Education DocType names and database identities.

## Implemented corrections

### Persistent Institution and Branch context

- Branch-switch responses now include the resolved Institution context.
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

Primary and Secondary surfaces therefore display labels such as:

- Examinations & Results
- Examination Operations
- Examination Group
- Examination Plan
- Examination Result

Internal Frappe names such as `Assessment Plan`, `Assessment Result`, and `Assessment Group` remain unchanged.

### Live examination terminology reversal

The visible terminology layer treats **Assessment**, **Examination**, and **Evaluation** as one reversible label family.

When the active Institution Type changes, already-rendered content can move in either direction without a manual refresh, including:

- Examination → Assessment
- Examination → Evaluation
- Assessment → Examination
- Assessment → Evaluation
- Evaluation → Assessment
- Evaluation → Examination

The same reversible handling applies to Group, Plan, Result, Operations, and “& Results” labels. Longest phrases are transformed before shorter words to prevent partial replacements.

### Live learner terminology reversal

The visible terminology layer now also treats **Student**, **Pupil**, and **Trainee** as one reversible learner family.

This applies to singular and plural labels across:

- menu items;
- page headings and descriptions;
- Student/Pupil/Trainee records and profiles;
- admission, attendance, applicant, and learner-selection labels;
- cards, empty states, placeholders, titles, and accessible labels.

`Student Group` and `Student Batch` phrases are resolved through their own canonical terminology first, preventing incorrect labels such as “Pupil Group” where the approved Primary term is **Class Arm**, or “Pupil Batch” where the approved term is **Admission Set**.

## Files changed

- `eduedge/api/branch_context.py`
- `eduedge/education/institution_type_defaults.py`
- `eduedge/public/js/eduedge_terminology.bundle.js`
- `eduedge/public/js/eduedge_shell_identity.bundle.js`
- `eduedge/public/js/eduedge_ui/navigation.js`
- `.github/workflows/ci.yml`
- `eduedge/tests/test_institution_type_foundation_contract.py`
- partner implementation status documentation

## Safety rules

- No standard Frappe DocType is renamed.
- No submitted academic or accounting document is changed.
- Branch switching remains permission-aware and server-authoritative.
- The browser terminology layer changes visible wording only; routes, API method names, fieldnames, and database values remain stable.
- Institution context is resolved by Branch → Institution → Company fallback.
- The correction does not force a full browser reload or discard in-page state.

## Automated validation

EduEdge CI run **1196** passed on the learner terminology correction:

- Python compilation
- JSON validation
- frontend syntax checks, including the shared shell identity and terminology bundles
- complete pure contract suite
- regression contracts for reversible Assessment/Examination/Evaluation labels
- regression contracts for reversible Student/Pupil/Trainee labels
- protection for Student Group and Student Batch terminology precedence

## Local acceptance completed

The following checks passed before the learner-label correction:

1. Institution and Branch appear side by side on every EduEdge page.
2. The pair refreshes immediately after Branch switching.
3. Primary and Secondary interfaces display Examination terminology.
4. The menu displays Examinations & Results.
5. Examination Operations, Examination Group, and Examination Plan display correctly.
6. Tertiary displays Assessment without requiring a refresh after the live reversal fix.
7. Training Centre displays Evaluation.
8. CBT Operations and Academic Foundation remain operational.

## Final local retest required

After pulling and rebuilding, switch directly between Institution Types without refreshing the browser and verify:

1. Primary displays **Pupil** and **Pupils** instead of Student/Students.
2. Secondary and Tertiary display **Student** and **Students**.
3. Training Centre displays **Trainee** and **Trainees**.
4. Primary `Student Group`-family labels resolve to **Class Arm**, not Pupil Group.
5. Primary `Student Batch`-family labels resolve to **Admission Set**, not Pupil Batch.
6. Institution and Branch remain correct throughout the switches.

## Status

Implemented with automated validation passed. All previous browser checks passed; only the learner terminology retest remains before this correction is accepted.