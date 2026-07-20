# ProcessEdge Support, Diagnostics and Upgrades

Support work must preserve ERPNext accounting truth, Frappe permissions, EduEdge academic truth, branch isolation, and CoreEdge access controls. Avoid broad rewrites when a focused correction is sufficient.

## Diagnostic flow

```mermaid
flowchart TD
    A[Capture tenant, user, role, branch, route and exact error] --> B[Reproduce with the least privilege needed]
    B --> C{Which layer failed?}
    C -->|Platform| D[Check CoreEdge health, context and access decision]
    C -->|Product| E[Check EduEdge API, validation, workflow and assets]
    C -->|Frappe| F[Check permissions, hooks, cache, workers and migrations]
    C -->|Data| G[Check branch, company, duplicates and record state]
    D --> H[Apply smallest safe correction]
    E --> H
    F --> H
    G --> H
    H --> I[Run focused and regression tests]
    I --> J[Build, migrate, clear cache and verify by role]
    J --> K[Document and communicate closure]
```

## Capture useful context

Record the site, user role, active branch, route, document state, time, exact action, error text, browser console details, network request, and relevant server log. Remove passwords and secrets before sharing evidence.

## Protect business truth

- Do not mutate submitted accounting documents.
- Do not rewrite approved or published academic evidence without an authorised correction workflow.
- Do not bypass branch or tenant checks to make a test pass.
- Use permission-aware APIs and idempotent patches.

## Upgrade sequence

1. Review repository status and current branches.
2. Back up the site and confirm recovery ownership.
3. Pull only the intended branch or merged main line.
4. Build required apps in dependency order.
5. Run migration and clear caches.
6. Run focused tests and relevant regressions.
7. Verify browser behaviour for affected roles and branches.
8. Record files changed, tests, migrations, risks, and follow-up work.

## Closure

Confirm the client-visible result, not merely that a command succeeded. State any skipped tests or cloud-only verification clearly.

## Practice Exercise

- Diagnose a simulated missing-product-bundle error without changing business data.
- Explain how to distinguish CoreEdge denial from an EduEdge permission error.
- Write an upgrade checklist for EdgeSuite UI and EduEdge.
- Produce a concise closure note listing tests, migrations, risk, and remaining QA.
