"""Source contracts for Duralux domain-template migration (Sprints 5-8)."""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings

SPRINT5_TEMPLATES = (
    "scheduling/appointment_calendar.html",
    "scheduling/appointment_list.html",
    "scheduling/appointment_reschedule.html",
    "scheduling/room_form.html",
    "scheduling/unit_form.html",
    "scheduling/unit_list.html",
    "scheduling/waitlist_form.html",
    "scheduling/waitlist_list.html",
    "finance/charge_list.html",
    "finance/service_price_form.html",
)

SPRINT6_TEMPLATES = (
    "consents/center.html",
    "consents/decision_error.html",
    "consents/partials/document_decision.html",
    "consents/revocation_error.html",
    "consents/revocation_work_error.html",
    "consents/revocation_work_queue.html",
    "goals/exercise_assign.html",
    "goals/exercise_catalog.html",
    "goals/exercise_execution_detail.html",
    "goals/exercise_form.html",
)

SPRINT7_TEMPLATES = (
    "content/detail.html",
    "content/editorial_compare.html",
    "content/editorial_create.html",
    "content/editorial_detail.html",
    "content/editorial_index.html",
    "content/editorial_preview.html",
    "content/learning/certificate.html",
    "content/learning/certificate_verify.html",
    "content/learning/cohort_detail.html",
    "content/learning/course_detail.html",
    "content/learning/index.html",
    "content/learning/lesson_page.html",
    "content/learning/module_detail.html",
    "content/learning/quiz_detail.html",
    "content/learning/quiz_feedback.html",
    "content/learning/quiz_participate.html",
    "content/lesson_player.html",
    "content/library.html",
    "content/reports.html",
)

PARTIALS = {
    "consents/partials/document_decision.html",
    "content/lesson_player.html",
}

LEGACY_CLASS_TOKENS = {
    "welcome-panel",
    "workspace-eyebrow",
    "workspace-intro",
    "shortcut-row",
    "primary-action",
    "link-action",
    "summary-card-grid",
    "summary-card",
    "summary-card-heading",
    "component-section",
    "responsive-table-wrapper",
    "responsive-table",
    "chart-container",
    "section-heading",
    "table-filter",
    "table-scroll",
    "table-actions",
    "pagination-status",
    "pagination-links",
    "content-card",
    "form-actions",
    "context-chip",
    "form-stack",
    "form-field",
    "field-error",
    "field-help",
    "mood-badge",
    "mood-neutral",
    "confirmation-actions",
    "breadcrumbs",
    "choice-group",
    "clinic-brand-preview",
    "detail-list",
    "destructive-action",
    "checklist",
    "checklist-mark",
    "document-summary",
    "page-title",
}


def _source(relative_path: str) -> str:
    return (Path(settings.BASE_DIR) / "templates" / relative_path).read_text(
        encoding="utf-8"
    )


def _class_tokens(source: str) -> set[str]:
    return {
        token
        for match in re.finditer(r'class=(["\'])(.*?)\1', source)
        for token in match.group(2).split()
    }


def _assert_migrated(relative_path: str) -> None:
    source = _source(relative_path)
    assert "style=" not in source, relative_path
    assert not re.search(r"<script(?![^>]*\bsrc=)", source), relative_path
    assert not (_class_tokens(source) & LEGACY_CLASS_TOKENS), relative_path
    assert "design_system_duralux/" not in source, relative_path
    if relative_path not in PARTIALS:
        assert "{% block title %}" in source or "<title>" in source, relative_path


def test_sprint5_templates_use_duralux_without_inline_or_legacy_visuals() -> None:
    for relative_path in SPRINT5_TEMPLATES:
        _assert_migrated(relative_path)


def test_sprint6_templates_use_duralux_without_inline_or_legacy_visuals() -> None:
    for relative_path in SPRINT6_TEMPLATES:
        _assert_migrated(relative_path)


def test_unconsumed_goal_placeholder_is_removed() -> None:
    template_root = Path(settings.BASE_DIR) / "templates"
    placeholder = template_root / "goals/placeholder.html"

    assert not placeholder.exists()
    for path in template_root.rglob("*.html"):
        assert "goals/placeholder.html" not in path.read_text(encoding="utf-8")


def test_sprint7_templates_use_duralux_without_inline_or_legacy_visuals() -> None:
    for relative_path in SPRINT7_TEMPLATES:
        _assert_migrated(relative_path)


def test_public_certificate_uses_duralux_brand_favicon_and_css() -> None:
    source = _source("content/learning/certificate_verify.html")
    assert "duralux/images/favicon.svg" in source
    assert 'include "layouts/partials/brand.html"' in source
    assert "duralux/css/bootstrap.min.css" in source
    assert "duralux/css/theme.min.css" in source
    assert "duralux/css/product-integration.css" in source
    assert "css/framework.css" not in source
    assert "css/tokens.css" not in source


def test_exercise_sharing_statuses_have_visible_icon_and_explanatory_text() -> None:
    execution_detail = _source("goals/exercise_execution_detail.html")

    assert "product-visibility-status" in execution_detail
    assert 'aria-hidden="true"' in execution_detail
    for description in (
        "Pode compartilhar com o profissional.",
        "Confirme antes de compartilhar com o profissional.",
        "Somente você pode ver este registro.",
    ):
        assert description in execution_detail


def test_sprint6_uses_bootstrap_card_structure_and_no_tailwind_tokens() -> None:
    unsupported_tokens = {"space-y-4", "rounded-lg", "prose"}

    for relative_path in SPRINT6_TEMPLATES:
        source = _source(relative_path)
        assert not (_class_tokens(source) & unsupported_tokens), relative_path

        class_sets = [
            set(match.group(2).split())
            for match in re.finditer(r'class=(["\'])(.*?)\1', source)
        ]
        card_count = sum("card" in classes for classes in class_sets)
        card_body_count = sum("card-body" in classes for classes in class_sets)
        assert card_body_count >= card_count, relative_path
