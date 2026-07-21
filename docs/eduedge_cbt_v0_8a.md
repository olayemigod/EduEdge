# EduEdge CBT V0.8A — Examination Foundation

## Business goal

Establish a safe, branch-aware CBT definition layer without changing completed admissions, academic operations, assessment publication, report-card, branch-governance, or accounting behaviour.

V0.8A separates:

- school-owned CBT operated inside an EduEdge tenant; and
- ProcessEdge-governed EduEdge public examinations consumed through central services.

V0.8A does not yet create candidate attempts, collect payments, publish CBT results, or operate the offline-resilient answer-sync engine.

## V0.8A.1 — Centres and question governance

### Examination Centres

Two centre types are supported:

- **School Examination Centre** — owned by an EduEdge School Branch / Campus and restricted by branch access.
- **EduEdge Exam Centre** — centrally operated and manageable only through ProcessEdge public-exam authority.

Centres are non-submittable master records. Their operational status is:

- Draft;
- Active;
- Suspended;
- Retired.

Only Active centres may be selected for schedules. The old `enabled` field is retained as a hidden compatibility value derived from Centre Status.

A School Examination Centre may separately receive a centrally controlled public-hosting status:

- Not Requested;
- Pending;
- Approved;
- Suspended;
- Revoked.

School staff cannot self-approve public hosting.

### Question Banks

Questions support:

- School Question Bank or EduEdge Examination Bank ownership;
- branch-safe school ownership;
- course, topic, curriculum, exam body, and difficulty classification;
- Single Choice, Multiple Choice, True/False, Short Answer, Essay, and Numeric types;
- governed answer options and marking data;
- positive marks and optional negative marking;
- Draft, Under Review, Approved, and Retired statuses;
- explicit versioning and supersession;
- immutable approved content and answer options.

Teachers and instructors may prepare school questions. School approval requires an authorised academic role. EduEdge Examination Bank creation, approval, retirement, and deletion require ProcessEdge public-exam authoring authority.

Students, parents, and invigilators are not granted Question Bank access because answer keys must not be exposed through ordinary DocType permissions.

## V0.8A.2 — Exam templates and CBT Operations

### Exam Templates

Templates define reusable examination blueprints and support:

- School Examination and EduEdge Public Examination ownership;
- branch, year, term, programme, class, course, assessment group, and exam-body context for school examinations;
- an optional Active default examination centre;
- duration, maximum attempts, pass percentage, navigation, timeout, and resume policies;
- question and option randomisation;
- question marks or disabled negative marking;
- manual or after-submission result-release definitions;
- Draft, Under Review, Approved, and Retired governance;
- versioning, supersession, immutability, and deletion protection.

Public templates clear school-only context and require ProcessEdge public-exam authoring authority.

### Approved-question selection

Template question rows:

- load only Approved questions from the matching ownership scope;
- filter by branch and course;
- reject duplicates and invalid display order;
- snapshot question type, topic, marks, and negative marks;
- calculate question count and totals;
- remain immutable after approval.

An approved template retains its stored scoring snapshot even when a source question is later retired.

### Smart forms

Frontend behaviour guides users toward valid records:

- Branch changes clear invalid centres, classes, questions, and version links.
- Academic Year changes clear incompatible term/class context.
- Programme, term, and course changes refresh dependent filters.
- Centre options show only Active centres in the valid scope and branch.
- Question options come from permission-aware server queries.
- Public centre, bank, and template choices are hidden unless server-authoritative public authoring is available.

Backend validation repeats all business-critical rules.

### CBT Operations

The EdgeSuite UI page provides:

- School Examination scope and, only for authorised ProcessEdge authors, public-authoring scope;
- branch-safe centre, question, and template readiness;
- centre lifecycle and public-hosting visibility;
- direct navigation into governed records;
- a CoreEdge capability matrix for public catalogue, assignment, hosting, launch, results, and authoring;
- clear visibility of what remains outside V0.8A.

It is registered in the persistent EduEdge sidebar, global product menu, and native Workspace.

## Public exam access across deployment types

Deployment mode does not grant public-exam privilege.

Shared-hosted, standalone, and white-label sites use the same CoreEdge capability model:

```text
cbt_public_exam/catalog
cbt_public_exam/assign
cbt_public_exam/host
cbt_public_exam/launch
cbt_public_exam/results
cbt_public_exam/author
```

Each grant belongs to one authenticated CoreEdge Service Client bound to the exact tenant, EduEdge product, integration user, and site identifier.

Standalone and white-label sites continue to own their School CBT records. When whitelisted, they consume central public exam versions without receiving editable public questions or answer keys.

Public authoring requires:

- `EduEdge Super Administrator` or `EduEdge Public Exam Administrator`; and
- an allowed CoreEdge `author` grant, or the controlled central-authority server flag.

`System Manager`, local `Administrator`, deployment mode, or server ownership alone does not grant public authoring.

See `docs/eduedge_public_exam_access_model.md` for the complete architecture and onboarding contract.

## Safety rules

- Approved questions and templates cannot be edited in place.
- Corrections require a higher version referencing an Approved or Retired record.
- School users cannot list or open centrally owned records through ordinary Desk permissions.
- Public authoring is not inferred from tenant administrative roles.
- Candidate, parent, and invigilator roles cannot access answer banks.
- Public hosting approval is controlled centrally.
- Public capability decisions fail closed after the allowed cache window.
- Public registration, paid-exam, attempts, resume, timeout, and result-release fields are definitions only in V0.8A.
- No Sales Invoice, Payment Entry, Journal Entry, candidate attempt, CBT result, academic result, or result publication is created or mutated.

## Migration

Run on the EduEdge development site:

```bash
cd ~/frappe-bench
bench --site <site-name> migrate
bench build --app eduedge
bench --site <site-name> clear-cache
```

The idempotent V0.8 centre patch maps legacy records safely:

- existing `enabled = 1` centres become Active;
- existing disabled centres become Draft;
- centres already changed through the new audited status flow are not overwritten.

The migration also provisions `EduEdge Public Exam Administrator`.

## Controlled site configuration

A normal client site must use remote CoreEdge configuration and must not set itself as the authoring authority.

The centrally controlled ProcessEdge exam-authoring site may use:

```json
{
  "eduedge_public_exam_authority": true
}
```

A standalone/white-label client uses settings similar to:

```json
{
  "edge_platform_mode": "remote",
  "coreedge_required": true,
  "coreedge_fail_closed": true,
  "coreedge_base_url": "https://coreedge.example.com",
  "coreedge_tenant_key": "TENANT-KEY",
  "coreedge_site_identifier": "school.example.com",
  "coreedge_client_id": "API-KEY",
  "coreedge_client_secret": "API-SECRET",
  "coreedge_access_decision_path": "/api/method/coreedge.api.v1.service_gateway.check_feature_access"
}
```

Secrets must not be committed to Git or copied into normal documentation.

## Automated validation

CI validates:

- Python compilation and JSON validity;
- frontend form/page syntax;
- centre lifecycle, migration, and hosting controls;
- question/template ownership and immutability;
- approved-question filtering and scoring snapshots;
- branch and public-master isolation;
- explicit public capability/action contract;
- absence of `System Manager` from public author roles;
- exact site identifier and Frappe token authentication in the remote adapter;
- CBT Operations registration and capability matrix.

## Manual QA checklist

### Centre lifecycle

1. Migrate an existing enabled centre and confirm it becomes Active.
2. Create a new School Examination Centre and confirm it starts as Draft.
3. Confirm Draft can become Active.
4. Confirm Active can become Suspended and then Active again.
5. Confirm Active or Suspended can become Retired.
6. Confirm Retired cannot return to another status.
7. Confirm only Draft centres can be deleted.
8. Confirm only Active centres appear in template centre queries.
9. Confirm school staff cannot edit Public Exam Hosting Status or Public Centre Reference.

### School question and template flow

10. Create and approve a valid school question.
11. Confirm invalid options, marks, branch, course, and status combinations are rejected.
12. Confirm approved question content becomes immutable.
13. Create a School Examination template and verify cascading academic filters.
14. Add only approved questions from the matching branch/course.
15. Confirm totals are calculated and duplicate questions/orders are rejected.
16. Approve the template and confirm immutability.
17. Create higher question and template versions safely.

### Public access governance

18. On a standalone site without CoreEdge grants, confirm the capability matrix shows Not Activated.
19. Confirm only School Examination Centre, School Question Bank, and School Examination choices appear on new forms.
20. Attempt to create public records through API/import and confirm backend permission rejection.
21. Confirm tenant `System Manager` and local `Administrator` cannot list public records without author authority.
22. On the controlled authority site, enable the authority flag temporarily and confirm an authorised ProcessEdge role can create public masters.
23. Disable the authority flag and confirm access closes again.
24. On a registered remote test site, activate only `catalog` and confirm other actions remain blocked.
25. Activate `host` separately and confirm hosting remains dependent on an Approved centre verification.
26. Suspend or revoke a CoreEdge grant and confirm the site loses that capability.
27. Confirm an incorrect site identifier is rejected before capability evaluation.

### UI and safety

28. Confirm CBT Operations loads with EdgeSuite UI and realtime services.
29. Confirm branch and public-scope counts do not leak records.
30. Confirm no accounting, attempt, CBT-result, or academic-result record is created.

## Not included in V0.8A

- central public catalogue synchronization;
- exam schedules and candidate eligibility;
- signed launch sessions;
- one active attempt per candidate;
- server-authoritative timing;
- browser answer storage and automatic sync;
- invigilator live monitoring;
- automated/human marking execution;
- signed result return and reconciliation;
- academic-result sync;
- EdgePay collection and wallet charging.

## Next implementation slice

V0.8A.3 adds the CBT Exam Schedule and Candidate Eligibility Foundation, including school schedules and central public-exam references. Attempt creation and answer capture remain in the following attempt-engine slice.
