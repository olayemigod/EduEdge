# EduEdge CBT V0.8A — Examination Foundation

## Business goal

Establish a safe, branch-aware CBT foundation without changing completed admissions, academic operations, assessment publication, report-card, branch-governance, or accounting behaviour.

The implementation deliberately separates:

- school-owned examinations and question banks operated inside an EduEdge school tenant; and
- EduEdge-operated public examinations, practice products, and examination-bank content managed by ProcessEdge platform administrators.

V0.8A defines governed records and operating controls. It does not yet create candidate attempts, collect payments, publish CBT results, or operate the offline-resilient answer-sync engine.

## Delivered in V0.8A.1

### EduEdge Examination Centre

Two centre types are supported:

- **School Examination Centre** — owned by an enabled EduEdge School Branch / Campus and restricted by branch access.
- **EduEdge Exam Centre** — operated at platform level and manageable only by EduEdge platform administrators.

The model records centre identity, enablement, candidate capacity, paid-exam readiness, public-registration readiness, location, and contact details.

### EduEdge CBT Question

Questions support:

- School Question Bank or EduEdge Examination Bank ownership;
- branch-safe school ownership;
- Subject / Course, topic, curriculum, exam body, and difficulty classification;
- Single Choice, Multiple Choice, True/False, Short Answer, Essay, and Numeric types;
- governed answer options and marking information;
- positive marks and optional negative marking;
- Draft, Under Review, Approved, and Retired statuses;
- explicit version numbers and superseded-question links;
- role-gated approval and retirement;
- immutable approved content and answer options.

Teachers and instructors can prepare school-owned questions. Approval and retirement require an authorised academic or platform management role. Candidate, parent, and invigilator roles are not granted direct Question Bank access because answer keys must never be exposed through ordinary DocType permissions.

## Delivered in V0.8A.2

### EduEdge CBT Exam Template

Exam templates define a reusable examination blueprint and support:

- **School Examination** and **EduEdge Public Examination** ownership scopes;
- branch, academic year, academic term, programme, class, subject, assessment group, and exam-body context for school examinations;
- optional default examination-centre selection;
- duration, maximum-attempt, pass-percentage, navigation, timeout, and resume policies;
- question and answer-option randomisation policies;
- use of question-level marks or disabling of negative marking;
- manual or after-submission result-release definitions for later attempt processing;
- Draft, Under Review, Approved, and Retired governance;
- explicit template versioning and supersession;
- approved-template immutability and deletion protection.

Public examination templates clear school-only academic context and can be managed only by an EduEdge platform administrator.

### Approved-question selection

Template question rows:

- load only Approved questions from the matching ownership scope;
- filter by selected school branch and Subject / Course;
- reject duplicate questions and duplicate or invalid display-order values;
- snapshot question type, topic, positive mark, and negative mark;
- calculate question count, total marks, and maximum negative marks;
- remain immutable after template approval.

An already approved template uses its stored scoring snapshot when it is later retired. This prevents a subsequently retired source question from blocking template retirement or altering the historical template definition.

### Smart form behaviour

The exam-template form uses cascading filters and clearing rules:

- Branch changes clear invalid centres, classes, questions, and superseded-template selections.
- Academic Year changes clear Academic Term and Student Group / Class.
- Programme and Academic Term changes refresh class validity.
- Subject / Course changes clear invalid classes, questions, and version links.
- Examination Centre options are filtered by school/public scope and branch.
- Question options are provided by a permission-aware server query and include only Approved questions valid for the selected scope, branch, and course.

Backend validation repeats every business-critical rule. Frontend filtering is only a guided data-entry layer.

### CBT Operations page

The first EdgeSuite UI CBT Operations page now provides:

- School Examination and authorised EduEdge Public Examination scope switching;
- branch-safe centre, template, and question readiness counts;
- enabled-centre and approved-template visibility;
- recent centre and template records with direct navigation;
- question-bank readiness visibility only for authorised question authors;
- a clear statement that scheduling, attempts, offline sync, invigilation, and result processing remain future phases.

The page is available through:

- the persistent EduEdge EdgeSuite sidebar;
- the global EdgeSuite product menu;
- the native EduEdge Workspace.

## Safety rules

- Approved and retired question content cannot be edited in place.
- A corrected question must be created as a higher version that supersedes an Approved or Retired question.
- Approved and retired exam-template content and question rows cannot be edited in place.
- A corrected template must be created as a higher version that supersedes an Approved or Retired template.
- EduEdge Examination Bank and public-template records cannot be converted into school-owned records by normal school users.
- School-owned centres, questions, and templates require access to the selected enabled branch.
- School roles cannot list platform-owned CBT records even while strict branch enforcement is using the legacy fallback.
- Students and parents have no direct Question Bank or Exam Template access.
- CBT Invigilators may read permitted school templates but cannot open the Question Bank or answer keys.
- Public registration, paid-exam readiness, maximum-attempt, result-release, resume, and timeout fields are definitions only until their execution engines are implemented.
- No Sales Invoice, Payment Entry, Journal Entry, assessment result, result publication, or submitted academic record is created or modified.

## Migration

Run on the EduEdge development site:

```bash
cd ~/frappe-bench
bench --site <site-name> migrate
bench build --app eduedge
bench --site <site-name> clear-cache
```

Then restart development processes or reload the production workers as appropriate for the deployment.

No data patch is required because V0.8A adds new DocTypes, a Page, permission hooks, and frontend assets. Existing school, branch, assessment, and accounting records are not backfilled or mutated.

## Automated tests

The repository contract and CI suite validates:

- centre-scope separation;
- question ownership, answer options, approval, versioning, and immutability;
- absence of candidate, parent, and invigilator access to the Question Bank;
- exam-template ownership and academic/timing/policy fields;
- template question snapshot structure;
- approved-question-only and branch/course validation markers;
- platform-record isolation and Frappe permission-hook registration;
- cascading smart-form query configuration;
- CBT Operations page, bundle, navigation, product-menu, and Workspace registration;
- Python compilation, JSON validity, and frontend entry-script syntax.

## Manual QA checklist

### V0.8A.1 centre and question QA

1. Create a School Examination Centre for an authorised branch.
2. Confirm another branch-restricted user cannot list or open that centre.
3. Confirm a School Administrator cannot create an EduEdge Exam Centre.
4. Create a Single Choice school question with two options and one correct answer.
5. Confirm duplicate option keys and multiple correct answers are rejected.
6. Move the question to Under Review and approve it as an Academic Administrator.
7. Confirm its question text, marks, ownership, and answer options can no longer be edited.
8. Create Version 2 referencing the Approved question and confirm the new version number is greater.
9. Confirm Student, EduEdge Parent, and CBT Invigilator users cannot open the Question Bank list.

### V0.8A.2 exam-template QA

10. Open CBT Operations and confirm a user without a current branch can still reach the page and select an authorised branch.
11. Confirm a school user cannot select EduEdge Public Examination scope.
12. Create a School Examination template and confirm Branch and Academic Year are mandatory.
13. Confirm the Examination Centre field shows only enabled School Examination Centres in the selected branch.
14. Confirm Student Group / Class options respect branch, year, term, programme, and course context.
15. Add questions and confirm the Link field shows only Approved questions for the selected branch and course.
16. Confirm a Draft, Under Review, Retired, cross-branch, public-bank, or different-course question is rejected by backend validation.
17. Confirm duplicate questions and duplicate display-order values are rejected.
18. Save the template and confirm question count, total marks, and negative-mark totals are populated.
19. Approve the template as an authorised academic administrator.
20. Confirm timing, academic context, question rows, marks, randomisation, and candidate instructions cannot be edited after approval.
21. Retire a linked source question, then confirm the Approved template can still be moved to Retired using its stored scoring snapshot.
22. Create a higher template version and confirm the superseded template has the same scope, branch, course, and exam body.
23. As a platform administrator, create an EduEdge Public Examination template and confirm school-only fields are cleared.
24. Confirm a normal school role cannot list or open the public centre, public question, or public template.
25. Confirm the CBT Operations counts and recent records change correctly between school and public scopes.
26. Confirm no accounting, candidate-attempt, CBT-result, or academic-result document is created.

## Not included in V0.8A

- exam schedules and examination sessions;
- candidate generation and eligibility rules;
- one active attempt per candidate;
- server-authoritative attempt timing;
- browser answer storage and automatic sync;
- pending-sync visibility and duplicate-event prevention;
- invigilator live monitoring and incident handling;
- answer snapshots inside attempts;
- automated and human marking execution;
- CBT result review, approval, publication, or Frappe Education result sync;
- EdgePay collection for public or paid examinations.

## Next implementation slice

V0.8A.3 should add the **CBT Exam Schedule and Candidate Eligibility Foundation**:

- scheduled examination instances created from Approved templates;
- branch, centre, start-window, end-window, and server-time rules;
- candidate source and eligibility definitions;
- duplicate-candidate prevention;
- schedule capacity and centre consistency checks;
- initial invigilator assignment and schedule readiness;
- no attempt creation or answer capture until the following attempt-engine slice.
