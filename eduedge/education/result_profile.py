from __future__ import annotations

import hashlib
import json
import re

import frappe
from frappe import _
from frappe.utils import cint, flt

COMPONENT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

METRIC_KEYS = {"Class Highest", "Class Lowest", "Class Average"}
METRIC_BASES = {
	"Current Term Raw Score",
	"Current Term Percentage",
	"Year-to-Date Cumulative Raw Score",
	"Year-to-Date Cumulative Percentage",
	"Annual Cumulative Raw Score",
	"Annual Cumulative Percentage",
	"Annual Average Percentage",
}
PERCENTAGE_BASES = {
	"Current Term Percentage",
	"Year-to-Date Cumulative Percentage",
	"Annual Cumulative Percentage",
	"Annual Average Percentage",
}
METRIC_DISPLAY_TYPES = {"Raw Score", "Percentage", "Number"}
ANNUAL_AGGREGATION_METHODS = {
	"Equal Average of Eligible Terms",
	"Weighted Average",
	"Raw Cumulative",
}
OVERALL_CALCULATION_METHODS = {
	"Average of Subject Percentages",
	"Aggregate Score Percentage",
}
MISSING_RESULT_POLICIES = {"Block Publication", "Exclude from Denominator"}
ABSENCE_POLICIES = {"Block Publication", "Exclude from Denominator", "Treat as Zero"}


def validate_result_profile(doc) -> None:
	assert_result_profile_mutable(doc)
	_validate_historical_scope_identity(doc)
	_validate_scope(doc)
	_validate_profile_name_scope(doc)
	_validate_calculation_settings(doc)
	_validate_components(doc)
	_validate_sources(doc)
	_validate_metrics(doc)
	_validate_default(doc)



def _validate_historical_scope_identity(doc) -> None:
	"""Keep the Institution/Branch identity stable after a profile has published history."""
	if doc.is_new():
		return
	if not any(doc.has_value_changed(fieldname) for fieldname in ("institution", "school_branch")):
		return
	published = frappe.db.exists(
		"EduEdge Result Publication",
		{"result_profile": doc.name, "status": "Published"},
	)
	if published:
		frappe.throw(
			_(
				"Result Profile Institution/Branch scope cannot change after published results exist. Create a new Result Profile for the new scope."
			),
			frappe.ValidationError,
		)

def assert_result_profile_mutable(doc) -> None:
	if doc.is_new():
		return
	locked = frappe.db.exists(
		"EduEdge Result Publication",
		{
			"result_profile": doc.name,
			"status": ["in", ["Pending Approval", "Approved"]],
		},
	)
	if locked:
		frappe.throw(
			_("Result Profile cannot be changed while Result Publication {0} is pending approval or approved. Reject/publish that publication first.").format(locked),
			frappe.ValidationError,
		)


def validate_publication_profile(doc) -> None:
	"""Validate profile-driven scope while preserving legacy Assessment Group publications."""
	if doc.get("result_profile") and doc.get("assessment_group"):
		frappe.throw(
			_("Select either a Result Profile or an Assessment Group, not both."),
			frappe.ValidationError,
		)
	if not doc.get("result_profile") and not doc.get("assessment_group"):
		frappe.throw(
			_("Select a Result Profile or Assessment Group."),
			frappe.ValidationError,
		)
	if not doc.get("result_profile"):
		return

	profile = frappe.get_doc("EduEdge Result Profile", doc.result_profile)
	if not profile.is_active and not doc.get("supersedes_publication"):
		frappe.throw(_("Select an active Result Profile."), frappe.ValidationError)

	branch = frappe.db.get_value(
		"EduEdge School Branch",
		doc.school_branch,
		["institution", "enabled"],
		as_dict=True,
	)
	if not branch or not branch.enabled:
		frappe.throw(_("Result Publication requires an enabled School Branch / Campus."), frappe.ValidationError)
	if profile.institution != branch.institution:
		frappe.throw(
			_("Result Profile must belong to the same Institution as the Result Publication."),
			frappe.ValidationError,
		)
	if profile.school_branch and profile.school_branch != doc.school_branch:
		frappe.throw(
			_("This Result Profile is restricted to a different School Branch / Campus."),
			frappe.ValidationError,
		)

	result_mode = doc.get("result_mode") or "Terminal"
	if result_mode == "Annual" and doc.academic_term:
		frappe.throw(
			_("Annual Result Publications must use the Academic Year scope without a single Academic Term."),
			frappe.ValidationError,
		)
	if result_mode == "Annual" and not doc.result_profile:
		frappe.throw(_("Annual Result Publications require a Result Profile."), frappe.ValidationError)


def get_result_profile_config(name: str) -> dict:
	doc = frappe.get_doc("EduEdge Result Profile", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"profile_name": doc.profile_name,
		"institution": doc.institution,
		"school_branch": doc.school_branch,
		"grading_scale": doc.grading_scale,
		"score_precision": cint(doc.score_precision),
		"overall_calculation_method": doc.overall_calculation_method,
		"annual_aggregation_method": doc.annual_aggregation_method,
		"minimum_eligible_periods": cint(doc.minimum_eligible_periods),
		"missing_result_policy": doc.missing_result_policy,
		"absence_policy": doc.absence_policy,
		"presentation": {
			"terminal_report_title": doc.terminal_report_title or "Terminal Report",
			"annual_report_title": doc.annual_report_title or "Annual Result",
			"show_student_photo": bool(doc.show_student_photo),
			"show_attendance": bool(doc.show_attendance),
			"show_comments": bool(doc.show_comments),
			"show_progression": bool(doc.show_progression),
			"show_grading_legend": bool(doc.show_grading_legend),
			"show_next_period_date": bool(doc.show_next_period_date),
			"show_report_signatory": bool(doc.show_report_signatory),
			"show_official_stamp": bool(doc.show_official_stamp),
			"show_verification_qr": bool(doc.show_verification_qr),
		},
		"components": [
			{
				"component_key": row.component_key,
				"component_label": row.component_label,
				"target_maximum_score": flt(row.target_maximum_score),
				"required": bool(row.required),
				"sequence": cint(row.sequence),
				"show_on_terminal": bool(row.show_on_terminal),
				"show_on_annual": bool(row.show_on_annual),
			}
			for row in sorted(doc.components, key=lambda row: (cint(row.sequence), row.idx))
		],
		"component_sources": [
			{
				"component_key": row.component_key,
				"assessment_group": row.assessment_group,
				"sequence": cint(row.sequence),
				"leaf_assessment_groups": resolve_assessment_group_leaves(row.assessment_group),
			}
			for row in sorted(doc.component_sources, key=lambda row: (cint(row.sequence), row.idx))
		],
		"metrics": [
			{
				"metric_key": row.metric_key,
				"display_label": row.display_label,
				"calculation_basis": row.calculation_basis,
				"display_as": row.display_as,
				"decimal_places": cint(row.decimal_places),
				"sequence": cint(row.sequence),
				"show_on_terminal": bool(row.show_on_terminal),
				"show_on_annual": bool(row.show_on_annual),
			}
			for row in sorted(doc.metrics, key=lambda row: (cint(row.sequence), row.idx))
		],
	}



def serialize_result_profile_config(config: dict) -> str:
	return json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)


def set_publication_result_profile_config(publication, config: dict | None) -> dict | None:
	if not config:
		publication.set("result_profile_config_json", None)
		publication.set("result_profile_config_hash", None)
		return None
	payload = serialize_result_profile_config(config)
	publication.set("result_profile_config_json", payload)
	publication.set(
		"result_profile_config_hash",
		hashlib.sha256(payload.encode("utf-8")).hexdigest(),
	)
	return config


def get_publication_result_profile_config(publication) -> dict | None:
	"""Return the exact calculation profile assigned to one publication.

	New governed publications persist the approved profile configuration on the
	publication. Historical publications created before that field existed recover
	the profile from an immutable Published Result Snapshot when available.
	"""
	if not publication or not publication.get("result_profile"):
		return None
	raw = publication.get("result_profile_config_json")
	if raw:
		expected_hash = str(publication.get("result_profile_config_hash") or "").strip()
		actual_hash = hashlib.sha256(str(raw).encode("utf-8")).hexdigest()
		if expected_hash and expected_hash != actual_hash:
			frappe.throw(
				_("Result Publication profile configuration integrity check failed."),
				frappe.ValidationError,
			)
		try:
			return json.loads(raw)
		except (TypeError, ValueError):
			frappe.throw(
				_("Result Publication profile configuration is invalid."),
				frappe.ValidationError,
			)

	if publication.get("name") and frappe.db.exists("DocType", "EduEdge Published Result Snapshot"):
		snapshot_json = frappe.db.get_value(
			"EduEdge Published Result Snapshot",
			{"result_publication": publication.get("name")},
			"payload_json",
		)
		if snapshot_json:
			try:
				profile = (json.loads(snapshot_json) or {}).get("profile")
			except (TypeError, ValueError):
				profile = None
			if profile:
				return profile

	return get_result_profile_config(publication.get("result_profile"))


def freeze_publication_result_profile_config(publication, *, force_current: bool = False) -> dict | None:
	if not publication.get("result_profile"):
		return set_publication_result_profile_config(publication, None)
	if not force_current and publication.get("result_profile_config_json"):
		return get_publication_result_profile_config(publication)
	if publication.get("supersedes_publication") and not force_current:
		source = frappe.get_doc("EduEdge Result Publication", publication.supersedes_publication)
		return set_publication_result_profile_config(
			publication,
			get_publication_result_profile_config(source),
		)
	return set_publication_result_profile_config(
		publication,
		get_result_profile_config(publication.result_profile),
	)

def resolve_assessment_group_leaves(assessment_group: str) -> list[str]:
	"""Resolve all leaf Assessment Groups recursively."""
	if not assessment_group:
		return []
	group = frappe.db.get_value(
		"Assessment Group",
		assessment_group,
		["name", "is_group", "lft", "rgt"],
		as_dict=True,
	)
	if not group:
		frappe.throw(
			_("Assessment Group {0} does not exist.").format(assessment_group),
			frappe.DoesNotExistError,
		)
	if not group.is_group:
		return [group.name]
	return frappe.get_all(
		"Assessment Group",
		filters={"lft": [">", group.lft], "rgt": ["<", group.rgt], "is_group": 0},
		pluck="name",
		order_by="lft asc",
	)


def get_component_source_index(profile: str | dict) -> dict[str, str]:
	config = get_result_profile_config(profile) if isinstance(profile, str) else profile
	index: dict[str, str] = {}
	for source in config.get("component_sources") or []:
		for leaf in source.get("leaf_assessment_groups") or []:
			existing = index.get(leaf)
			if existing and existing != source["component_key"]:
				frappe.throw(
					_("Assessment Group {0} is mapped to more than one Result Component.").format(leaf),
					frappe.ValidationError,
				)
			index[leaf] = source["component_key"]
	return index


def _validate_profile_name_scope(doc) -> None:
	profile_name = (doc.profile_name or "").strip()
	if not profile_name:
		frappe.throw(_("Result Profile Name is required."), frappe.ValidationError)
	doc.profile_name = profile_name
	filters = {
		"name": ["!=", doc.name],
		"profile_name": profile_name,
		"institution": doc.institution,
		"school_branch": doc.school_branch if doc.school_branch else ["is", "not set"],
	}
	duplicate = frappe.db.exists("EduEdge Result Profile", filters)
	if duplicate:
		frappe.throw(
			_("Result Profile {0} already uses this name in the same Institution and Branch scope.").format(
				duplicate
			),
			frappe.DuplicateEntryError,
		)


def _validate_scope(doc) -> None:
	if not doc.grading_scale:
		frappe.throw(_("Select the official Grading Scale for this Result Profile."), frappe.ValidationError)
	institution = frappe.db.get_value(
		"EduEdge Institution", doc.institution, ["name", "enabled"], as_dict=True
	)
	if not institution or not institution.enabled:
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
	if doc.grading_scale:
		grading_meta = frappe.get_meta("Grading Scale")
		if grading_meta.has_field("eduedge_institution"):
			grading_institution = frappe.db.get_value(
				"Grading Scale", doc.grading_scale, "eduedge_institution"
			)
			if grading_institution != doc.institution:
				frappe.throw(
					_("Grading Scale must belong to the selected Institution."),
					frappe.ValidationError,
				)

	if doc.school_branch:
		branch = frappe.db.get_value(
			"EduEdge School Branch",
			doc.school_branch,
			["institution", "enabled"],
			as_dict=True,
		)
		if not branch or not branch.enabled:
			frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
		if branch.institution != doc.institution:
			frappe.throw(
				_("Result Profile Branch / Campus must belong to the selected Institution."),
				frappe.ValidationError,
			)


def _validate_calculation_settings(doc) -> None:
	if doc.overall_calculation_method not in OVERALL_CALCULATION_METHODS:
		frappe.throw(_("Invalid overall result calculation method."), frappe.ValidationError)
	if doc.annual_aggregation_method not in ANNUAL_AGGREGATION_METHODS:
		frappe.throw(_("Invalid annual aggregation method."), frappe.ValidationError)
	if doc.missing_result_policy not in MISSING_RESULT_POLICIES:
		frappe.throw(_("Invalid missing-result policy."), frappe.ValidationError)
	if doc.absence_policy not in ABSENCE_POLICIES:
		frappe.throw(_("Invalid absence policy."), frappe.ValidationError)
	if cint(doc.minimum_eligible_periods) < 1:
		frappe.throw(_("Minimum Eligible Periods must be at least 1."), frappe.ValidationError)
	if not 0 <= cint(doc.score_precision) <= 6:
		frappe.throw(_("Score Precision must be between 0 and 6."), frappe.ValidationError)


def _validate_components(doc) -> None:
	if not doc.components:
		frappe.throw(_("Add at least one Result Component."), frappe.ValidationError)
	keys: set[str] = set()
	for row in doc.components:
		key = (row.component_key or "").strip().lower()
		if not COMPONENT_KEY_PATTERN.fullmatch(key):
			frappe.throw(
				_("Component Key {0} must use lowercase letters, numbers and underscores only.").format(
					row.component_key or _("(blank)")
				),
				frappe.ValidationError,
			)
		row.component_key = key
		if key in keys:
			frappe.throw(_("Result Component {0} appears more than once.").format(key), frappe.ValidationError)
		keys.add(key)
		if flt(row.target_maximum_score) < 0:
			frappe.throw(_("Target Maximum Score cannot be negative."), frappe.ValidationError)


def _validate_sources(doc) -> None:
	component_keys = {row.component_key for row in doc.components}
	seen_groups: set[str] = set()
	if not doc.component_sources:
		frappe.throw(_("Map at least one Assessment Group to a Result Component."), frappe.ValidationError)
	assessment_group_meta = frappe.get_meta("Assessment Group")
	for row in doc.component_sources:
		row.component_key = (row.component_key or "").strip().lower()
		if row.component_key not in component_keys:
			frappe.throw(
				_("Assessment source Component Key {0} is not defined in Result Components.").format(
					row.component_key or _("(blank)")
				),
				frappe.ValidationError,
			)
		if assessment_group_meta.has_field("eduedge_institution"):
			group_institution = frappe.db.get_value(
				"Assessment Group", row.assessment_group, "eduedge_institution"
			)
			if group_institution != doc.institution:
				frappe.throw(
					_("Assessment Group {0} must belong to the selected Institution.").format(
						row.assessment_group
					),
					frappe.ValidationError,
				)
		if row.assessment_group in seen_groups:
			frappe.throw(
				_("Assessment Group {0} is mapped more than once.").format(row.assessment_group),
				frappe.ValidationError,
			)
		seen_groups.add(row.assessment_group)
		resolve_assessment_group_leaves(row.assessment_group)

	leaf_owners: dict[str, str] = {}
	for row in doc.component_sources:
		for leaf in resolve_assessment_group_leaves(row.assessment_group):
			owner = leaf_owners.get(leaf)
			if owner and owner != row.component_key:
				frappe.throw(
					_("Assessment Group leaf {0} resolves into multiple Result Components.").format(leaf),
					frappe.ValidationError,
				)
			leaf_owners[leaf] = row.component_key


def _validate_metrics(doc) -> None:
	seen: set[tuple[str, str]] = set()
	for row in doc.metrics:
		if row.metric_key not in METRIC_KEYS:
			frappe.throw(_("Invalid report statistic."), frappe.ValidationError)
		if row.calculation_basis not in METRIC_BASES:
			frappe.throw(_("Invalid statistic calculation basis."), frappe.ValidationError)
		if row.display_as not in METRIC_DISPLAY_TYPES:
			frappe.throw(_("Invalid statistic display type."), frappe.ValidationError)
		if not (row.display_label or "").strip():
			frappe.throw(_("Every enabled report statistic needs a Display Label."), frappe.ValidationError)
		if not 0 <= cint(row.decimal_places) <= 6:
			frappe.throw(_("Metric decimal places must be between 0 and 6."), frappe.ValidationError)
		if row.display_as == "Percentage" and row.calculation_basis not in PERCENTAGE_BASES:
			frappe.throw(
				_("Percentage display requires a percentage calculation basis."),
				frappe.ValidationError,
			)
		key = (row.metric_key, row.calculation_basis)
		if key in seen:
			frappe.throw(
				_("Statistic {0} with basis {1} appears more than once.").format(*key),
				frappe.ValidationError,
			)
		seen.add(key)


def _validate_default(doc) -> None:
	if not doc.is_default or not doc.is_active:
		return
	filters = {
		"name": ["!=", doc.name],
		"institution": doc.institution,
		"school_branch": doc.school_branch if doc.school_branch else ["is", "not set"],
		"is_default": 1,
		"is_active": 1,
	}
	duplicate = frappe.db.exists("EduEdge Result Profile", filters)
	if duplicate:
		frappe.throw(
			_("Result Profile {0} is already the active default for this scope.").format(duplicate),
			frappe.DuplicateEntryError,
		)
