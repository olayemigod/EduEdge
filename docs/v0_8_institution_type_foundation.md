# EduEdge V0.8 — Company, Institution, Branch, and Terminology Foundation

## Business model

EduEdge now uses a three-level education ownership model:

```text
ERPNext Company
    └── EduEdge Institution
            └── EduEdge School Branch / Campus
```

- **Company** is the legal and accounting owner.
- **Institution** is the identifiable school, university, polytechnic, college, or training centre.
- **Branch / Campus** is an operational location belonging to one Institution.

One Company may own several Institutions of different types, and every Institution may own several Branches.

## Institution Type ownership

Institution Type belongs to `EduEdge Institution`, not independently to a Branch. EduEdge seeds and protects these V0.8 types:

- Primary School
- Secondary School
- Tertiary Institution
- Training Centre

A Branch stores a synchronized read-only Institution Type for filtering and reporting, but the linked Institution remains authoritative.

## Runtime resolution

EduEdge resolves terminology in this order:

1. Document or explicitly selected Branch → linked Institution
2. Active Branch → linked Institution
3. Explicit Institution
4. Company fallback Institution Type
5. Secondary School system fallback

Standard Frappe DocType names, routes, APIs, and database identities remain unchanged.

## Migration

Existing Branches are grouped only by their existing Company and Institution Type. EduEdge creates one reviewable migration Institution for each distinct Company/type pair, links the relevant Branches, and marks the generated Institution for administrator review.

Migration does not infer institution identity from Branch names, addresses, academic records, or similar text. Administrators may rename generated Institutions or split Branches into additional Institutions after migration.

## EdgeSuite UI

`/app/eduedge-institution-structure` is the primary administration surface. It supports:

- optional Company fallback;
- Institution creation and maintenance;
- seeded Institution Type selection;
- Branch-to-Institution assignment;
- hierarchy visibility;
- migrated-record review indicators;
- terminology preview.

Native Frappe forms remain available as administrative fallbacks.

## Safety

- No submitted academic, assessment, or accounting documents are mutated.
- Tenants cannot create or edit seeded Institution Type definitions.
- Branch Institution Type cannot diverge from its Institution.
- Company changes are blocked after linked Branches exist.
- Existing CoreEdge product identity ownership is unchanged.
