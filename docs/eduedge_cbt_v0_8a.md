# EduEdge CBT V0.8A — Examination Centre and Question Bank Foundation

## Business goal

Establish the first safe CBT domain objects without changing completed admissions, academic operations, assessment publication, report-card, branch-governance, or accounting behaviour.

This slice deliberately separates school-owned examination operations from the EduEdge-operated public examination platform.

## Delivered in V0.8A.1

### EduEdge Examination Centre

Two centre types are supported:

- **School Examination Centre** — owned by an enabled EduEdge School Branch / Campus and restricted by branch access.
- **EduEdge Exam Centre** — operated at platform level and manageable only by EduEdge platform administrators.

The model records centre identity, enablement, candidate capacity, paid-exam readiness, public-registration readiness, location, and contact details.

V0.8A.1 does not register candidates, schedule exams, collect payments, or create accounting documents.

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

## Safety rules

- Approved and retired question content cannot be edited in place.
- A corrected question must be created as a higher version that supersedes an Approved or Retired question.
- EduEdge Examination Bank records cannot be converted into school-owned records by normal school users.
- School-owned centres and questions require access to the selected enabled branch.
- Public registration and payment processing are only readiness flags in this slice.
- No Sales Invoice, Payment Entry, Journal Entry, assessment result, or submitted academic record is created or modified.

## Migration

Run:

```bash
bench --site <site-name> migrate
bench --site <site-name> clear-cache
```

No data patch is required because this slice adds new DocTypes and permission hooks only.

## Automated tests

The repository contract suite validates:

- centre-scope separation;
- question ownership and classification fields;
- child answer-option structure;
- absence of candidate, parent, and invigilator access to the Question Bank;
- approval and immutability safeguards;
- branch permission hook registration.

## Manual QA checklist

1. Create a School Examination Centre for an authorised branch.
2. Confirm another branch-restricted user cannot list or open that centre.
3. Confirm a School Administrator cannot create an EduEdge Exam Centre.
4. Create a Single Choice school question with two options and one correct answer.
5. Confirm duplicate option keys and multiple correct answers are rejected.
6. Submit the question for review and approve it as an Academic Administrator.
7. Confirm its question text, marks, ownership, and answer options can no longer be edited.
8. Create Version 2 referencing the Approved question and confirm the new version number is greater.
9. Confirm Student, EduEdge Parent, and CBT Invigilator users cannot open the Question Bank list.
10. Confirm no accounting or academic-result document is created.

## Next implementation slice

V0.8A.2 should add:

- CBT Exam Template;
- template question rows with safe question selection;
- School Examination versus EduEdge public-exam ownership;
- academic year, term, programme, class, and subject context;
- randomisation, timing, attempt, and marking-policy definitions;
- validation that only Approved question versions can enter an exam template;
- an EdgeSuite UI CBT Operations entry point.
