# EduEdge MVP Result Engine V1

## Goal

Extend the existing Frappe Education assessment/result stack into configurable terminal and annual result composition without creating a shadow marks ledger.

## Source of truth

- Frappe Education `Assessment Group`, `Assessment Plan`, `Assessment Result` and `Grading Scale` remain authoritative.
- EduEdge Result Profile only describes how submitted native Assessment Results are composed, aggregated and displayed.
- CBT continues to sync into native Assessment Results before it reaches this engine.

## Foundation added in this slice

- `EduEdge Result Profile` with configurable components and native Assessment Group source mappings.
- Recursive Assessment Group leaf resolution for nested assessment trees.
- Generic report metrics with configurable label, calculation basis, display representation and Terminal/Annual visibility.
- No hardcoded CHS/CLS/CAS fields. Great Oxford-style CHS/CLS/CAS can later be delivered as a preset using Class Highest/Class Lowest/Class Average metrics.
- Upgrade-safe native fields:
  - Grading Scale Interval report remark;
  - Academic Term report label;
  - Academic Term annual-result weight;
  - Assessment Result score state to distinguish a genuine numeric zero from Absent, Exempt and Not Offered.
- Terminal composition service over native submitted result rows.
- Generic class-statistics calculation helpers.
- Optional Result Profile + Terminal/Annual mode on the existing EduEdge Result Publication record.
- Branch/Institution permission scoping for Result Profiles.

## Backward compatibility

Historical Result Publications do not require a Result Profile. Existing Assessment Results are not changed or resubmitted. Existing numeric results default to the Scored state after migration.

## Next slices

1. Publication-readiness integration using Result Profile blockers and unmapped assessment groups.
2. Annual/cumulative period aggregation with Academic Term labels and weights.
3. Generic cohort statistics materialisation.
4. Immutable publication snapshots.
5. Report Cards V2 and Terminal/Annual print presets.
