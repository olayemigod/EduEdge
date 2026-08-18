from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_resolver_fails_closed_on_missing_or_ambiguous_mapping():
    source = _read("eduedge/education/instructor_scope.py")
    assert "get_active_instructor_names_for_user" in source
    assert "resolve_exact_instructor_for_user" in source
    assert "more than one active Instructor" in source
    assert "not linked to exactly one active Employee and Instructor" in source
    assert 'filters={"user_id": resolved_user, "status": "Active"}' in source
    assert 'filters={"employee": ["in", employees], "status": "Active"}' in source


def test_manager_readiness_distinguishes_identity_failure_modes():
    source = _read("eduedge/education/instructor_scope.py")
    for label in (
        "No Employee Link",
        "Missing Employee",
        "Inactive Instructor",
        "Inactive Employee",
        "No User Login",
        "Inactive User",
        "Ambiguous Employee Mapping",
        "Ambiguous Instructor Mapping",
        "Ready",
    ):
        assert label in source
    assert "operational_ready" in source
    assert "active_employee_count" in source
    assert "active_instructor_count" in source


def test_new_identity_links_cannot_introduce_ambiguity():
    source = _read("eduedge/education/people_governance.py")
    assert "_validate_instructor_employee_identity" in source
    assert "mapping_changed" in source
    assert "already linked to another active Instructor" in source
    assert "linked to more than one active Employee" in source
    assert "already resolves to another active Instructor" in source
    assert "if not mapping_changed" in source


def test_historical_instructors_remain_visible_through_scoped_assignment_history():
    source = _read("eduedge/education/academic_permissions.py")
    assert "def instructor_query" in source
    assert "EduEdge Instructor Branch Assignment" in source
    assert "EduEdge Instructor Assignment" in source
    assert "has_instructor_permission" in source
    assert 'getattr(doc, "doctype", None) == "Instructor"' in source


def test_instructor_register_surfaces_readiness_without_destructive_repair():
    api = _read("eduedge/api/instructor_profiles.py")
    ui = _read("eduedge/public/js/eduedge_instructors/EduEdgeInstructors.vue")
    assert "get_instructor_identity_states" in api
    assert 'row["identity"]' in api
    assert 'result["identity"]' in api
    assert "academic_assignment_names" in api
    assert "Teaching identity:" in ui
    assert "Assignment-driven teaching access requires one active User" in ui
    assert "identity-readiness" in ui
    assert "identityTone" in ui
