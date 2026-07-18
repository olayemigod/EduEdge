# EduEdge V0.1 manual QA

## Installation

- Install ERPNext, Education, EdgeSuite UI, and EduEdge.
- Confirm CoreEdge is not installed on the EduEdge site.
- Run migrate and build both EdgeSuite UI and EduEdge.
- Confirm the EduEdge app launcher opens `/app/eduedge`.

## Setup Center

- Open EduEdge Setup Center.
- Confirm the loading state is styled.
- Confirm EdgeSuite UI loads before the EduEdge bundle.
- Temporarily remove the EdgeSuite UI asset and confirm a controlled error block appears.
- Confirm no CoreEdge credentials appear in browser responses.

## School Branch

- Create a main campus and a second campus.
- Confirm branch codes normalize to uppercase hyphenated values.
- Confirm duplicate branch codes are rejected.
- Confirm a Cost Center from another Company is rejected.
- Confirm a Warehouse from another Company is rejected.
- Mark one branch as default and verify only defaults in the same Company are cleared.
- Disable a branch and confirm it is not available for branch switching.

## Branch permissions

- Add a User Permission for one School Branch.
- Confirm the user sees only permitted branches.
- Confirm direct API switching to an unauthorized branch is rejected.
- Confirm switching branch also sets the compatible Company user default.

## Platform modes

- In standalone mode, confirm protected branch switching is allowed with `PLATFORM_DISABLED`.
- In optional remote mode with no contract path, confirm the operation continues with a warning.
- In required/fail-closed remote mode with no valid decision, confirm the mutation is blocked.
