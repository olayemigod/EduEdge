# EduEdge CBT Candidate Runtime

## Status

Implemented on the stacked draft branch `agent/eduedge-cbt-attempt-engine`.

This document describes the first school-examination candidate runtime. It does not describe the future centrally hosted EduEdge public-examination launch service.

## Business goal

Allow a candidate to continue answering during temporary network failure without converting EduEdge into a full offline or LAN-server product.

The runtime must:

- save each answer in the candidate browser before network transmission;
- show whether the browser is online, unstable, or offline;
- synchronise automatically when connectivity is available;
- prevent duplicate answer creation during retries;
- resume after browser refresh in the same tab;
- use server-authoritative timing;
- lock answers when the examination time ends;
- preserve answers saved before the deadline for controlled reconciliation;
- show pending-sync status clearly to the candidate;
- keep correct answers and marking guides outside the candidate payload.

## Product boundary

### Implemented for school examinations

- Candidate launch link prepared by an authorised school user.
- Full-screen candidate examination page at `/eduedge-cbt-attempt`.
- Single Choice, Multiple Choice, True/False, Yes/No, Short Answer, Essay, and Numeric response controls.
- Free Navigation and Forward Only policies.
- Browser IndexedDB answer storage.
- Persistent pending sync batches with idempotency keys.
- Automatic sync after answer changes, periodically, and when the browser returns online.
- Browser heartbeat and server-time correction.
- Refresh recovery from cached questions and answers.
- Offline submission intent.
- Pending Sync status and automatic final reconciliation.
- Twenty-four-hour technical reconciliation window for answers whose browser timestamp is before the server cutoff.
- Mandatory attempt review after post-submission or post-timeout reconciliation.

### Deliberately blocked for public examinations

Local EduEdge tenant sites cannot prepare public-examination attempts. Public attempts require a future central signed-launch service so public question content and scoring keys are not copied into a customer-controlled database.

## Settings ownership

No new general EduEdge settings were introduced.

- Reusable examination policy remains on `EduEdge CBT Exam Template`.
- Sitting-specific timing and invigilation controls remain on `EduEdge CBT Exam Schedule`.
- Candidate-specific exceptions remain in `EduEdge CBT Intervention Log`.
- Idempotency, timing authority, browser queue schema, retry cadence, reconciliation window, and answer-key separation are enforced technical controls.

## Candidate launch flow

1. The Candidate Assignment must be a School Examination assignment with status `Released`.
2. The Examination Schedule must be `Active`.
3. An authorised staff user opens the Candidate Assignment.
4. Under **CBT**, the user selects **Prepare Candidate Attempt**.
5. EduEdge creates the Attempt, question snapshots, protected scoring keys, and one launch token.
6. The staff user copies or opens the candidate link immediately.

The link format is:

```text
https://school.example.com/eduedge-cbt-attempt#attempt=CBT-ATT-00001&token=<one-time-returned-token>
```

The token is placed in the URL fragment. It is not sent in the initial HTTP request or referrer header. The candidate page moves the token into `sessionStorage` and removes it from the visible URL. EduEdge stores only the token hash on the Attempt record.

If the link is lost, the same token cannot be displayed again. Token reissue should be implemented later as an audited intervention rather than by storing plain launch tokens.

## Browser persistence model

The browser database is named:

```text
eduedge-cbt-runtime
```

It contains three stores:

- `answers` — latest candidate answer and local/server revision state per question;
- `batches` — the exact pending sync payload and idempotency key currently being retried;
- `meta` — cached attempt state, current question, timer deadline, and submission intent.

The launch token is not stored in IndexedDB or local storage. It remains in the current tab's `sessionStorage`.

The client session identifier is stored in local storage so a normal refresh uses the same device identity.

## Answer-save sequence

For every answer change:

1. The browser captures the answer and candidate-side saved time.
2. The answer revision is written to IndexedDB.
3. The interface shows the answer as pending.
4. A sync batch is created with an idempotency key.
5. The batch is sent to the server when connectivity is available.
6. The server validates question identity, option identity, answer type, revision, and idempotency.
7. The browser marks only the sent revision as synchronised.
8. A newer local revision remains pending for the next batch.

Text and numeric answers are serialised per question. Submission and timeout wait for captured text-field writes and all in-flight IndexedDB writes before locking the attempt.

## Server timing

The server sets:

- `started_at`;
- `expires_at`;
- examination duration;
- approved extra time;
- final timeout status.

The browser displays a local countdown derived from the latest server `seconds_remaining` response. The browser countdown does not determine the official expiry.

When the browser reaches zero, it locks answer entry locally and records submission intent. The server independently finalises expired attempts through candidate API calls and a scheduled job.

## Late reconciliation

Temporary loss of connectivity may continue beyond the scheduled end. A fixed technical reconciliation window of 24 hours is available.

This is not extra examination time.

A late sync is accepted only when:

- the launch token hash remains valid;
- the request is within the technical reconciliation window;
- the attempt is in a reconcilable state;
- each answer carries a browser saved time no later than the server submission or timeout cutoff;
- revisions and idempotency checks pass.

Any post-submission or post-timeout reconciliation forces `requires_review = 1` and adds an audit reason.

## Security boundaries

- Correct option IDs, answer keys, and marking guides are stored in `EduEdge CBT Attempt Scoring Key` records.
- Candidate question snapshots contain only candidate-visible content.
- Candidate website responses do not contain scoring keys.
- Prepared and terminal attempts do not return question content from the runtime guard.
- Candidate question HTML is rendered through a basic allow-list sanitizer.
- The launch page is marked `noindex`, `nofollow`, `noarchive`, and `no-referrer`.
- Public-examination attempts are blocked on tenant sites.
- Branch and child-record access remains routed through the parent Attempt.

## Migration and deployment

Do not migrate the current `eduedge.local` site while Branch Access QA is still active.

Use a separate CBT bench/site, or wait until the Branch Access QA cycle is completed.

On the isolated CBT test site:

```bash
cd ~/frappe-bench-cbt
git -C apps/eduedge checkout agent/eduedge-cbt-attempt-engine
bench --site eduedge-cbt.local migrate
bench build --app eduedge
bench --site eduedge-cbt.local clear-cache
bench restart
```

The candidate JavaScript and CSS are normal EduEdge public assets. A build is retained in the deployment steps because the same branch also contains bundled EduEdge and EdgeSuite assets.

## Manual QA matrix

### Preparation and launch

1. Create and approve CBT questions.
2. Create and approve an Exam Template.
3. Create an Examination Schedule and activate it.
4. Create a Candidate Assignment and move it through eligibility, check-in, and release.
5. Confirm **Prepare Candidate Attempt** appears only for a released School Examination candidate.
6. Prepare the attempt and copy the candidate link.
7. Confirm a second preparation request is rejected because the candidate already has an active attempt.
8. Confirm the candidate link token disappears from the browser address after page load.

### Start and question display

9. Confirm Prepared state does not display questions.
10. Start the examination and confirm the server returns questions only after start.
11. Confirm the candidate name, timer, connection state, and pending count render correctly.
12. Confirm correct answers and marking guides are absent from browser network responses.
13. Test every supported question type.
14. Test Free Navigation.
15. Test Forward Only and confirm previous questions cannot be reopened.

### Browser saving

16. Answer a question and immediately disable the network.
17. Confirm the answer remains visible and shows pending sync.
18. Refresh the same tab while offline and confirm cached questions and answers restore.
19. Enter a long essay, type the final characters, and immediately click Submit.
20. Confirm the final characters are present in IndexedDB and later on the server.
21. Change an answer repeatedly and confirm server revision conflicts are not created.

### Synchronisation

22. Restore connectivity and confirm automatic sync without manual refresh.
23. Confirm the pending count returns to zero.
24. Retry the same saved batch and confirm the server returns an idempotent replay.
25. Reuse an idempotency key with different content and confirm rejection.
26. Simulate an unstable connection and confirm the batch remains in IndexedDB for retry.

### Submission and timeout

27. Submit online with no pending answers and confirm status `Submitted`.
28. Submit offline and confirm submission intent remains visible.
29. Reconnect and confirm answers sync before final submission.
30. Allow the timer to reach zero while online and confirm server timeout handling.
31. Allow the timer to reach zero while offline, reconnect, and confirm only pre-deadline answers reconcile.
32. Confirm late reconciliation forces attempt review.
33. Attempt to sync an answer timestamped after the server cutoff and confirm rejection.
34. Attempt reconciliation after the 24-hour technical window and confirm token expiry.

### Permissions and isolation

35. Confirm a user without Candidate Assignment write permission cannot prepare an attempt.
36. Confirm users outside the Branch cannot list or open the Attempt.
37. Confirm Students, Parents, Teachers, and Invigilators cannot open scoring-key records.
38. Confirm a normal tenant cannot prepare a public-examination attempt.

## Remaining implementation

- live invigilator dashboard and interruption alerts;
- audited token reissue or session recovery;
- objective scoring and manual-marking workflow;
- result review, approval, and publication blocking;
- candidate accessibility acceptance testing;
- public-examination signed launch through CoreEdge;
- EdgePay collection for paid public examinations.
