# EduEdge CBT Schedule and Candidate Governance Status

**Date:** 27 July 2026  
**Status:** Implemented in code; acceptance QA pending  
**Parent implementation record:** `docs/partner/eduedge_implementation_status.md`

## Partner-facing update

EduEdge now includes the controlled examination-sitting layer that follows the previously implemented Question Bank and Exam Template foundation.

Implemented capabilities include:

- creation of Branch-aware CBT examination schedules from Approved templates;
- inheritance and locking of examination timing, navigation, resume, randomisation, marking, result-release, device-change, and review policies;
- examination centre, invigilator, check-in, candidate start, late-entry, extension, and force-submission controls at the individual sitting level;
- School Student eligibility assignment with Branch and Student Group/Class validation;
- centrally governed public-candidate assignment using the CoreEdge public-exam `assign` capability;
- append-only intervention records requiring reasons and attempt review;
- prevention of silent changes to activated schedules and eligible candidate identity;
- Branch-safe list and record permissions.

This delivery does **not** mean the complete Offline-Resilient CBT attempt engine is finished. Candidate browser launch, live attempts, answer saving, offline synchronisation, scoring execution, result approval, and paid public-exam collection remain pending.

## Acceptance required

Before this capability is represented as production-ready, ProcessEdge must complete:

- migration and build on `eduedge.local`;
- native-form browser testing;
- restricted-role and Branch-permission testing;
- school schedule and candidate eligibility workflow testing;
- CoreEdge public assignment grant testing;
- confirmation that no existing CBT Question, Exam Template, Institution, academic, result, or accounting records are altered incorrectly.
