# S14.05/S14.06 — visual reference UI translation increment

Date: 2026-09-08

## Scope

This bounded increment marks the fixed product-owned copy in
`templates/visual_reference/reference.html` for Django translation and makes
`static/duralux/js/visual-reference-charts.js` consume labels translated by the
server. It covers the visual reference only; it does not claim completion of
S14.05, S14.06, Sprint 14, or either launch-language catalog.

The existing DOM structure, IDs, fragment links, Bootstrap behavior, theme
updates, chart values, and synthetic sample values remain unchanged. `Bootstrap`
and `Duralux` remain product or technology names. No user-authored, clinical,
legal, or operational data is present in this reference surface.

## Translation contract

- All fixed visible prose, headings, labels, actions, status text, captions,
  accessibility text, and translatable chart configuration use `translate` or
  `blocktranslate`.
- Complete sentences containing `<strong>` retain their markup inside a single
  `blocktranslate`, allowing English and Spanish to use coherent word order.
- The translated form submit label is assigned server-side before it is passed
  to the shared form component.
- The chart receives its series, axis, value, and accessible image labels from
  escaped server-rendered `data-*` attributes. Its three translated week labels
  are separate escaped attributes and are assembled as an array by JavaScript;
  no translated string is interpolated into JSON.
- Date presentation uses `document.documentElement.lang` with
  `Intl.DateTimeFormat` and retains `timeZone: "UTC"`. Language selection does
  not select a currency or time zone.
- JavaScript has no untranslated UI fallback because every chart consumer in
  this bounded page supplies the required translated labels.

## Draft catalog handoff

`docs/migration/evidence/reference-ui-translations.json` contains 94 unique
source messages and complete non-empty English and general Spanish drafts. Each
entry has exactly `msgid`, `en`, and `es`. This surface contains no pluralized
message, so no `msgid_plural` entries are required. Catalog owners must merge and
review these drafts centrally; this increment does not edit or compile PO/MO
files and does not publish `en` or `es` in `LANGUAGES`.

## Verification

Focused static verification completed:

- Django system check with `DJANGO_SETTINGS_MODULE=config.settings.test`:
  no issues.
- Django template loader compiled `visual_reference/reference.html` successfully.
- Django `templatize` extraction found 94 unique messages; the JSON draft contains
  the same 94 unique `msgid` values, with no missing or surplus entries.
- JSON structure validation confirmed every English and Spanish draft is non-empty.
- `node --check static/duralux/js/visual-reference-charts.js`: passed.
- A residual fixed-text scan found only the proper name `Bootstrap` outside
  translation tags; the matches containing `<strong>` are inside
  `blocktranslate`.

The shared pre-increment state is preserved at
`.migration-runtime/shared-i18n-before`. The inherited project baseline remains
1,310 passing tests with 86.02% coverage. No database tests or shared pytest run
were started for this bounded increment, and the 90% coverage gate remains open.
Native-language editorial review, central PO/MO merge and compilation, complete
cross-role extraction, and multilingual browser acceptance remain pending before
either launch language can be published.
