# EduEdge V0.9.1 — Acceptance Corrections

## Business goal

Close two acceptance issues found after the unified CBT and Institution/Academic Context branch migrated successfully on `eduedge.local`:

1. Current Institution and Branch were not displayed consistently on every EduEdge page.
2. Primary and Secondary school interfaces still showed generic **Assessment** wording where operational users expect **Examination**.

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

The terminology registry now includes:

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

## Automated validation

EduEdge CI run **1180** passed on the correction head:

- Python compilation
- JSON validation
- frontend syntax checks, including the shared shell identity bundle
- complete pure contract suite

## Local retest required

After pulling and rebuilding, verify:

1. Institution and Branch appear side by side on every EduEdge-owned page.
2. The pair refreshes immediately after Branch switching.
3. Primary and Secondary interfaces display Examination terminology.
4. Tertiary interfaces retain Assessment terminology.
5. Training Centre interfaces display Evaluation terminology.
6. Native Frappe Assessment Plan/Result/Group routes retain their internal routes while showing the resolved EduEdge wording.
7. CBT Operations, Question Builder, Academic Foundation, Institution Structure, and other previously passed pages still open normally.

## Status

Implemented with automated validation passed. Browser acceptance retest remains required before the unified branch is merged to `main`.
