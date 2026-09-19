# Sprint 11 — Cobertura visual, acessibilidade e resíduos

Data: 09/09/2026 | Branch: `codex/duralux-migration` | Escopo: Validação WCAG 2.2 AA, responsividade e orçamentos

## 1. Status das tarefas da Sprint 11

- **S11.01**: Reconciliação dos templates concluída (100 templates ativos cobertos e registrados em `templates-matrix.md`).
- **S11.02**: Conferência de breakpoints em 375px, 768px e 1440px. Tabelas com wrappers responsivos (`.table-responsive`, `.product-table-scroll`), sem quebra horizontal. Validado via `tests/test_duralux_wcag_and_responsive.py::test_s11_02_*`.
- **S11.03**: Acessibilidade WCAG 2.2 AA validada: taxas de contraste >= 4.5:1 nos temas claro e escuro, presença de marcos e links de salto (`#main-content`, `<header>`, `<main>`), suporte a `prefers-reduced-motion` no CSS. Validado via `tests/test_duralux_wcag_and_responsive.py::test_s11_03_*`.
- **S11.04**: Verificação estática e em tempo de execução: zero links quebrados (`#`, `javascript:void(0)`), referências estáticas (`{% static %}`) 100% resolvíveis sem 404. Validado via `tests/test_duralux_wcag_and_responsive.py::test_s11_04_*`.
- **S11.05**: Seletores de teste alinhados à estrutura Duralux sem relaxamento de assertivas de segurança.
- **S11.06**: Remoção comprovada de tokens e recursos visuais obsoletos (`tests/test_duralux_legacy_removal.py`).
- **S11.07**: Revisão de branding Mindcare, datas, moedas e isolamento multi-tenant preservados.
- **S11.08**: Plugins especializados (`apexcharts`, `lesson-player`, etc.) carregados exclusivamente nas páginas demandantes; footprint de assets de runtime estritamente dentro do orçamento (< 2MB). Validado via `tests/test_duralux_wcag_and_responsive.py::test_s11_08_*`.

## 2. Evidência de Execução

Execução dos testes específicos de regressão da Sprint 11 em PostgreSQL local (`compose.test.yml`):

```text
tests/test_duralux_wcag_and_responsive.py::test_s11_02_every_table_has_responsive_wrapper_to_prevent_horizontal_overflow PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_02_css_supports_mobile_tablet_desktop_breakpoints PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_03_wcag_contrast_ratios_meet_level_aa PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_03_landmarks_and_skip_links_present_in_base_layouts PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_03_reduced_motion_respected_in_css PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_04_no_broken_demo_links_or_javascript_void PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_04_all_static_references_in_templates_resolve PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_08_specialized_plugins_are_conditionally_loaded PASSED
tests/test_duralux_wcag_and_responsive.py::test_s11_08_runtime_asset_size_is_within_budget PASSED

9 passed in 1.48s
```
