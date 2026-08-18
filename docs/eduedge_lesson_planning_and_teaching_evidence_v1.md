# EduEdge Lesson Planning & Teaching Evidence V1

## Goal

Provide a governed teaching-preparation workflow that connects approved curriculum planning to exact Instructor responsibility and append-only delivery evidence:

**Approved Scheme of Work → Exact Instructor Assignment → Lesson Plan → Academic Review → Approved Lesson Plan → Scheme Delivery Evidence**

This layer does not replace Scheme of Work, Instructor Assignment, Course Schedule, Attendance, CBT, or Assessment governance. It connects them without rewriting historical records.

## Scope

### Lesson Plan master

`EduEdge Lesson Plan` records:

- Approved Scheme of Work and exact Scheme item;
- Branch / Campus;
- Class / Programme Offering;
- optional Class Arm / Student Group;
- Subject / Course;
- Academic Session and Term / Semester;
- Lesson Date and optional Period / Slot;
- Instructor and exact Instructor Assignment;
- lesson objectives;
- prior knowledge / entry behaviour;
- introduction / starter;
- teaching methods;
- teacher activities;
- learner activities;
- learning resources;
- formative assessment / evaluation;
- differentiation / support notes;
- homework / follow-up;
- submission/review audit;
- approval snapshots of Scheme, Class, Class Arm, Subject, Topic, and Scheme learning objective.

Statuses are:

- Draft
- Submitted
- Approved
- Returned

### Workflow

- Draft and Returned plans can be edited by an authorised user.
- Submit requires minimum teaching-preparation content.
- Submitted plans are read-only while awaiting Academic Review.
- Academic management can Approve or Return for Correction.
- Returned plans can be corrected and resubmitted.
- Approved plans are immutable academic history.
- Submitted, Returned, and Approved plans cannot be deleted.

## Exact teaching responsibility

Lesson Plan creation does not rely only on a Teacher role or Branch Eligibility.

The selected Instructor must have an effective `EduEdge Instructor Assignment` matching the exact:

- Branch;
- Class / Programme Offering;
- Class Arm where applicable;
- Subject / Course;
- Lesson Date.

Class-wide Subject responsibility can cover all Class Arms. Class-Arm responsibility covers only the assigned Student Group.

Limited Instructor users must resolve to exactly one Instructor identity. When `enforce_instructor_assignment_capabilities` is enabled, the exact assignment must also grant `Can View Subject Content`.

The capability flag remains migration-safe and is not silently enabled by Lesson Planning.

## Smart workbench

The EdgeSuite Lesson Plans workbench uses the cascade:

**Branch → Class / Programme Offering → Class Arm → Subject / Course → Approved Scheme of Work → Scheme Item → Lesson Date → Eligible Instructor**

Dependent values are cleared when a parent context changes.

Instructor options are derived from effective exact Instructor Assignments for the selected context and date. The API does not load every active Instructor and filter them in the browser.

History filters include:

- Branch;
- Class;
- Class Arm;
- Subject;
- Instructor;
- status;
- date range.

Filters are URL-persisted and history is paginated.

## Teaching evidence connection

`EduEdge Scheme Delivery Log` remains append-only and now supports:

- optional link to an Approved Lesson Plan;
- optional teaching evidence attachment;
- existing delivery notes and exact Instructor Assignment audit.

A linked Lesson Plan must match the exact:

- approved Scheme of Work;
- Scheme item;
- Branch;
- Class / Programme Offering;
- Class Arm;
- Subject;
- Instructor;
- Delivery Date.

The delivery workbench shows only matching Approved Lesson Plans. Evidence can be attached from the UI and remains part of the immutable delivery log.

The evidence field should be used for appropriate classroom evidence such as teaching materials, worksheets, activity outputs, or suitable classroom photos. Users should avoid uploading unnecessary sensitive Student information.

## Historical integrity

S2I does not mutate:

- an Approved Scheme of Work;
- Instructor Assignment history;
- prior Lesson Plan approval history;
- earlier Scheme Delivery Log entries.

Approval snapshots readable labels so later master-data wording changes do not rewrite the historical meaning of an Approved Lesson Plan.

Scheme delivery continues as append-only events. Lesson Plan and evidence links are recorded only on the new delivery event.

## Duplicate safety

EduEdge blocks duplicate Lesson Plans for the same:

- Instructor;
- Branch;
- Class;
- Class Arm context;
- Subject;
- Scheme item;
- Lesson Date;
- Period / Slot.

Blank Period / Slot values are normalized during duplicate checking so database NULL/empty-string differences cannot bypass the guard.

## Permissions

Direct `EduEdge Lesson Plan` DocType permissions are reserved for academic-management roles.

Teacher / Instructor access runs through governed EduEdge APIs that enforce:

- exact Instructor identity;
- Branch access;
- exact teaching assignment;
- optional assignment-capability enforcement.

This prevents broad direct DocType permission from becoming a bypass around teaching scope.

## Files

Core implementation:

- `eduedge/eduedge/doctype/eduedge_lesson_plan/`
- `eduedge/api/lesson_plans.py`
- `eduedge/eduedge/page/eduedge_lesson_plans/`
- `eduedge/public/js/eduedge_lesson_plans.bundle.js`
- `eduedge/public/js/eduedge_lesson_plans/EduEdgeLessonPlans.vue`
- `eduedge/api/scheme_delivery.py`
- `eduedge/eduedge/doctype/eduedge_scheme_delivery_log/eduedge_scheme_delivery_log.json`
- `eduedge/public/js/eduedge_ui/components/SchemeDeliveryPanel.vue`
- `eduedge/access_control.py`
- `eduedge/public/js/eduedge_ui/navigation.js`

Contract coverage:

- `eduedge/tests/test_lesson_plan_foundation_contract.py`
- `eduedge/tests/test_lesson_plan_ui_contract.py`
- `eduedge/tests/test_lesson_plan_delivery_evidence_contract.py`
- `eduedge/tests/test_lesson_plan_smart_instructor_options_contract.py`

## Migration and backward compatibility

A site migration is required because this slice adds:

- the `EduEdge Lesson Plan` DocType;
- the optional `lesson_plan` Link on `EduEdge Scheme Delivery Log`.

Existing Scheme Delivery Log rows remain valid because the new Lesson Plan link is optional.

Existing Scheme of Work, Instructor Assignment, Course Schedule, Attendance, CBT, and Assessment records are not migrated or rewritten by this slice.

## Validation state

Automated repository validation is required before handoff. Manual browser QA is intentionally deferred until the project owner resumes the QA session.

Deferred QA should cover at minimum:

- manager workbench smart cascade;
- limited Instructor identity/scope restrictions;
- Draft save and duplicate protection;
- Submit → Return → correct → resubmit;
- Submit → Approve;
- Approved immutability;
- approval snapshots;
- teaching delivery with and without linked Lesson Plan;
- evidence upload;
- wrong Instructor/Class/Subject/date negative cases;
- pagination/filter persistence;
- migration and frontend build on the integration site.
