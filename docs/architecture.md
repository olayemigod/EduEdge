# EduEdge architecture

## Product boundary

EduEdge owns education-specific workflows, validations, pages, APIs, reports, and extensions.

It builds on Frappe Education rather than duplicating Student, Guardian, Instructor, Program, Course, Academic Year, Academic Term, admissions, enrolment, attendance, fees, or assessment masters.

## Runtime composition

```text
Frappe
├── ERPNext
│   └── Frappe Education
├── EdgeSuite UI
└── EduEdge

External platform service:
CoreEdge
```

EdgeSuite UI is installed locally on the product site. EduEdge pages must render without importing CoreEdge or EdgeSuite UI source files.

CoreEdge is reached only through the EduEdge platform client. The initial remote client has no invented default endpoint paths. The central contract must be configured explicitly when the CoreEdge HTTP service is available.

## Platform modes

- `standalone`: local product operation; platform access returns `PLATFORM_DISABLED`.
- `remote`: EduEdge calls the configured central CoreEdge contract.

Legacy `shared_hosted` and `white_label` configuration values normalize to `remote`.

## Failure behaviour

Protected EduEdge mutations use cached access decisions when the remote service is temporarily unavailable.

- Required or fail-closed mode blocks when no valid decision exists.
- Optional fail-open mode continues with a warning.
- Read-only setup and reporting pages should remain usable.

## School branch model

`EduEdge School Branch` provides the local operational company/campus layer. It links to ERPNext Company, Cost Center, Warehouse, and Address without creating accounting records automatically.

The branch service validates permissions on the server and stores only a user-scoped active-branch default.
