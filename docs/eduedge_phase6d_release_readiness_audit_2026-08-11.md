# EduEdge Phase 6D Release-Readiness Audit

**Audit date:** 2026-08-11  
**Repository:** `olayemigod/EduEdge`  
**Integration branch:** `agent/eduedge-full-academic-cbt-integration`  
**Pull request:** #19  
**Purpose:** Review Phase 6D implementation before resuming deferred integration/browser QA.

## Executive conclusion

Phase 6D has moved beyond Instructor Assignment CRUD into a connected academic-responsibility chain:

**Instructor identity → Branch eligibility → exact academic responsibility → lifecycle → operational capability → Course Schedule/Attendance/Assessment scope → Scheme of Work → curriculum delivery → Lesson Plan → teaching evidence.**

The assignment lifecycle slices already completed earlier browser QA for End, Replace / Handover, Transfer, and Prepare Next Term / Session. Later slices were implemented with automated contracts while manual QA was deferred.

This audit found several real pre-QA security, history-integrity, smart-form, and privacy weaknesses. The blocker/high-risk defects that would invalidate meaningful QA have been hardened before restarting QA. Remaining issues are classified below as production-release risks or deliberate QA targets rather than hidden defects.

PR #19 must remain draft and unmerged until the deferred QA plan is completed.

---

## Phase 6D implementation status

| Slice | Scope | Implementation | Prior browser QA | Deferred QA state |
|---|---|---:|---:|---:|
| S2A | End Assignment | Complete | Passed | Regression smoke only |
| S2B | Replace / Handover | Complete | Passed | Regression smoke only |
| S2C | Transfer Assignment | Complete | Passed | Regression smoke only |
| S2D.1 | Prepare Next Term / Session backend | Complete | Passed | Regression smoke only |
| S2D.2 | Prepare Next Term / Session manager UI | Complete | Passed | Regression smoke only |
| S2D.3 | Smart Assignment Register filters/history | Complete | Deferred | Required |
| S2E | Disable / Re-enable / Delete governance | Complete | Deferred | Required |
| S2F | Exact assignment capabilities and operational enforcement | Complete | Deferred | Required |
| S2G | Instructor identity, schedule, attendance, examiner/supervisor integrity | Complete | Deferred | Required |
| S2H | Scheme of Work, delivery, coverage, Academic Readiness | Complete | Deferred | Required |
| S2I | Lesson Planning and Teaching Evidence | Complete | Deferred | Required |

---

## What is structurally strong

### Assignment lifecycle and history

- Existing responsibility identity cannot be silently edited in place.
- Direct `enabled` mutation is blocked; governed Disable / Re-enable actions are required.
- Direct deletion is blocked; Delete Unused must prove a future record is unused, disabled, unreferenced, and history-free.
- End, Replace / Handover, Transfer, and Prepare Next Period maintain separate provenance rather than overloading one status field.
- Submitted/historical operational records are not rewritten by assignment lifecycle actions.
- Replace / Transfer / Prepare actions use server-side validation and idempotent/history-rewrite protection.
- Primary responsibility conflicts and overlapping exact assignments are validated server-side.

### Permission and scope model

- Branch access remains a broad eligibility/access layer; exact Instructor Assignment remains the specific academic-responsibility layer.
- User → Employee → Instructor resolution fails closed when identity is missing or ambiguous.
- Exact assignment capabilities are separate from Question Review / Final Approval governance.
- Assessment Plan, marks, Course Schedule, Attendance, CBT authoring, and curriculum operations have assignment-aware enforcement foundations.
- State-changing academic actions use POST boundaries and server-authoritative validation.

### Smart forms and operational UI

- Instructor Assignment Register is server-filtered and paginated rather than loading the whole assignment history into the browser.
- Cascades clear stale child values when a parent context changes.
- Readable business labels are preferred over raw internal hashes.
- Scheme and Lesson Plan workbenches derive choices from Branch/Class/Arm/Subject and exact assignment context.
- URL-persisted filtering exists on large operational registers where implemented.

### Historical academic content

- Approved Scheme of Work is immutable and versioned.
- Scheme approval snapshots readable curriculum labels.
- Scheme delivery is append-only.
- Approved Lesson Plans are immutable and snapshot readable academic context.
- Lesson Plan review uses Draft → Submitted → Approved / Returned rather than direct status manipulation.

---

## Audit findings corrected before QA

### A1 — BLOCKER — Lesson Plan horizontal authorisation

**Finding:** An existing Draft/Returned Lesson Plan accepted caller-controlled context before the original record had been authorised. A limited Instructor who obtained another record ID could attempt to rewrite it into a context they controlled.

**Correction:** Limited users are now validated against the original `get_doc_before_save()` Instructor before Scheme/context resolution. Cross-Instructor takeover is rejected before caller-provided context can make the record appear authorised.

**QA:** Explicit negative test required with two Instructor identities.

### A2 — BLOCKER — Scheme draft horizontal authorisation and handover semantics

**Finding:** Existing Scheme Draft context was mutated before authorisation. The older Scheme access check also anchored too heavily on the academic-period start date, which could incorrectly block a legitimate replacement Instructor mid-term while allowing a former Instructor to retain inappropriate write authority.

**Correction:** Existing Draft is authorised before caller context mutation. Instructor Scheme access is now based on exact assignment overlap with the Scheme period; current write authority requires an assignment effective for the current/scheduled write reference date. Capability enforcement remains layered on top.

**QA:** Test original-context takeover rejection, mid-term replacement visibility, and former-Instructor write denial.

### A3 — HIGH — Primary Branch profile save could rewrite Branch eligibility history

**Finding:** Saving an Instructor Primary Branch could select an arbitrary existing Branch eligibility row and re-enable/mark it primary, potentially reactivating historical access.

**Correction:** Only one currently effective period may be promoted to Primary. Historical and future eligibility periods are not rewritten. If no current period exists, a new current period is created. Ambiguous multiple-current-period state fails closed.

**QA:** Use an Instructor with historical + current/future Branch eligibility periods and verify dates are unchanged.

### A4 — HIGH — Broad Employee option loading

**Finding:** Instructor page loaded up to 1,000 active Employee rows, contrary to smart-form and privacy/performance rules.

**Correction:** Employee options are now dependent on Home Institution, restricted to active Employees in that Institution's ERPNext Company, bounded, cleared when Home Institution changes, and revalidated on save.

**QA:** Verify Company/Institution isolation and stale Employee clearing.

### A5 — HIGH — Inactive Instructor could become impossible to close correctly

**Finding:** Governed Disable could narrow an assignment after the Instructor became inactive, but End / Replace / Transfer source closure could still fail because normal validation demanded an active Instructor/Branch eligibility.

**Correction:** Governed lifecycle source closure may narrow/close existing history even after Instructor departure or Branch-access withdrawal. Creation, successor records, re-enable, and widening remain strict.

**QA:** Test End/Replace source closure after Instructor status becomes Left; verify no new responsibility can be created for inactive Instructor.

### A6 — HIGH — Teaching evidence privacy and attachment ownership

**Finding:** Scheme Delivery accepted an evidence URL produced by a generic upload path without sufficiently proving privacy, file ownership, allowed type/size, or binding the upload to the append-only delivery event.

**Correction:** Evidence must be a private Frappe File owned by the current user, unattached, <= 10 MB, and an allowed image/PDF/Office/text type. After delivery-log creation it is attached to that exact Scheme Delivery Log row and evidence field. UI requests private upload.

**QA:** Verify private upload, wrong-owner/external URL rejection, allowed files, size/type rejection, persistence, and open evidence permission.

### A7 — UI — Instructor Assignment History was labelled Current

**Finding:** Instructor profile returned recent historical assignments but UI labelled the section “Current Instructor Assignments.”

**Correction:** Relabelled to “Instructor Assignment History.”

**QA:** Visual/readability smoke.

---

## Remaining known risks / implementation gaps to carry through QA

These are not hidden. They are release decisions or follow-on hardening items that must be resolved or accepted explicitly before merge/production.

### R1 — HIGH — Course Schedule exact-assignment cutover is data-dependent

The existing Course Schedule compatibility path becomes strict after exact Instructor Assignment data exists in the Branch. A partially migrated Branch can therefore move from permissive legacy behavior to strict validation before every schedule has assignment coverage.

**Risk:** Production cutover can disrupt scheduling if assignment migration is incomplete.

**QA/release gate:** Academic Readiness must show assignment coverage before production cutover. Test a Branch with partial coverage. Decide before merge whether an explicit Branch-level readiness switch is required.

### R2 — HIGH — Capability enforcement is intentionally migration-safe OFF by default

`enforce_instructor_assignment_capabilities` is intentionally not switched on automatically.

**Risk:** If production readiness is not checked, a site could remain on the compatibility path longer than intended.

**QA/release gate:** QA capability management with enforcement OFF first; then turn ON deliberately and run exact Teacher/Instructor negative tests. Production activation must be a documented release step, not an implicit migration side effect.

### R3 — MEDIUM — Assignment Register crafted-filter defense-in-depth

The UI cascade is strong, but some backend filter combinations rely on final assignment-row constraints rather than fully rejecting every invalid Offering/Arm/Course cross-combination at filter-validation time.

**Risk:** Primarily confusing/empty results rather than a known data leak, but backend should ideally reject impossible filter combinations explicitly.

**QA:** Manually call crafted filter combinations and confirm no cross-Branch/cross-Class data appears. Harden further if any inconsistent row is returned.

### R4 — MEDIUM — Some option endpoints still use bounded bulk lists

The main registers are paginated, but a few manager planning/selection endpoints still have relatively high bounded option ceilings.

**Risk:** Large institutions may see slower initial option loading.

**QA:** Browser Network/Performance inspection with realistic record volume; capture payload sizes and request duration.

### R5 — MEDIUM — Bulk assignment compatibility behavior

Legacy/bulk assignment paths require regression checking against S2E lifecycle governance so an existing assignment is never silently enabled/disabled by a bulk create/edit action.

**QA:** Attempt bulk create against an existing disabled/future assignment and verify governed action guidance rather than hidden status mutation.

### R6 — MEDIUM — Branch Eligibility remains an editable governance master

Instructor Branch Eligibility periods validate overlap and Primary rules, but the product has not yet converted the entire Branch Eligibility master into an append-only lifecycle object.

**Risk:** Administrators with direct write rights can still edit eligibility period dates within normal DocType rules.

**Release decision:** Decide whether Branch Eligibility is intended to remain an editable access-governance master or become immutable history with End/Replace-style actions. Do not silently change this behavior during QA.

### R7 — MEDIUM — Scheme list pagination after permission filtering

Limited Instructor Scheme listing may return short pages because records are paged at database level then exact permission filtering is applied.

**Risk:** UX pagination inconsistency, not known data leakage.

**QA:** Test a restricted Instructor where authorised and unauthorised Schemes are interleaved.

### R8 — MEDIUM — Scheme version concurrency

Version creation is governed, but no explicit database uniqueness/locking strategy currently guarantees two concurrent “next version” requests cannot both calculate the same version number.

**QA:** Low-frequency concurrency test or later hardening before high-scale rollout.

### R9 — MEDIUM — Readable-name fallbacks

Most operational surfaces use readable labels. Some historical records can still fall back to internal IDs if their master is no longer in the current option list.

**QA:** Inspect ended/replaced/transferred/prepared assignments, Lesson Plan history, Scheme Delivery history, and cross-period links for raw hashes.

### R10 — MEDIUM — Academic Readiness coverage can be expanded

Current Academic Readiness covers Instructor assignment coverage, Instructor identity, Scheme approval/curriculum delivery, and assessment activity. It does not yet make every S2I Lesson Plan review/evidence state or the capability-enforcement production state a top-level readiness gate.

**QA/release gate:** Validate current readiness usefulness first; add Lesson Plan/capability readiness if the QA workflow shows management needs it before merge.

---

## Security/permission QA matrix

Deferred QA must exercise at least these identities:

1. `Administrator` / System Manager equivalent;
2. Academic Administrator with one permitted Branch;
3. Academic Administrator without access to another Branch;
4. Teacher/Instructor with exactly one User → Employee → Instructor identity;
5. Teacher with missing identity mapping;
6. Teacher with ambiguous mapping where test data can safely be created;
7. former/inactive Instructor with historical assignments;
8. two different Instructor users for cross-record takeover tests.

Test both UI visibility and direct API/backend rejection. Hidden buttons are not a security control.

---

## Deferred QA execution order

### QA0 — Integration baseline

- pull audited branch head;
- ensure EdgeSuite UI dependency is current;
- build EduEdge assets;
- migrate the disposable integration site twice;
- clear cache and restart;
- verify installed app versions;
- run relevant database-backed tests;
- keep `enforce_instructor_assignment_capabilities` OFF initially;
- confirm no migration/idempotency error before feature testing.

### QA1 — S2D.3 Assignment Register

- default Current + Upcoming behavior;
- presets;
- Branch → Session/Term → Offering → Arm → Subject cascade;
- lifecycle filters;
- readable search;
- pagination;
- counts/chips;
- URL persistence;
- large history;
- restricted Branch negative tests.

### QA2 — S2E Governance

- future Disable;
- Re-enable;
- Delete Unused;
- started-history rejection;
- lifecycle/provenance reference rejection;
- governance logs;
- inactive Instructor closure regression.

### QA3 — S2F Capability Manager, enforcement OFF

- capability UI only on subject-bearing valid assignments;
- dependency on View Subject Content;
- reason/user/time audit;
- optimistic concurrency;
- no Question Review/Final Approval contamination.

### QA4 — S2G Identity and teaching operations

- User → Employee → Instructor readiness;
- Employee Home Institution scoping;
- Course Schedule exact assignment;
- Attendance ownership;
- Examiner exact-subject eligibility;
- Supervisor/invigilation authority separation;
- former Instructor behavior.

### QA5 — Enable exact capability enforcement deliberately

- enable `enforce_instructor_assignment_capabilities` only after QA3/QA4 data is ready;
- Teacher positive and negative checks for Subject Content, Topic Management, CBT Authoring, Assessment Plan creation, and marks;
- Branch/Class/Arm/Subject/date cross-scope negatives;
- verify management routes remain appropriate.

### QA6 — S2H Scheme of Work / Delivery / Readiness

- draft creation;
- exact Instructor authoring;
- approval snapshots;
- immutability;
- versioning/retirement;
- mid-term handover access;
- former Instructor write denial;
- append-only delivery transitions;
- coverage reports;
- Academic Readiness.

### QA7 — S2I Lesson Plan / Teaching Evidence

- smart cascade;
- Draft save;
- duplicate guard;
- cross-Instructor takeover negative;
- Submit → Return → correct → resubmit;
- Submit → Approve;
- approval snapshots and immutability;
- linked Approved Lesson Plan on delivery;
- private evidence upload and negative file checks.

### QA8 — Broad security/regression

- cross-Institution/Branch direct API attempts;
- route/menu visibility;
- native-form bypass attempts;
- POST-only mutation checks;
- submitted Attendance/Assessment Result/history integrity;
- performance/network payload observations.

### QA9 — Previously closed lifecycle smoke

Only small regression smoke for End, Replace / Handover, Transfer, and Prepare Next Term / Session. Do not repeat the earlier full successful lifecycle QA unless a regression appears.

---

## Merge/release gate

Phase 6D should not be considered merge-ready until:

- CI remains green on the QA head;
- integration-site build and two migrations pass;
- deferred QA1–QA8 pass or produce explicitly accepted follow-up issues;
- capability enforcement cutover is deliberate and documented;
- Course Schedule partial-migration risk is resolved or explicitly governed;
- no cross-Branch, cross-Instructor, or cross-context API bypass is found;
- no submitted/historical academic record is silently mutated;
- private teaching evidence remains permission protected;
- important historical relations display readable business labels;
- PR #19 remains draft until the release gate is met.
