# EduEdge → CoreEdge V2.4 Context Normalizer

EduEdge School Branch remains the local campus/branch authority.

`eduedge.services.coreedge_context_reconciliation.get_context_reconciliation_rows()` exports School Branch identity in the CoreEdge V2.4 reconciliation shape:

- local DocType and document name;
- branch display name;
- branch code;
- Company;
- enabled state;
- current `platform_branch_id` snapshot.

The helper is read-only and deliberately does not import CoreEdge.

It does not:

- create or change CoreEdge mappings;
- write `platform_branch_id`;
- alter Branch Governance;
- alter User Branch Access or Instructor Branch Eligibility;
- switch the user's active branch;
- change branch accounting defaults.

The existing `platform_branch_id` field may later cache a confirmed CoreEdge reference, but it must never become an independent authorization source. EduEdge permission, Branch Governance and academic eligibility checks remain authoritative locally.
