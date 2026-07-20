# EduEdge V0.8 — Offline-Resilient CBT Foundation

## Business goal

Provide a secure CBT engine that continues saving candidate answers in the browser during temporary network loss while keeping the server authoritative for eligibility, timing, attempt identity, submission and result approval.

## Product boundary

EduEdge owns the CBT engine, question bank, exam attempts, answer sync, invigilator visibility and result handoff.

Frappe Education remains the academic system of record for Students, Student Groups, Courses, Academic Years, Academic Terms, Assessment Groups and approved Assessment Results.

CoreEdge remains a remote platform service. Protected CBT mutations use the existing EduEdge platform access guard and do not import or install CoreEdge locally.

## Implemented in V0.8 foundation

### Question bank

- branch- and course-aware objective questions;
- Single Choice, Multiple Choice and True/False types;
- validated answer-option rules;
- deterministic content hashes and version increments;
- questions used by scheduled or active exams cannot be edited or deleted.

### Exam definition

- branch, class, course, academic year and optional term context;
- server start/end window and per-attempt duration;
- audited pending-sync grace period;
- one or more questions with explicit marks;
- optional question and option randomisation;
- resume-after-refresh and auto-timeout controls;
- explicit Draft, Scheduled, Active, Closed and Cancelled lifecycle;
- exam content becomes immutable after scheduling.

### Attempts and answer snapshots

- one active attempt per student and exam;
- candidate eligibility from active Student Group membership;
- portal user must match the Student email account;
- immutable question text, option order, marks and answer-key snapshot;
- answer keys remain at permission level 1 and are never returned by the candidate API;
- server deadline is the earlier of the candidate duration and the exam closing time;
- device, session, IP hash, tab-switch and focus-violation evidence.

### Offline-resilient sync

- one deterministic answer record per attempt and question;
- monotonic client sequence numbers;
- same-sequence/same-payload requests are idempotent duplicates;
- same-sequence/changed-payload requests are conflicts and never overwrite silently;
- stale requests are rejected;
- sequence gaps are accepted but remain auditable and contribute to pending-sync visibility;
- answers saved before the deadline may sync during the configured grace period;
- every batch creates an append-only sync audit log;
- duplicate browser batch IDs return the existing batch result.

### Submission and result safety

- attempts with unresolved browser answers remain Pending Sync;
- Pending Sync attempts cannot be approved;
- objective scoring uses the immutable attempt snapshot;
- submitted or timed-out attempts produce Provisional results;
- explicit authorised approval changes the result to Approved;
- V0.8 does not yet create or mutate Frappe Education Assessment Result records.

### Invigilator visibility

The backend monitor returns every active class candidate with:

- Not Started, In Progress, Pending Sync, Submitted or Timed Out status;
- answered/total question progress;
- network state and last sync time;
- pending-answer count;
- tab-switch and focus-violation counts;
- result state.

## Out of scope for this foundation

- full LAN/offline server mode;
- subjective/essay automatic marking;
- webcam, biometric or invasive surveillance;
- candidate Vue examination page;
- IndexedDB answer queue and browser service worker;
- live invigilator EdgeSuite dashboard;
- question import wizard;
- automatic Assessment Result creation;
- Parent Portal result display;
- public past-question marketplace.

## Next implementation phase

1. Build the EdgeSuite candidate examination page.
2. Store answers in IndexedDB before every network request.
3. Detect online/offline/reconnected states.
4. Auto-sync queued answers with monotonic sequence and batch IDs.
5. Show saved-locally, synced and pending indicators per answer.
6. Resume after refresh from the server attempt plus local browser queue.
7. Build the invigilator monitor and pending-sync resolution workflow.
8. Add controlled Assessment Result handoff only after approval.

## Migration

```bash
bench --site eduedge.local migrate
```

The migration creates the CBT DocTypes and permission definitions. It does not create questions, exams, attempts, accounting entries or academic results.

## Manual QA

1. Create an active question for a branch and course.
2. Confirm invalid correct-option combinations are rejected.
3. Create a CBT Exam for a matching Student Group and Course.
4. Confirm questions from another branch or course are rejected.
5. Schedule and activate the exam through the API.
6. Start an eligible student attempt and confirm a second start resumes the same active attempt.
7. Sync one answer twice with the same sequence and payload; the second must be Duplicate.
8. Sync the same sequence with a changed payload; it must be Conflict.
9. Move beyond the server deadline and confirm the attempt becomes Pending Sync.
10. Confirm approval is blocked while pending answers remain.
11. Complete sync, submit and approve the result.
12. Confirm no Assessment Result or accounting document was created automatically.
