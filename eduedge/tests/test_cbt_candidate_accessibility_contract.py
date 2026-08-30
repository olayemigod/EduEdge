from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


def test_candidate_page_loads_accessibility_assets_after_primary_runtime_assets():
    page = (APP / "www" / "eduedge-cbt-attempt.html").read_text(encoding="utf-8")

    base_css = "/assets/eduedge/css/eduedge_cbt_candidate.css?v=1"
    accessibility_css = "/assets/eduedge/css/eduedge_cbt_candidate_accessibility.css?v=1"
    candidate_js = "/assets/eduedge/js/eduedge_cbt_candidate.js?v=1"
    serialization_js = "/assets/eduedge/js/eduedge_cbt_candidate_serialization.js?v=1"
    accessibility_js = "/assets/eduedge/js/eduedge_cbt_candidate_accessibility.js?v=1"

    for asset in (base_css, accessibility_css, candidate_js, serialization_js, accessibility_js):
        assert asset in page

    assert page.index(base_css) < page.index(accessibility_css)
    assert page.index(candidate_js) < page.index(accessibility_js)
    assert page.index(serialization_js) < page.index(accessibility_js)


def test_candidate_accessibility_semantics_cover_runtime_question_and_status_surfaces():
    source = (APP / "public" / "js" / "eduedge_cbt_candidate_accessibility.js").read_text(encoding="utf-8")

    for expected in (
        'const ROOT_ID = "eduedge-cbt-candidate-root"',
        'questionText.setAttribute("role", "heading")',
        'answerArea.setAttribute("role", "group")',
        'answerArea.setAttribute("aria-labelledby", QUESTION_TEXT_ID)',
        'button.setAttribute("aria-current", "step")',
        'connection.setAttribute("role", "status")',
        'connection.setAttribute("aria-live", "polite")',
        "new MutationObserver",
    ):
        assert expected in source


def test_candidate_accessibility_styles_respect_user_display_preferences():
    source = (APP / "public" / "css" / "eduedge_cbt_candidate_accessibility.css").read_text(encoding="utf-8")

    assert "@media (prefers-reduced-motion: reduce)" in source
    assert "animation: none !important" in source
    assert "transition: none !important" in source
    assert "@media (forced-colors: active)" in source
    assert "forced-color-adjust: auto" in source
