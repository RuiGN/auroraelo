# Duralux asset and HTML matrix

Sprint 0 inventory of the local `design_system_duralux/` package. Classification describes how each HTML can inform later work; it does not authorize copying demo data or dependencies. Every adoption status starts as `pending`.

- Local Duralux HTML files: **77**.
- Local Duralux asset files: **1059**.
- Asset areas: `css/` 4, `images/` 125, `js/` 37, `scss/` 158, `vendors/` 735.
- Extensions: `.css` 25, `.eot` 1, `.gif` 1, `.ico` 1, `.jpg` 7, `.js` 77, `.map` 65, `.mp4` 1, `.png` 160, `.scss` 158, `.svg` 549, `.ttf` 5, `.webp` 2, `.woff` 2, `.woff2` 5.

| Duralux HTML | Classification | Components / evidence | Observed plugins | Intended Django destination | Prior disposition | Status |
|---|---|---|---|---|---|---|
| `analytics.html` | standalone demo | KPIs, séries, mapa, filtros de período | ApexCharts, daterangepicker, jVectorMap, Select2, time-to, circle-progress | `analytics/*`, `therapist_dashboard/home.html` | adaptar | `pending` |
| `apps-calendar.html` | application demo | calendário mensal/semanal, toolbar, modal de evento | TUI Calendar, Moment, Chance, TUI date/time picker | `scheduling/appointment_calendar.html` | adaptar | `pending` |
| `apps-chat.html` | application demo | lista de conversas, thread, compositor, anexos | Emoji One Area, time-tracker | `scheduling/conversation_*` | adaptar | `pending` |
| `apps-email.html` | application demo | inbox, filtros, leitura, compositor rico | Select2, Tagify, Quill | `content/notifications.html`, `scheduling/conversation_*` | adaptar | `pending` |
| `apps-notes.html` | application demo | cartões de notas, etiquetas, estados vazios | nenhum | `journal/*`, `content/editorial_*` | adaptar | `pending` |
| `apps-storage.html` | application demo | navegador de arquivos, quota, lista/grid | Select2 | `content/library.html`, mídia editorial | adaptar | `pending` |
| `apps-tasks.html` | application demo | kanban/lista, detalhes, prioridade, datas | Select2, datepicker, Quill | `goals/*` | adaptar | `pending` |
| `auth-404-cover.html` | authentication/state | erro 404, ilustração, retorno | nenhum | sem destino direto | não usar | `pending` |
| `auth-404-creative.html` | authentication/state | erro 404, composição decorativa, retorno | nenhum | sem destino direto | não usar | `pending` |
| `auth-404-minimal.html` | authentication/state | erro 404 compacto, mensagem, retorno | nenhum | `errors/404.html` e padrão para `errors/*` | adaptar | `pending` |
| `auth-login-cover.html` | authentication/state | formulário, painel de imagem, lembrar senha | nenhum | sem destino direto | não usar | `pending` |
| `auth-login-creative.html` | authentication/state | formulário, fundo decorativo, marca | nenhum | sem destino direto | não usar | `pending` |
| `auth-login-minimal.html` | authentication/state | formulário, marca, senha, mensagens | nenhum | `accounts/auth_form.html` | adaptar | `pending` |
| `auth-maintenance-cover.html` | authentication/state | manutenção, imagem, retorno | nenhum | sem consumidor atual | não usar | `pending` |
| `auth-maintenance-creative.html` | authentication/state | manutenção, fundo decorativo, retorno | nenhum | sem consumidor atual | não usar | `pending` |
| `auth-maintenance-minimal.html` | authentication/state | manutenção compacta, retorno | nenhum | sem consumidor atual | não usar | `pending` |
| `auth-register-cover.html` | authentication/state | cadastro, painel de imagem, força de senha | lslstrength | sem destino direto | não usar | `pending` |
| `auth-register-creative.html` | authentication/state | cadastro, fundo decorativo, força de senha | lslstrength | sem destino direto | não usar | `pending` |
| `auth-register-minimal.html` | authentication/state | cadastro compacto, senha, termos | lslstrength | `accounts/auth_form.html` em `invitation_accept` | adaptar | `pending` |
| `auth-reset-cover.html` | authentication/state | solicitação de recuperação, imagem | nenhum | sem destino direto | não usar | `pending` |
| `auth-reset-creative.html` | authentication/state | solicitação de recuperação, decoração | nenhum | sem destino direto | não usar | `pending` |
| `auth-reset-minimal.html` | authentication/state | recuperação compacta, e-mail, retorno | nenhum | `accounts/auth_form.html` em `password_recovery` | adaptar | `pending` |
| `auth-resetting-cover.html` | authentication/state | redefinição de senha, imagem | nenhum | sem destino direto | não usar | `pending` |
| `auth-resetting-creative.html` | authentication/state | redefinição de senha, decoração | nenhum | sem destino direto | não usar | `pending` |
| `auth-resetting-minimal.html` | authentication/state | nova senha, confirmação, feedback | nenhum | `accounts/auth_form.html` em `password_reset` | adaptar | `pending` |
| `auth-verify-cover.html` | authentication/state | código de verificação, imagem | nenhum | sem destino direto | não usar | `pending` |
| `auth-verify-creative.html` | authentication/state | código de verificação, decoração | nenhum | sem destino direto | não usar | `pending` |
| `auth-verify-minimal.html` | authentication/state | código segmentado, instruções, reenvio | nenhum | `accounts/auth_form.html`, cadastro/desafio MFA | adaptar | `pending` |
| `customers-create.html` | CRM/management demo | formulário em seções, datas, selects | Select2, datepicker, lslstrength | `people/patient_form.html` | adaptar | `pending` |
| `customers-view.html` | CRM/management demo | cabeçalho de perfil, abas, timeline, dados | Select2 | `people/patient_detail.html` | adaptar | `pending` |
| `customers.html` | CRM/management demo | listagem, filtros, tabela, ações | DataTables, Select2 | `people/patient_list.html`, `people/professional_list.html` | adaptar | `pending` |
| `docs/documentations.html` | documentation | índice documental, navegação, chamadas | nenhum | documentação de implementação somente | não usar | `pending` |
| `docs/html/changelog.html` | documentation | changelog, navegação documental | nenhum | documentação de implementação somente | não usar | `pending` |
| `docs/html/configuration.html` | documentation | opções de configuração, exemplos de código | nenhum | documentação de implementação somente | não usar | `pending` |
| `docs/html/credit-resource.html` | documentation | créditos de imagens, ícones e plugins | nenhum | `runtime-asset-manifest.md` | não usar | `pending` |
| `docs/html/folder-structure.html` | documentation | árvore de diretórios, explicações | nenhum | documentação de implementação somente | não usar | `pending` |
| `docs/html/get-started.html` | documentation | introdução, requisitos, navegação | nenhum | documentação de implementação somente | não usar | `pending` |
| `docs/html/installation.html` | documentation | passos de instalação, exemplos | nenhum | documentação de implementação somente | não usar | `pending` |
| `docs/html/layouts.html` | documentation | variantes de layout, opções do tema | nenhum | `layouts/*` como orientação | não usar | `pending` |
| `help-knowledgebase.html` | standalone demo | hero de busca, categorias, FAQ, artigos | Select2 | `content/library.html`, ajuda editorial | adaptar | `pending` |
| `index.html` | standalone demo | dashboard, KPIs, funil, atividades | daterangepicker, ApexCharts, circle-progress | `workspace/home.html` | adaptar | `pending` |
| `invoice-create.html` | CRM/management demo | formulário de cobrança, itens, totais | Select2, datepicker, Cleave | `finance/service_price_form.html` | adaptar | `pending` |
| `invoice-view.html` | CRM/management demo | resumo, itens, totais, impressão | jquery.print | `finance/charge_list.html` e futuro detalhe autorizado | adaptar | `pending` |
| `leads-create.html` | CRM/management demo | formulário de lead, selects, etapas | Select2 | sem destino direto | não usar | `pending` |
| `leads-view.html` | CRM/management demo | perfil de lead, abas, timeline | Select2 | sem destino direto | não usar | `pending` |
| `leads.html` | CRM/management demo | tabela de leads, filtros, ações | DataTables, Select2 | sem destino direto | não usar | `pending` |
| `partials/customizer.html` | partial | seletor de tema, fonte, navegação e skin | nenhum | sem destino direto | não usar | `pending` |
| `payment.html` | standalone demo | tabela financeira, filtros, estados | DataTables | `finance/charge_list.html` | adaptar | `pending` |
| `projects-create.html` | CRM/management demo | wizard, formulário, editor, datas | jQuery Steps/Validation, Select2, Quill, datepicker | `goals/form.html`, fluxos longos de consentimento | adaptar | `pending` |
| `projects-view.html` | CRM/management demo | progresso, detalhes, timeline, gráfico | ApexCharts | `goals/detail.html`, consentimentos | adaptar | `pending` |
| `projects.html` | CRM/management demo | listagem, filtros, tabela, progresso | DataTables, Select2 | `goals/list.html`, `consents/center.html` | adaptar | `pending` |
| `proposal-create.html` | CRM/management demo | formulário editorial, tags, editor, datas | Tagify, Quill, Select2, datepicker | `content/editorial_create.html` | adaptar | `pending` |
| `proposal-edit.html` | CRM/management demo | edição, tags, editor, datas | Tagify, Quill, Select2, datepicker | `content/editorial_create.html`, versões | adaptar | `pending` |
| `proposal-view.html` | CRM/management demo | detalhe, ações, comentários, anexos | Tagify, Quill, Select2 | `content/editorial_detail.html`, preview/compare | adaptar | `pending` |
| `proposal.html` | CRM/management demo | listagem, progresso, filtros, tabela | DataTables, Tagify, Quill, Select2, circle-progress | `content/editorial_index.html` | adaptar | `pending` |
| `reports-leads.html` | report demo | KPIs, gráficos, filtros, listas | ApexCharts, circle-progress, Select2 | `analytics/report_list.html` | adaptar | `pending` |
| `reports-project.html` | report demo | progresso, calendário, gráficos, timeline | ApexCharts, circle-progress, jquery.calendar | `analytics/clinic_panel.html`, relatórios | adaptar | `pending` |
| `reports-sales.html` | report demo | KPIs, gráficos, ranking, progresso | ApexCharts, circle-progress | `analytics/clinic_panel.html`, financeiro | adaptar | `pending` |
| `reports-timesheets.html` | report demo | horas, gráficos, ranking, progresso | ApexCharts, circle-progress | sem destino direto | não usar | `pending` |
| `settings-customers.html` | settings demo | preferências, formulário, selects | Select2 | `clinics/setup.html` | adaptar | `pending` |
| `settings-email.html` | settings demo | SMTP/notificações, switches, selects | Select2 | `scheduling/reminder_preferences.html` | adaptar | `pending` |
| `settings-finance.html` | settings demo | moeda, impostos, campos financeiros | Select2 | `finance/service_price_form.html` | adaptar | `pending` |
| `settings-gateways.html` | settings demo | provedores de pagamento, credenciais | Select2 | sem destino direto | não usar | `pending` |
| `settings-general.html` | settings demo | identidade, endereço, preferências gerais | nenhum | `clinics/setup.html` | adaptar | `pending` |
| `settings-leads.html` | settings demo | estados e preferências de leads | Select2 | sem destino direto | não usar | `pending` |
| `settings-localization.html` | settings demo | idioma, fuso, formatos, selects | Select2 | `clinics/setup.html` | adaptar | `pending` |
| `settings-miscellaneous.html` | settings demo | opções diversas, switches, selects | Select2 | sem destino direto | não usar | `pending` |
| `settings-recaptcha.html` | settings demo | chaves reCAPTCHA e switches | Select2 | sem destino direto | não usar | `pending` |
| `settings-seo.html` | settings demo | metadados, indexação, selects | Select2 | sem destino direto | não usar | `pending` |
| `settings-support.html` | settings demo | preferências de suporte, contatos | Select2 | `content/reports.html` como referência secundária | adaptar | `pending` |
| `settings-tags.html` | settings demo | lista/edição de etiquetas | nenhum | `content/editorial_*` | adaptar | `pending` |
| `settings-tasks.html` | settings demo | estados, prioridades e defaults | Select2 | `goals/*` | adaptar | `pending` |
| `widgets-charts.html` | widget catalogue | famílias de gráficos e legendas | ApexCharts, daterangepicker, Select2 | componentes de analytics | adaptar | `pending` |
| `widgets-lists.html` | widget catalogue | listas, avatares, progresso, pagamentos | circle-progress, Select2 | componentes de lista reutilizáveis | adaptar | `pending` |
| `widgets-miscellaneous.html` | widget catalogue | timeline, ratings, progresso, utilitários | ApexCharts, circle-progress, daterangepicker, Select2 | componentes compartilhados | adaptar | `pending` |
| `widgets-statistics.html` | widget catalogue | cartões KPI, tendências, progresso | daterangepicker, Select2 | `components/summary_card.html`, analytics | adaptar | `pending` |
| `widgets-tables.html` | widget catalogue | tabelas responsivas, estados, ações | ApexCharts, Select2, time-to | `components/responsive_table.html` | adaptar | `pending` |

## Current source runtime assets

The source currently contains **17** files under `static/`; each must be independently accepted or replaced during migration:

- `static/duralux/css/bootstrap.min.css` — `pending`
- `static/duralux/css/product-integration.css` — `pending`
- `static/duralux/css/theme.min.css` — `pending`
- `static/duralux/images/favicon.svg` — `pending`
- `static/duralux/images/logo_header.webp` — `pending`
- `static/duralux/images/logo_login.webp` — `pending`
- `static/duralux/js/bootstrap.bundle.min.js` — `pending`
- `static/duralux/js/dashboard-charts.js` — `pending`
- `static/duralux/js/form-behaviors.js` — `pending`
- `static/duralux/js/lesson-player.js` — `pending`
- `static/duralux/js/product-shell.js` — `pending`
- `static/duralux/js/visual-reference-charts.js` — `pending`
- `static/duralux/vendors/apexcharts/apexcharts.min.js` — `pending`
- `static/duralux/vendors/css/feather.min.css` — `pending`
- `static/duralux/vendors/fonts/feather.eot` — `pending`
- `static/duralux/vendors/fonts/feather.ttf` — `pending`
- `static/duralux/vendors/fonts/feather.woff` — `pending`

## Coverage and constraints

- HTML matrix rows: **77**; unmapped against prior evidence: **0**.
- The 8 documentation HTMLs remain design/licensing evidence, never application screens.
- SCSS, sourcemaps, demo images, sample data and vendor bundles are inventory only. Runtime promotion requires a real consumer, compatible version, local serving, license review and an explicit allowlist.
- Brand candidates present locally include `assets/images/logo_login.webp`, `assets/images/logo_header.webp` and `assets/images/favicon.svg`; their migration status remains `pending`.
