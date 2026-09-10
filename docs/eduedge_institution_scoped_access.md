# EduEdge Institution-Scoped User Access

## Goal

Allow a School Administrator to manage one EduEdge Institution and every Branch or Campus under it without receiving access to another Institution owned by the same Company.

## Access hierarchy

EduEdge User Branch Access keeps its internal DocType identity for backward compatibility, but its visible assignment model now supports:

- **Company** — every enabled Institution and Branch in the selected Company.
- **Institution** — the selected Institution and every enabled Branch under it.
- **Branch** — only the selected Branch, with its parent Institution available as required context.

The role still controls what a user may do. The assignment controls where the user may do it.

## Recommended assignment

A normal School Administrator should receive an **Institution** assignment. Branch Managers, Teachers, Invigilators, Admissions Officers, and similar operational users should normally receive **Branch** assignments. Company access should remain restricted to authorised tenant or group administrators.

## Active context

Management users may operate in an Institution-wide All Branches view. Transaction screens that require a Branch must still request or derive a specific operational Branch. Institution access does not remove ERPNext Company, accounting-role, or User Permission controls.

## Migration

The post-model-sync patch maps existing records safely:

- Legacy HQ / All-Branch access becomes Company scope.
- Existing School Branch assignments remain Branch scope.
- No existing Branch assignment is widened automatically to Institution scope.
- Company and Institution are derived from the selected Branch where needed.

## Manual QA

1. Migrate and clear cache.
2. Create an Institution assignment for a School Administrator.
3. Confirm the assigned Institution is visible even when it has no Branch.
4. Confirm every enabled Branch under that Institution is visible.
5. Confirm another Institution under the same Company is hidden.
6. Create a new Branch under the assigned Institution and confirm it becomes accessible automatically.
7. Confirm a Branch assignment remains restricted to its Branch and parent Institution.
8. Confirm Company access remains explicit.
9. Confirm accounting documents still respect ERPNext Company, role, and User Permission controls.
