# S14.01 — UI translation inventory

Inventory date: 2026-09-08. Scope: repository state inspected for S14.01; no
runtime, template, Python, JavaScript or catalog was changed. The machine-readable
snapshot is `docs/migration/evidence/i18n-inventory.json` and the reviewed terms are
in `docs/migration/i18n-glossary.md`.

## Subsequent translation checkpoints

The S14.01 figures below are the historical inventory before shared translations.
The newer `shared-ui-translation-report.md` records 27 templates/7 Python files
with 341 required compiled keys and 336 new message drafts. The subsequent clinic/
onboarding, people and consent slices extend the cumulative scope to **42 templates
and 25 Python files**, with **639 required compiled keys**. The current scope is
`translated-ui-scope.json`; fresh extraction and catalog validation are recorded in
`evidence/continuation-catalog-check.json` and `evidence/continuation-ui.pot`.
All three scoped catalogs pass; the other 58 templates, domain messages, recipient
jobs and plugin locales still require work. Full multilingual acceptance and human
terminology review remain pending; only pt-br is published. See
`continuation-report.md` for the reconciled checkpoint.

### Current execution checkpoint (updated during continuation)

The declared scope now reconciles **101/101 active HTML templates** and **48 Python
files containing gettext markers**, with no gettext-bearing Python file outside the
scope. The current fresh extraction validates **1,418 compiled `django` keys** for
`pt_BR`, `en` and `es`; the separate `djangojs` gate validates all three launch
catalogs and their plural forms. This is engineering reachability evidence, not
human terminology approval or full visual/domain acceptance. The current scope is
`translated-ui-scope.json`; the CI probes are recorded in
`evidence/continuation-catalog-ci-probe.json`.

## Baseline status and counting method

This is a preparation inventory, **not proof that extraction or translation is
complete**. It deliberately reports candidates to review rather than claiming that
every literal is user-visible. A later `makemessages` run, manual review, compiled
catalog check and browser acceptance remain required by S14.05–S14.12.

| Surface | Baseline evidence | Required action |
| --- | ---: | --- |
| Active first-party templates | 100 files (the original 99 plus the new selector); 32 gettext-tag occurrences in 5 files; 869 conservative **unmarked** literal occurrences | Review every file below; mark UI text and translatable attributes, use `blocktranslate` for interpolated prose and pluralization, preserve escaping and variables. The selector's 4 strings do not establish coverage of the original 99. |
| Duralux source/vendor HTML | 77 files under `design_system_duralux/` | Excluded from runtime translation: reference/source material only. Translate only text copied into an active template. |
| Python gettext | 3 calls: `core/forms.py` (1), `consents/forms.py` (2) | Retain placeholders; add lazy/contextual/plural translations only to strings that can reach a person. |
| Python review candidates | 428 literal `ValidationError`/permission/configuration exception arguments; 166 form label/help/error mappings; 8 Django message calls | Triage reachability. Translate UI/form/notification text; keep logs, exception diagnostics, audit actions and protocol codes as developer/stable strings. Counts overlap neither templates nor docstrings. |
| Python docstrings | 1,685 AST docstrings | Developer documentation, excluded unless a docstring is explicitly rendered (none found). |
| First-party JavaScript | 6 files used; 10 visible literal occurrences in 3 files; no `djangojs` catalog | Move visible literals to a CSP-compatible local JS catalog/data contract; configure locale-specific formatting. `language-selector.js` receives confirmation text from translated HTML and adds no hard-coded UI string. |
| Third-party runtime | Django Admin/forms/auth/messages templates; Bootstrap 5.3.3; ApexCharts 3.52.0 | Framework catalogs apply to Django surfaces. Bootstrap has no message catalog. Configure ApexCharts locale locally before enabling translated toolbar/UI. |
| Fixed outbound text | 2 account e-mails, 2 neutral scheduling messages, 4 content-notification bodies, one `[TESTE]` prefix | Activate the recipient language around rendering and restore it; never include or translate clinical/user-authored content. |
| Generated/exported documents | certificate templates, audit/finance/analytics/integration CSV and fiscal-document records | Translate fixed headings only; retain source data, identifiers and accepted document versions byte-for-byte. No PDF renderer was found. |
| Catalogs | `pt_BR` remains incomplete; `en`/`es` contain only the 4 selector bootstrap strings; no `djangojs` | Catalog set is incomplete and must not drive public language enablement. |

The template heuristic parses text nodes plus `alt`, `title`, `placeholder` and
`aria-label`, excludes `script`/`style`, pure variables, URL-like tokens,
punctuation-only content and complete `blocktranslate` regions, and counts
occurrences rather than unique messages. It can miss fragmented text, data
attributes, dynamic values and literals emitted by
includes, and can include user-authored or developer-only samples. Therefore 869 is
a conservative unmarked-work estimate, **not a completeness assertion**.

## Active template worklist

Except where a gettext count is shown, gettext is zero for every file below. The
number in parentheses is the heuristic unmarked-candidate count. A zero means
“manual review required”; it often means
the visible text arrives through context, form metadata or an included component.

| Area | Exact files and candidate occurrences |
| --- | --- |
| accounts | `accounts/auth_base.html` (2); `accounts/auth_form.html` (0); `accounts/auth_message.html` (0); `accounts/mfa_enroll.html` (10); `accounts/mfa_recovery_codes.html` (3); `accounts/sessions.html` (8) |
| analytics | `analytics/clinic_panel.html` (11); `analytics/patient_dashboard.html` (9); `analytics/report_list.html` (5); `analytics/therapist_dashboard.html` (11) |
| clinics | `clinics/confirm_switch.html` (8); `clinics/setup.html` (27); `clinics/whitelabel_domains.html` (6) |
| components | `components/content_state.html` (0); `components/duralux_field.html` (0); `components/form.html` (2); `components/language_selector.html` (0 unmarked; 4 gettext); `components/pagination.html` (1); `components/responsive_table.html` (8); `components/summary_card.html` (0) |
| consents | `consents/center.html` (0; 7 gettext); `consents/decision_error.html` (0; 5 gettext); `consents/partials/document_decision.html` (0; 13 gettext); `consents/revocation_error.html` (0; 3 gettext); `consents/revocation_work_error.html` (3); `consents/revocation_work_queue.html` (9) |
| content | `content/detail.html` (3); `content/editorial_compare.html` (5); `content/editorial_create.html` (43); `content/editorial_detail.html` (44); `content/editorial_index.html` (4); `content/editorial_preview.html` (3); `content/lesson_player.html` (11); `content/library.html` (8); `content/notifications.html` (3); `content/recommendations.html` (6); `content/reports.html` (6) |
| content/learning | `content/learning/certificate.html` (8); `content/learning/certificate_verify.html` (5); `content/learning/cohort_detail.html` (4); `content/learning/course_detail.html` (13); `content/learning/index.html` (14); `content/learning/lesson_page.html` (2); `content/learning/module_detail.html` (6); `content/learning/quiz_detail.html` (12); `content/learning/quiz_feedback.html` (4); `content/learning/quiz_participate.html` (2) |
| errors | `errors/400.html` (2); `errors/403.html` (2); `errors/404.html` (2); `errors/500.html` (2) |
| finance | `finance/charge_list.html` (14); `finance/service_price_form.html` (3) |
| goals | `goals/detail.html` (10); `goals/exercise_assign.html` (8); `goals/exercise_catalog.html` (7); `goals/exercise_execute.html` (9); `goals/exercise_execution_detail.html` (11); `goals/exercise_form.html` (12); `goals/form.html` (8); `goals/list.html` (11); `goals/low_energy.html` (20); `goals/patient_exercises.html` (6) |
| journal | `journal/checkin_list.html` (16); `journal/checkin_today.html` (12); `journal/checkin_unavailable.html` (3); `journal/detail.html` (20); `journal/form.html` (8); `journal/list.html` (42); `journal/partials/calendar.html` (12) |
| layouts | `layouts/base.html` (2); `layouts/detached.html` (5); `layouts/partials/brand.html` (0); `layouts/partials/header.html` (19); `layouts/partials/messages.html` (1); `layouts/partials/navigation.html` (18); `layouts/vertical.html` (5) |
| onboarding | `onboarding/clinic_checklist.html` (6); `onboarding/patient_onboarding.html` (14) |
| people | `people/patient_detail.html` (8); `people/patient_form.html` (6); `people/patient_list.html` (11); `people/professional_list.html` (11) |
| scheduling | `scheduling/appointment_calendar.html` (13); `scheduling/appointment_list.html` (14); `scheduling/appointment_request.html` (3); `scheduling/appointment_reschedule.html` (4); `scheduling/conversation_create.html` (3); `scheduling/conversation_detail.html` (8); `scheduling/conversation_list.html` (4); `scheduling/reminder_preferences.html` (6); `scheduling/room_form.html` (3); `scheduling/unit_form.html` (3); `scheduling/unit_list.html` (13); `scheduling/waitlist_form.html` (3); `scheduling/waitlist_list.html` (9) |
| remaining | `therapist_dashboard/home.html` (29); `visual_reference/reference.html` (74); `workspace/home.html` (5); `workspace/shortcut.html` (0) |

Priority order for marking: shared layouts/components and account/error screens;
consent and scheduling; people/clinical navigation; content/learning and generated
certificates; analytics/finance; then the visual reference. Re-run extraction after
each group so duplicate/context/plural decisions remain reviewable.

## Python, validation, messages and context processors

Files with form metadata to review are `accounts/forms.py`, `analytics/forms.py`,
`clinics/forms.py`, `consents/forms.py`, `content/forms.py`, `core/forms.py`,
`finance/forms.py`, `goals/forms.py`, `journal/forms.py`, `onboarding/forms.py`,
`onboarding/selectors.py`, `people/forms.py`, and `scheduling/forms.py`.

Files with literal validation/permission candidates are `ai_assistant/services.py`,
`analytics/services.py`, `audit/models.py`, `audit/services.py`, `clinics/services.py`,
`consents/models.py`, `consents/selectors.py`, `consents/services.py`,
`content/forms.py`, `content/learning_authoring.py`, `core/uploads.py`,
`finance/billing_services.py`, `finance/ledger_models.py`, `finance/ledger_services.py`,
`finance/payout_services.py`, `finance/reporting_services.py`, `finance/services.py`,
`finance/subscription_services.py`, `finance/webhook_services.py`,
`goals/exercise_services.py`, `goals/exercise_views.py`, `goals/forms.py`,
`goals/low_energy_services.py`, `goals/services.py`, `integrations/calendars.py`,
`integrations/pwa.py`, `integrations/services.py`, `integrations/video.py`,
`integrations/whatsapp.py`, `journal/forms.py`, `journal/services.py`,
`onboarding/services.py`, `people/services.py`, `privacy/services.py`,
`routines/care_plan_services.py`, `routines/medication_services.py`,
`routines/services.py`, `routines/sleep_services.py`,
`scheduling/availability_services.py`, `scheduling/messaging_services.py`,
`scheduling/reminder_services.py`, `scheduling/services.py`,
`scheduling/unit_services.py`, `scheduling/waitlist_services.py`,
`support_network/services.py`, `wellness/crisis_services.py`,
`wellness/relapse_services.py`, `wellness/services.py`, and
`wellness/sobriety_services.py`.

The 8 Django message literals are in `core/middleware.py` (1) and
`content/views.py` (7). Context processors are framework `request`, `auth`, and
`messages`, plus `accounts.context_processors.language_preferences`,
`clinics.context_processors.clinic_navigation` and
`consents.context_processors.revocation_work_notifications`. Context values such as
page titles, status labels and pending-work descriptions must be translated where
they are constructed; user/clinic names and authored content must pass through.

Do not translate operational diagnostics, log records, audit action/resource/outcome
codes, API error identifiers, exception class names, cache keys, URL names, database
values or enum values. A `ValidationError` literal is translatable only when the
error reaches a form/API/UI consumer; configuration and invariant failures remain
developer-facing even though the heuristic counted them.

## JavaScript and plugin scope

| File | UI/runtime scope | Action |
| --- | --- | --- |
| `static/duralux/js/dashboard-charts.js` | 2 visible literals (`Cadastros`, empty-period message) | Catalog/data attributes; locale-aware chart options. |
| `static/duralux/js/product-shell.js` | 4 visible status/copy literals | `djangojs` or server-provided data; preserve focus/status behavior. |
| `static/duralux/js/visual-reference-charts.js` | 4 visible fallback/axis/ARIA occurrences and hard-coded `Intl.DateTimeFormat("pt-BR")` | Supply effective locale and translated accessible labels. |
| `static/duralux/js/form-behaviors.js` | No fixed visible literal; reads confirmation/dirty text from HTML data attributes | Translate source attributes in templates and keep unsaved-change semantics. |
| `static/duralux/js/lesson-player.js` | No fixed visible literal | Player labels remain template-owned. |
| `static/duralux/js/language-selector.js` | No fixed visible literal; confirmation comes from translated `data-language-confirm` | Keep the server-owned translated data contract and focus restoration. |
| `static/duralux/vendors/apexcharts/apexcharts.min.js` | Bundled third-party chart UI | Do not edit vendor minified source; register local `pt-br`, `en`, `es` locale objects and set `defaultLocale`. |
| `static/duralux/js/bootstrap.bundle.min.js` | Bundled interaction code | No application catalog; visible labels belong to HTML. |

## E-mail, notifications and generated outputs

Fixed text requiring recipient-context translation is in:

- `accounts/views.py`: clinic invitation subject/body and success UI;
- `accounts/services.py`: password-recovery subject/body;
- `scheduling/delivery_templates.py`: appointment reminder and new-message notice;
- `content/services.py`: three recommendation state notifications;
- `content/receivers.py`: credential-revocation recommendation notification;
- `clinics/whitelabel_services.py`: `[TESTE]` prefix only; the communication-template
  subject/body is authored tenant content and must not be machine-translated.

Generated-output scope includes `content/learning/certificate.html` and
`content/learning/certificate_verify.html`, CSV headings in `audit/services.py`,
`finance/reporting_services.py`, `analytics/advanced_reporting.py` and
`integrations/services.py`, plus fixed fiscal-document presentation around records
from `finance/payout_services.py`. No PDF generation library or active PDF template
was found. File names, IDs, hashes, timestamps, monetary values and uploaded document
contents remain data; only fixed headings/help text may be localized.

## Content boundary

Translate interface chrome, fixed instructions, accessibility names, form labels,
framework validation messages and fixed notification/e-mail/document headings.
Never translate patient journal entries, check-in answers, therapist notes, chat
messages, content authored by a clinic/editor, uploaded files, names, addresses or
free-text reasons. Display those values exactly as stored.

A consent document is versioned legal/user-authored content. Its title/body,
purpose text, alternatives and accepted snapshot are not silently translated.
Translate only surrounding UI. A separately reviewed localized consent version must
be a new explicitly versioned artifact with its own provenance and acceptance; a
language switch must never mutate or reinterpret an existing acceptance.

## Catalog findings and release gate

`locale/pt_BR/LC_MESSAGES/django.po` has 32 non-header entries: 24 translated,
8 empty and 0 fuzzy. The empty entries are two English revocation-form strings and
six Portuguese revocation UI strings. The compiled `.mo` contains 24 non-header
messages, so it does not cover the empty entries. The PO header still identifies
`Projetomnunes`, which is stale provenance for Mindcare.

Bootstrap `locale/en` and `locale/es` Django catalogs now exist and each contains
the selector's 4 translated strings with 0 empty and 0 fuzzy entries. No locale has
a `djangojs` catalog. Settings still allow only `pt-br`; the bootstrap catalogs are
explicitly partial and no public three-language completion evidence exists. English
and Spanish must remain absent from the public selector/allowlist
until both `django` and `djangojs` catalogs have no required empty/fuzzy entries,
compile successfully, pass placeholder/plural checks and complete human terminology
and browser review. This inventory therefore accepts only the S14.01 discovery and
glossary stage; it does not accept S14.05–S14.12 or public multilingual enablement.
