# EduEdge Partner Implementation Status

**Product:** EduEdge Education Management and School Intelligence Platform  
**Publisher:** ProcessEdge Solutions Limited  
**Current stage:** Core school operations, academic operations pages, and CBT definition foundation  
**Last updated:** 28 July 2026  
**Status:** Automated validation passed; local build, migration, browser and realistic workflow acceptance remain pending.

## Implemented academic operations page batch

EduEdge now has a connected EdgeSuite workflow for:

1. **Academic Foundation** — Institution-owned Academic Sections, Academic Levels, progression pathways, Institution Academic Calendars, current-period visibility and readiness warnings.
2. **Programmes / Classes** — Institution-aware catalogue, bounded search, course-row and active-Offering counts, safe quick maintenance, and native full forms for advanced curriculum rows.
3. **Programme Offerings** — Branch-first delivery context, year and period, Level, Cohort, Study Mode, Delivery Mode, dates, admission and enrollment availability, lifecycle-based capacity, and identity-lock visibility.
4. **Daily Academic Operations** — Classes or Student Groups, Course Schedules, Instructor assignment, Room usage, attendance completion, draft attendance and submitted-attendance protection.

## Existing product foundation

The broader implemented foundation includes:

- ERPNext Company → EduEdge Institution → Branch / Campus hierarchy;
- Primary School, Secondary School, Tertiary Institution and Training Centre terminology;
- Branch-aware admission, applicants, students, enrollment and fee context;
- append-only enrollment lifecycle and safe capacity handling;
- assessment, result approval and publication;
- report cards and manual progression review;
- governed CBT centres, questions, responsibilities, templates, schedules, candidate assignments and intervention logs;
- Branch governance, role permissions, Setup Center and Training Centre; and
- remote CoreEdge service boundaries without installing CoreEdge inside EduEdge.

## Safety commitments

- Standard Frappe Education DocTypes remain unchanged.
- Submitted Program Enrollment, Attendance, result and accounting records are not silently mutated.
- Programme Offering identity cannot change after operational use.
- Branch and Institution access remains backend-authoritative.
- Dependent field filtering is backed by server validation.
- Ambiguous legacy Institution ownership is not guessed.
- Capacity uses current append-only enrollment lifecycle status.

## Automated validation

The latest branch passed:

- Python compilation;
- JSON validation;
- all registered frontend entry-script checks; and
- the complete pure contract suite.

## Local acceptance still required

1. Pull the latest Academic Operations page branch.
2. Build EduEdge assets.
3. Migrate `eduedge.local`.
4. Clear cache.
5. Test Academic Foundation readiness and calendars.
6. Test Programme/Class catalogue filtering and quick maintenance.
7. Test Programme Offering capacity, availability and identity locks.
8. Test daily schedules, Rooms and attendance readiness.
9. Test Primary, Secondary, Tertiary and Training Centre terminology.
10. Test restricted roles, Institution scope and Branch permissions.
11. Verify submitted academic and accounting safety.
12. Retest EdgeSuite quick-editor and dialog rendering.

## Important limitations

- Offline-Resilient CBT candidate attempts, browser answer saving, network synchronisation, pending-sync visibility, live invigilation, scoring execution and result approval blocking remain separate planned work.
- Full EduEdge billing and EdgePay integration remain planned.
- Automatic promotion, class movement and Program Enrollment creation remain intentionally excluded.
