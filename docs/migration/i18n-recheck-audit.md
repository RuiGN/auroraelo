# Sprint 14 i18n recheck audit

## Verdict and boundary

**Full multilingual UI acceptance is not supported.** The catalog checker passes while reachable form labels, validation messages, model display labels, notices and notifications still remain Portuguese. Enabling English/Spanish locally exposes these gaps; it does not resolve them or authorize production publication.

Baseline: branch `codex/duralux-migration`, HEAD `fe3e5e9`, plus concurrent parent-agent changes. This audit changed only this report. No settings, application code, catalogs or PRD were edited; no pytest suite, database, Docker build, deployment, `.env` or real-user data was accessed. Findings are targeted counterexamples, not a complete inventory or human/native-language review. Previously recorded test/browser results were inspected as evidence scope, not rerun or independently accepted.

## What the green checker actually proves

A fresh run of `.venv/bin/python scripts/check_ui_catalogs.py --scope docs/migration/translated-ui-scope.json --output <temporary-directory>/check.json --pot-output <temporary-directory>/ui.pot` exited **0**, reporting **1,250 required keys**, no missing entries, placeholder errors or stale Django MO files, and **`publication_acceptance: false`**. Outputs and compilation staging were disposable.

The JSON scope contains **100 HTML files and 26 Python files, no JavaScript files**. `scripts/check_ui_catalogs.py:33-56` copies only that allowlist and extracts already-marked messages. Lines `73-90` check only `django.po`/`django.mo`; the placeholder expression at line `37` is limited to named percent placeholders. An unmarked string, an omitted Python file, or a JavaScript consumer cannot make this gate fail. The key count includes plural forms, not screens, visible strings or reviewed translations. `docs/migration/translated-ui-scope.json:2` calling this the “Full translated UI scope” overstates the evidence.

## Concrete gaps

| Area | Source and reachable output | Finding |
| --- | --- | --- |
| Marked Python omitted from extraction | `scheduling/forms.py:18-24,47,57`; `scheduling/unit_views.py:104`; `finance/forms.py:17-24`; `goals/forms.py:15-24`; `journal/forms.py:19-33` | These files are outside the allowlist. Compiled EN/ES lookup confirmed missing keys such as `Data e horário`, `Salvar unidade`, `Vigência inicial`, `Qual é a sua meta?` and `Como você está se sentindo?`; lookup returns the Portuguese source. `templates/components/duralux_field.html:5-19` renders labels/help/errors unchanged, and `templates/scheduling/unit_form.html:13` renders the untranslated submit label. Gettext marking alone is insufficient. |
| Unmarked domain UI | `content/forms.py:186-207` → `templates/content/editorial_create.html:15-24`; `content/views.py:196,322,348`; `analytics/forms.py:12,16` | CMS field labels and success messages, plus report-period labels, remain literal Portuguese. A translated surrounding template does not translate Python metadata. |
| Untranslated safety notice | `analytics/views.py:32-35,93-96` → `templates/analytics/patient_dashboard.html:4,13` | The non-diagnostic notice and Python page-title context are unmarked. The heading has its own translation, but the notice and document title do not inherit it. Separately, the marked emergency-channel notice at `scheduling/views.py:68` is absent from both compiled EN/ES catalogs. |
| User-facing service errors | `scheduling/unit_services.py:47-50` → `scheduling/unit_views.py:93-94` → `templates/scheduling/unit_form.html:11` | Duplicate-unit validation raises `Já existe uma unidade com este nome.` without gettext, then becomes a visible form error. This is a traced UI error, not an assumption that every internal exception needs translation. |
| Stable codes versus display labels | `scheduling/reminder_models.py:13-21` → `scheduling/forms.py:56-59` and `templates/scheduling/reminder_preferences.html:13`; `goals/models.py:64-83` → `templates/goals/detail.html:21-32` | Choice labels such as `Consulta`, `Exercício`, `Média` and `Curto prazo` are plain strings. `get_*_display` and `blocktranslate` around a variable do not translate those labels. Translate presentation labels, never persisted enum codes. |
| Date/decimal presentation | `templates/finance/charge_list.html:50`, `templates/journal/detail.html:11`, `templates/scheduling/appointment_list.html:33`; `finance/forms.py:16-17` | Display dates are pinned to `d/m/Y`, sometimes including literal Portuguese `às`. The actual finance amount field has `localize=False`. In contrast, `tests/test_i18n_presentation_and_preservation.py:38-40,80-110` verifies a test-only localized form, not this production form or these date fragments. |
| Recipient notifications | `content/services.py:1241-1258`; `content/receivers.py:60-68` → `templates/content/notifications.html:17` | Fixed notification bodies are persisted in Portuguese for every recipient, without recipient-language rendering/context. Password-recovery and scheduling-delivery coverage does not complete this path. These fixed bodies are product copy, not authored clinical content to preserve verbatim. |

### Executed, database-free counterexamples

With minimal Django settings and explicit `translation.override` for each language, using the actual compiled catalogs, the actual `ReminderType` class AST and the actual finance date-template line:

| Probe | pt-br | en | es |
| --- | --- | --- | --- |
| `gettext("Data e horário")` | `Data e horário` | `Data e horário` | `Data e horário` |
| `ReminderType.APPOINTMENT.label` | `Consulta` | `Consulta` | `Consulta` |
| Finance due-date fragment, synthetic date 2026-10-31 | `<td>31/10/2026</td>` | `<td>31/10/2026</td>` | `<td>31/10/2026</td>` |

A separate isolated instantiation of the actual `ServicePriceForm` class AST rejected synthetic amount `123,45` in all three locales, with `amount.localize=False`; Django's framework error itself was correctly localized. This proves the form-contract gap, not a browser or database round-trip failure.

## JavaScript and catalog-quality qualifications

- The `javascript-catalog` route exists (`config/urls.py:58-62`). Direct `msgfmt --check` into temporary files succeeded for all three `djangojs.po` files; each matched its checked-in MO and contained **5 non-header compiled keys including plural forms**. This is useful plumbing evidence, not consumer coverage.
- `tests/test_javascript_catalog_i18n.py:26-38,41-55,58-81` checks response strings/plurals and parallel requests under an overridden allowlist. No `javascript-catalog`/`jsi18n` reference was found in application templates, nor gettext/ngettext calls in first-party `static/duralux/js` scripts. Thus these tests do not demonstrate post-load UI consumption of that endpoint. Server-translated data attributes are a valid alternative and must not be called missing translations merely because JS lacks gettext.
- `static/duralux/js/dashboard-charts.js:16-18` still has Portuguese fallback copy. Its normal template supplies translated attributes (`templates/therapist_dashboard/home.html:106-107`), so this is a **conditional fallback gap**, not proof that the normal chart is Portuguese. Both chart scripts use document-language `Intl` formatting and hide toolbars (`static/duralux/js/dashboard-charts.js:20-36`, `static/duralux/js/visual-reference-charts.js:6-12,35-40`); no explicit ApexCharts locale registration was found in these initializers. Visible plugin/dynamic states still need integrated acceptance; hidden toolbar labels are not asserted as a reproduced defect.
- Compiled singular source-equals-target entries were counted: **37 EN, 123 ES**. These are review candidates, **not missing-translation totals**. Examples are legitimate identities: `locale/en/LC_MESSAGES/django.po:399-400` (`English (US)`) and `locale/es/LC_MESSAGES/django.po:589-590` (`Registros clínicos`). No erroneous translation is established merely by equality. Conversely, nonempty `msgstr` cannot establish terminology quality. `docs/migration/i18n-glossary.md:80-84` explicitly limits approval to an engineering proposal and still requires native-language review.

## Availability, documentation and acceptance

At audit start, base allowed only pt-br (`config/settings/base.py:196-200`), imported by development and production. The selector consumes that allowlist (`accounts/language_preferences.py:11-13`, `accounts/context_processors.py:30-33`), explaining absent EN/ES despite catalog files. During this audit the parent added the separate local-development allowlist at `config/settings/development.py:62-67`; its runtime verification belongs to the parent. Production still imports base `LANGUAGES` at `config/settings/production.py:19`. **Local draft availability and editorial/commercial production acceptance are different gates.** Do not withhold a requested local preview solely because commercial approval is pending; do not relabel preview availability as completed translation.

Claims requiring correction include `DURALUX.prd:335,345-358,473`, `docs/migration/execution-status.md:14,20-21`, `docs/migration/evidence/sprint-14.md:86-92`, and `docs/migration/final-acceptance.md:7,21-24`. Some still cite 25 Python files/1,244 keys, while the current allowlist/check reports 26/1,250. More importantly, neither figure proves full UI coverage. `docs/migration/final-acceptance.md:36` separately acknowledges pending commercial/editorial approval. The inspected browser matrix iterates only authentication/header surfaces on login/workspace (`scripts/verify-duralux-i18n.cjs:16-25`), not the full four-role/domain matrix required by S14.11.

## Required status reconciliation

- **Reopen S14.05 and S14.07:** complete Python/source reachability, label/error marking and extraction, catalog coverage and terminology review. Retain valid bounded deliveries; do not mark them all undone.
- **Reopen S14.06 integrated acceptance:** endpoint tests and translated data attributes are partial evidence; exercise actual dynamic consumers, fallbacks and visible plugin states per language.
- **Reopen S14.08 and S14.09:** actual date/amount form contracts and content-recipient notification paths contradict full acceptance.
- **Reopen S14.10:** CI calls the bounded checker (`.github/workflows/quality.yml:50-55`), so omitted/unmarked UI and djangojs are not covered by that gate. `Dockerfile:11-22` installs gettext and copies sources but contains no extraction/compilation/check step. In-image translation behavior was not verified by this audit; retain it as an explicit acceptance requirement rather than infer failure or success from checkout files.
- **Reopen S14.11, S14.12 and C11:** require real role/domain/locale coverage and language-specific sign-off against identified artifacts. Source counterexamples invalidate the claim of fully reviewed UI; no human, clinical, legal or commercial approval is asserted here.
- **S14.03 local availability:** track the parent's runtime-settings correction and actual-setting tests separately, then close only that engineering defect. No new defect was established in S14.01 inventory, S14.02 persistence or S14.04 selector mechanics; revalidate relevant behavior without treating those foundations as proof of C11.

Reclosure must expand the source inventory and exercise actual consumers, not merely increase a catalog key count. Preserve authored content, accepted documents, stable identifiers, permissions, canonical amounts and time-zone/UTC semantics throughout.
