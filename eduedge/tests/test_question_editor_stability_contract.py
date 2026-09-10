from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


def test_question_builder_installs_caret_stability_runtime():
    page = (
        APP
        / "eduedge/page/eduedge_question_builder/eduedge_question_builder.js"
    ).read_text()
    stability = (APP / "public/js/eduedge_question_editor_stability.bundle.js").read_text()

    for expected in (
        '"eduedge_question_editor_stability.bundle.js"',
        "window.installEduEdgeQuestionEditorStability",
        "wrapper.editor_stability_runtime?.destroy?.()",
        "wrapper.editor_stability_runtime = window.installEduEdgeQuestionEditorStability(root[0])",
    ):
        assert expected in page

    for expected in (
        "function captureSelectionOffsets",
        "function restoreSelectionOffsets",
        'root.querySelectorAll(".question-editor[contenteditable]")',
        'editor.addEventListener("input", onInput)',
        "queueMicrotask",
        "requestAnimationFrame",
        "document.activeElement !== root",
    ):
        assert expected in stability


def test_question_builder_exposes_one_explicit_safe_draft_save_action():
    stability = (APP / "public/js/eduedge_question_editor_stability.bundle.js").read_text()
    builder = (APP / "public/js/eduedge_question_builder/EduEdgeQuestionBuilder.vue").read_text()

    assert 'String(button.textContent || "").trim().toLowerCase() === "save draft"' in stability
    assert 'setAttribute("data-edgesuite-save", "draft")' in stability
    assert 'setAttribute("aria-label", "Save Draft")' in stability
    assert "@click=\"saveAs('Draft')\"" in builder

    # Ctrl+S must map only to the existing governed Draft action; it must not
    # expose review/approval lifecycle actions as generic save controls.
    assert 'data-edgesuite-save", "approve"' not in stability
    assert 'data-edgesuite-save", "review"' not in stability
