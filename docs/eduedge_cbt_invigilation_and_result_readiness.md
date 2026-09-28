# EduEdge CBT Invigilation and Result Readiness

## Scope

This layer provides permission-safe live examination monitoring and reusable result-readiness gates. It does not score, approve, publish, or sync results into Frappe Assessment Result.

## Invigilation view

Route:

```text
/app/eduedge-cbt-invigilation
```

The page supports:

- Branch and Examination Schedule filtering;
- automatic refresh every 15 seconds;
- candidate and attempt status;
- heartbeat age and connection health;
- server-saved answer count;
- browser-reported pending answer count;
- server-derived remaining time;
- integrity-review visibility;
- direct navigation to the Attempt or Candidate Assignment.

The API deliberately excludes answer payloads, correct option IDs, answer keys, and marking guides.

A live attempt is treated as stale when no heartbeat has been received for more than 90 seconds. This is a fixed technical monitoring threshold, not a school setting.

## Result-readiness gates

`eduedge.cbt.result_readiness.get_result_readiness(exam_schedule)` returns two decisions:

- `ready_for_result_processing`;
- `ready_for_result_approval`.

Operational result processing is blocked when any of the following exists:

- no active candidate assignments;
- no prepared attempts;
- eligible or released candidates without an attempt;
- Prepared, In Progress, Pending Sync, or Timed Out attempts;
- unresolved browser answer counts;
- attempts requiring integrity review;
- attempts whose state is not ready for result processing.

Result approval is additionally blocked until every relevant latest attempt is `Scored`.

### Server-timeout reconciliation hold

A server-only timeout cannot prove that an offline browser has no newer local answers. For school CBT with auto-submit enabled:

- the server places the attempt in `Pending Sync` at timeout even when its last reported pending count is zero;
- an online active browser flushes its local queue and may immediately confirm zero pending, which moves the attempt to `Auto Submitted`;
- if pre-cutoff answers arrive after timeout, the attempt remains integrity-review controlled before scoring;
- if the browser never returns, the attempt stays result-blocking for the 24-hour reconciliation window;
- after that deadline, an authorised reviewer may explicitly accept a zero-pending server snapshot for scoring;
- attempts with a non-zero pending count remain blocked after the deadline until those pending answers are resolved.

This prevents scoring from closing the reconciliation endpoint before valid offline answers have had a chance to reach the server.

Future scoring, approval, and publication actions must call:

```python
from eduedge.cbt.result_readiness import (
    assert_result_processing_ready,
    assert_result_approval_ready,
)
```

The guard is server-side and must not be replaced with a frontend-only check.

## Permissions

The route appears only when the permission manifest grants read access to at least one of:

- `EduEdge CBT Exam Schedule`;
- `EduEdge CBT Candidate Assignment`;
- `EduEdge CBT Attempt`.

Record visibility remains constrained by the existing Branch and public-examination permission hooks.

## QA boundary

The implementation is on the isolated CBT attempt branch. Do not migrate the current `eduedge.local` Branch Access QA site. Use a separate CBT bench/site or wait until the Branch Access QA cycle is complete.
