# EduEdge CBT V0.8A.3 — Schedule and Candidate Governance Foundation

## Status

Implemented on the integrated EduEdge foundation branch. Automated validation passed. Site migration, browser acceptance, role testing, and realistic examination workflow QA remain pending.

## Business goal

Move the existing governed CBT Question Bank and Exam Template foundation into controlled examination sittings without prematurely implementing the browser attempt and offline answer-sync engine.

This slice deliberately keeps general EduEdge settings minimal. Examination-specific controls remain on the Exam Template or the Examination Schedule, while integrity rules remain enforced in code.

## Implemented scope

### Reusable Exam Template policies

The existing `EduEdge CBT Exam Template` now owns:

- Device Change Policy;
- Attempt Review Policy.

These reusable policies become immutable after template approval and are copied into each schedule snapshot.

### Examination Schedule

`EduEdge CBT Exam Schedule` now provides:

- Approved Exam Template selection;
- school or centrally governed public-exam scope inherited from the template;
- Branch/Campus and Course context inherited from the template;
- Active Examination Centre validation;
- scheduled start and calculated end time;
- optional check-in opening time;
- candidate check-in requirement;
- candidate start mode;
- late-entry policy and grace period;
- primary invigilator validation;
- time-extension permission and maximum extension;
- authorised force-submission policy;
- immutable template policy snapshot;
- Draft, Ready, Active, Suspended, Completed, and Cancelled lifecycle;
- immutable sitting policy after activation.

School schedules remain Branch-safe. Centrally authored public schedules require ProcessEdge public-exam authoring authority.

### Candidate Assignment

`EduEdge CBT Candidate Assignment` now provides:

- one candidate assignment per schedule and Student or public-candidate reference;
- School Student or central public-candidate identity modes;
- Branch/Campus and Course context inherited from the schedule;
- Student Branch validation;
- active Student Group/Class membership validation where the template specifies a group;
- approved candidate extra time;
- calculated candidate access window;
- Draft, Eligible, Checked In, Released, Completed, Withdrawn, and Disqualified lifecycle;
- check-in opening enforcement;
- immutable candidate identity after eligibility confirmation;
- CoreEdge `assign` capability checks bound to the exact schedule record;
- additional authority-site role protection for centrally managed public assignments.

### Intervention Log

`EduEdge CBT Intervention Log` now provides an append-only audit record for:

- Device Change;
- Time Extension;
- Force Submission;
- Attempt Unlock;
- Attempt Suspension;
- Reconnection Approval;
- Manual Sync Resolution;
- Candidate Reassignment;
- Other controlled interventions.

Every intervention requires a reason, records the acting user and time, and forces attempt review. Time extensions and force-submission records are checked against the schedule policy. Logs cannot be edited or deleted through normal document operations.

### Smart forms and permissions

- Schedule forms show only Approved templates and valid Active centres.
- Candidate forms filter Students to the inherited Branch/Campus.
- School and public candidate identity fields switch according to the selected schedule.
- Candidate Assignments and Intervention Logs use Branch-aware query and record permissions.
- Public assignment visibility uses CoreEdge `assign` capability rather than public-authoring capability.
- The central authority site additionally requires an authorised ProcessEdge public-exam role.

## Safety rules preserved

- No general CBT runtime settings were added.
- No Question Bank record was recreated or duplicated.
- No approved Question or Exam Template is mutated.
- No submitted academic or accounting document is changed.
- No candidate attempt, answer, result, payment, or accounting entry is created by this slice.
- Public assignment decisions remain permission-aware, record-bound, and fail closed.
- Activated schedules and eligible candidate identities cannot be silently repurposed.

## Automated validation

The repository CI validates:

- Python compilation;
- JSON validity;
- native form JavaScript syntax;
- schedule ownership of sitting-specific controls;
- template ownership of reusable integrity policies;
- absence of exam-specific fields from general EduEdge Settings;
- Branch and public capability hooks;
- candidate eligibility and identity-lock contracts;
- append-only intervention contracts;
- record-bound CoreEdge assignment capability calls;
- authority-site public assignment role restrictions.

## Migration and local validation

Run on the EduEdge development site:

```bash
cd ~/frappe-bench
bench --site eduedge.local migrate
bench build --app eduedge
bench --site eduedge.local clear-cache
```

Then validate:

1. Create and approve a School Examination template.
2. Create a schedule and confirm Branch, Course, centre, and policies are inherited correctly.
3. Confirm only Active centres in the valid Branch are selectable.
4. Move the schedule through Draft → Ready → Active.
5. Confirm activated sitting controls cannot be changed.
6. Assign an eligible Student in the template Student Group/Class.
7. Confirm an unrelated Branch Student is rejected.
8. Confirm a Student outside the required group is rejected.
9. Confirm duplicate assignment is rejected.
10. Confirm check-in cannot occur before the configured opening time.
11. Record a permitted time extension and confirm it is append-only.
12. Confirm excessive extension and disabled force submission are rejected.
13. Test School Administrator, Education Manager, Teacher, Instructor, and CBT Invigilator visibility.
14. Test public assignment with and without the CoreEdge `assign` grant.
15. On the authority site, confirm ordinary school roles cannot manage public assignments.

## Not included

The following remain for the attempt-engine slice:

- candidate login binding and signed launch sessions;
- one active attempt per candidate;
- immutable question/option presentation snapshots per attempt;
- server-authoritative attempt timing;
- browser answer storage;
- idempotent answer synchronisation;
- pending-sync visibility and reconciliation;
- invigilator live attempt monitoring;
- objective scoring and manual-marking queues;
- result approval blocking and publication;
- EdgePay collection for paid public examinations.
