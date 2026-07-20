from __future__ import annotations

PRODUCT_CODE = "EduEdge"
PRODUCT_FAMILY = "education_management"
DISTRIBUTION = "eduedge"
DISPLAY_LABEL = "EduEdge"

FEATURE_KEYS = frozenset(
	{
		"foundation",
		"school_branch",
		"student_management",
		"admission",
		"fees",
		"academics",
		"attendance",
		"assessment",
		"cbt",
		"offline_resilient_cbt",
		"student_pickup",
		"school_bus",
		"school_intelligence",
		"lms",
		"edgefinder",
		"communications",
	}
)


def normalize_feature_key(feature_key: str | None) -> str | None:
	if not feature_key:
		return None
	return str(feature_key).strip().lower().replace(" ", "_").replace("-", "_")


def resolve_product_identity(
	*,
	tenant_key: str | None = None,
	feature_key: str | None = None,
) -> dict:
	normalized_feature = normalize_feature_key(feature_key)
	return {
		"product_code": PRODUCT_CODE,
		"product_app": PRODUCT_CODE,
		"active_product_app": PRODUCT_CODE,
		"product_family": PRODUCT_FAMILY,
		"distribution": DISTRIBUTION,
		"display_label": DISPLAY_LABEL,
		"tenant_key": tenant_key,
		"feature_key": normalized_feature,
		"known_feature_key": normalized_feature in FEATURE_KEYS if normalized_feature else False,
	}
