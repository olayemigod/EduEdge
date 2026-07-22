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

EduEdge CI run **1204** passed on the completed terminology correction:

- Python compilation
- JSON validation
- frontend syntax checks, including the shared shell identity and terminology bundles
- complete pure contract suite
- regression contracts for reversible Assessment/Examination/Evaluation labels
- regression contracts for reversible Student/Pupil/Trainee labels
- protection for Student Group and Student Batch terminology precedence

## Browser acceptance completed

The following checks passed on `eduedge.local`:

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

## Remaining acceptance work

The Institution context and terminology browser acceptance slice is complete. The unified branch still requires:

- restricted-role and Branch-permission testing;
- realistic admissions, enrollment, class, attendance, examination, result-publication, and report-card workflow QA;
- Programme Offering capacity and lifecycle QA;
- fee-context and submitted-accounting safety verification; and
- final merge readiness review.

## Status

**Accepted for Institution context and terminology behaviour.** Automated validation and the focused browser acceptance checks passed. The PR remains draft until the wider restricted-role and realistic workflow QA is completed.