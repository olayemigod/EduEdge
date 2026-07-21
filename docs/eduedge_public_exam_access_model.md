# EduEdge Public Exam Access Model

## Decision

EduEdge public examinations are centrally governed ProcessEdge products. Access is granted by CoreEdge to an exact registered EduEdge product site. Deployment location does not itself grant or remove access.

The same model applies to:

- ProcessEdge shared-hosted tenants;
- customer-owned standalone sites;
- white-label deployments;
- controlled ProcessEdge development and public-exam authority sites.

A local `Administrator`, `System Manager`, school owner, server owner, or white-label operator does not automatically become an EduEdge public-exam content administrator.

## Separation of ownership

### School CBT

School CBT records belong to the local school tenant and branch:

- School Examination Centres;
- School Question Bank questions;
- School Examination templates;
- future school schedules, candidates, attempts, and academic-result integration.

These records remain available even when public-exam access is not activated, subject to the normal EduEdge product activation policy.

### EduEdge public examinations

Public examination masters remain controlled by ProcessEdge:

- EduEdge Examination Bank questions and answer keys;
- public examination templates and versions;
- catalogue and product metadata;
- centrally controlled launch, timing, marking, and result contracts;
- public-exam audit and commercial policy.

Standalone and white-label sites do not receive editable copies of central question banks or answer keys. Future schedules and attempts reference a centrally published exam/version and use signed, time-bound service contracts.

## CoreEdge capability grants

The CoreEdge feature key is:

```text
cbt_public_exam
```

Each action is activated separately for one registered `CoreEdge Service Client`:

| Capability | Purpose |
|---|---|
| `catalog` | Browse centrally published EduEdge Exams available to the tenant |
| `assign` | Assign or register eligible candidates from the product site |
| `host` | Host an EduEdge public examination at an approved school centre |
| `launch` | Create or resume signed candidate examination sessions |
| `results` | Receive signed result and reconciliation records |
| `author` | Create or govern ProcessEdge public question and template masters |

A catalogue grant does not imply hosting. Hosting does not imply authoring. Grants can be activated, suspended, expired, or revoked independently.

CoreEdge evaluates the grant only after confirming:

1. the authenticated integration user has the CoreEdge Service Client role;
2. exactly one active Service Client registration exists for that user;
3. the reported product-site identifier matches the registered site;
4. the registered tenant and EduEdge product activation are valid;
5. the exact feature/action grant is active and within its validity window.

## Runtime access versus feature access

EduEdge uses two separate CoreEdge contracts:

- **Runtime access** confirms the tenant can operate EduEdge generally.
- **Feature access** confirms a specific optional service action such as public-exam hosting or launch.

A missing public-exam grant must not disable normal school operations. Feature-access decisions always fail closed after their short cache expires, even when an ordinary runtime check is configured to warn/fail open.

## Authoring policy

Public authoring requires both:

- an explicit EduEdge role:
  - `EduEdge Super Administrator`; or
  - `EduEdge Public Exam Administrator`;
- an allowed `cbt_public_exam/author` decision from CoreEdge, or the controlled central-authority server flag.

`System Manager`, `EduEdge Administrator`, and local `Administrator` do not receive public authoring merely through their role. `Administrator` is usable as a technical bootstrap identity only when the site itself is the controlled authority or CoreEdge explicitly grants authoring.

The central ProcessEdge authoring site uses the server-side setting:

```json
{
  "eduedge_public_exam_authority": true
}
```

This flag must not be set on customer or white-label sites.

## Standalone and white-label onboarding

A standalone/white-label site is registered in central CoreEdge as one Service Client bound to:

- tenant;
- EduEdge product app;
- dedicated non-Desk integration user;
- deployment mode;
- exact site identifier;
- environment;
- API credentials.

The EduEdge site configuration keeps runtime and feature endpoints separate:

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
  "coreedge_access_decision_path": "/api/method/coreedge.api.v1.service_gateway.check_runtime_access",
  "coreedge_feature_access_decision_path": "/api/method/coreedge.api.v1.service_gateway.check_feature_access"
}
```

The runtime endpoint remains responsible for general EduEdge activation. The feature endpoint evaluates exact action grants. Credentials must be transferred through a secure channel and must not be committed to Git, documentation, support tickets, or screenshots.

## Examination centre governance

Examination Centres are non-submittable master records. Their operational lifecycle is:

```text
Draft -> Active -> Suspended -> Active
                   \-> Retired
Active ----------------> Retired
```

Only Active centres may be selected for schedules. `enabled` is retained as a hidden compatibility value derived from Centre Status.

A school centre may separately be approved to host EduEdge public examinations:

```text
Not Requested
Pending
Approved
Suspended
Revoked
```

The public-hosting status and central centre reference are controlled by ProcessEdge/CoreEdge verification. School administrators may maintain the local centre but cannot self-approve it as a public host.

## Runtime and outage policy

- CoreEdge is authoritative for public-exam capabilities.
- Allowed or blocked decisions may be cached only for the configured short TTL.
- After cache expiry, public-exam capabilities fail closed when CoreEdge is unavailable.
- School-owned CBT remains separate and is not blocked merely because a public-exam feature endpoint is unavailable, unless general EduEdge runtime access is also blocked.
- Candidate launch and answer-sync phases will use stricter signed-session and server-time controls than catalogue browsing.

## Current V0.8A boundary

V0.8A implements:

- capability evaluation and display;
- central authoring restrictions;
- exact-site remote adapter binding;
- separate runtime and feature-access contracts;
- centre lifecycle and public-hosting readiness;
- branch-safe public-master isolation.

V0.8A does not yet implement:

- public catalogue synchronization;
- central exam assignment;
- signed candidate launch tokens;
- question/answer delivery to attempts;
- result-return signatures;
- public-exam payments or wallet charging.

Those services must build on the capability contract rather than copying public masters into tenant-owned records.

## Acceptance matrix

| Site/user condition | School CBT | Public catalogue | Public hosting | Public authoring |
|---|---:|---:|---:|---:|
| Standalone, no CoreEdge connection | Allowed | Blocked | Blocked | Blocked |
| Remote site, no public grants | Allowed | Blocked | Blocked | Blocked |
| Remote site with `catalog` | Allowed | Allowed | Blocked | Blocked |
| Remote site with `catalog`, `assign`, `launch`, `results` | Allowed | Allowed | Blocked unless separately granted | Blocked |
| Remote site with `host` and verified centre | Allowed | According to grants | Allowed | Blocked |
| ProcessEdge authority site + authorised role | Allowed | Allowed | Allowed by policy | Allowed |
| Tenant System Manager without explicit grants | Allowed within branches | Blocked | Blocked | Blocked |
