# Auditoria de contratos — S00.03, S00.04 e S00.06

Data da revisão: 08/09/2026. Esta é uma auditoria documental e estática do
destino Mindcare. A origem `projetomnunes` foi mantida somente para leitura. Não
foram executados testes, requisições, banco real ou validação visual nesta tarefa.

## Resultado

Os inventários-base estão reconciliados: `routes-matrix.md` contém 182 entradas
(147 callbacks do projeto e 35 callbacks do Django Admin) e
`templates-matrix.md` contém os 97 templates em disco. A suíte PostgreSQL já
executada contém 1.253 casos aprovados, conforme
`evidence/destination-final-pytest.xml` (`failures="0"`, `errors="0"`). Essa
evidência sustenta muitos contratos funcionais e de autorização, mas não fecha
por si só S00.03, S00.04 ou S00.06.

Estado recomendado após esta auditoria:

| Tarefa | Estado recomendado | Justificativa |
| --- | --- | --- |
| S00.03 | manter aberta | todas as rotas foram inventariadas, mas 35 callbacks do Admin continuam framework-managed e sem exercício documentado; 15 callbacks próprios não têm restrição de método por decorator e exigem contrato explícito por função/teste |
| S00.04 | manter aberta | os 97 arquivos, extends, includes literais, forms e raízes de contexto estão inventariados; os muitos `extends layout_template` dependem de contexto construído pela view e ainda não há renderização documentada de todos os pares rota/template/estado |
| S00.06 | manter aberta | há evidência funcional para jornadas críticas dos quatro perfis, porém não houve inspeção visual, responsiva, por teclado ou dos estados de erro nesta auditoria |

## Camadas transversais de autorização e contexto

`@login_required` prova apenas autenticação. A clínica ativa vem do middleware de
clínica e é novamente exigida por helpers como `_clinic_and_actor`, `_clinic_id`
e `_request_context`. As decisões relevantes ocorrem de forma transitiva:

- `clinics.policies.ClinicAuthorizationPolicy` nega ações desconhecidas, exige
  ator e clínica ativos e consulta `ClinicMembership.objects.for_clinic(...).active_on(...)`.
- `clinics.policies.has_active_clinic_role` revalida usuário, clínica, papel e
  vigência. Não se deve substituir esse contrato por flags mantidas na sessão.
- `people.policies.PatientAuthorizationPolicy` acrescenta o papel de paciente e,
  para leitura clínica, uma `CareRelationship` ativa entre terapeuta e paciente.
- seletores de agenda filtram paciente pelo próprio perfil, terapeuta pelos
  vínculos ativos e equipe pelos papéis `clinic_admin`/`administrative_staff`;
  conversas ainda exigem participação ativa.
- diário e metas combinam `for_clinic`, titularidade do perfil, visibilidade,
  pedido/concessão de acesso e vínculo terapêutico. A presença de um UUID na URL
  não autoriza o objeto.
- conteúdo público ao membro exige publicação e audiência; edição, publicação,
  denúncias e autoria de cursos delegam decisões de papel e estado a services.
  A participação em curso acrescenta matrícula, pré-requisitos, dono da tentativa
  e conclusão.
- finanças autoriza `clinic_admin` ou `administrative_staff`; alterações de preço
  usam ainda a ação `clinic.manage`. Relatórios distinguem paciente (individual)
  e administrador de clínica (operacional), e downloads exigem ator, clínica,
  chave temporária e validade.
- os context processors `clinics.context_processors.clinic_navigation` e
  `consents.context_processors.revocation_work_notifications` acrescentam clínica,
  navegação e pendências às páginas consumidoras; eles não concedem acesso.

## Exceções e contratos específicos de rota

| Rota/família | Contrato efetivo e exceção ao resumo do decorator | Evidência existente |
| --- | --- | --- |
| `/`, `/health/live/`, `/health/ready/` | callbacks públicos sem decorator; home e liveness devolvem resposta simples, readiness consulta banco/cache e devolve 503 de forma controlada. O método não está explicitamente limitado | `config.views`; cobertura de health não foi identificada nominalmente no JUnit, portanto continua uma lacuna de S00.03 |
| `/admin/login/` do projeto | redirect público para `account_login?next=/admin/`; o Admin também expõe seu callback homônimo sob o mount. A matriz deve preservar essa distinção | `tests.test_account_session_mfa::test_django_admin_login_uses_account_entrypoint` |
| `/workspace/` e `/workspace/detached/` | autenticados; MFA e clínica ativa são gates de middleware. `/workspace/` pode redirecionar à variante salva; os callbacks não têm `require_GET` | `test_privileged_session_cannot_open_workspace_until_mfa_is_verified`, `test_workspace_requires_authenticated_active_tenant`, `test_default_workspace_route_restores_the_saved_layout` |
| troca de clínica | review é GET sem mutação e só aceita clínica retornada por `active_clinics_for_actor`; confirmação é POST, reautoriza, gira rastreamento da sessão e aceita apenas redirect local | `test_switch_review_is_get_only_revalidates_and_does_not_mutate`, `test_confirm_switch_reauthorizes_rotates_session_and_redirects_locally`, `test_switch_blocks_external_redirect` |
| login, recuperação e convite | login/recuperação são públicos e não enumeram identidade; logout é POST e o service exige sessão; convite de usuário existente pode exigir login do destinatário | `test_login_uses_same_generic_error_for_unknown_wrong_or_tenantless_identity`, `test_logout_is_post_only_flushes_session_and_is_audited`, `test_existing_recipient_must_log_in_to_accept_http_invitation` |
| MFA e sessões | login é insuficiente para ações privilegiadas: desafio/enrollment, limite de tentativas, no-store e reautenticação aplicam gates adicionais; reset administrativo exige admin verificado, senha atual e mesmo tenant | `test_administrative_mfa_reset_http_flow_requires_current_password`, `test_administrative_mfa_reset_denies_target_from_another_clinic`, `test_confirmed_mfa_challenge_hides_provisioning_material_and_disables_cache` |
| agenda | listagens são filtradas por papel; criação aceita paciente ou equipe conforme service; transições validam participante/vínculo, estado e clínica. Anexo exige acesso à conversa, não mera autenticação | `test_appointment_request_http_flow`, `test_cross_clinic_appointment_denied`, `test_schedule_and_cancel_appointment_reminder` |
| unidades, salas e espera | unidades/salas exigem administração conforme helper; fila de espera admite `clinic_admin` e `administrative_staff`, sempre no tenant | `test_unit_list_http`, `test_room_create_http`, `test_waitlist_cross_clinic_denied` |
| prontuário de paciente | diretório e cadastro seguem ações próprias; terapeuta só abre ficha clínica de paciente vinculado. Acesso demográfico e clínico não são equivalentes | `test_therapist_opens_linked_patient_ficha_and_audits`, `test_therapist_denied_unlinked_patient_ficha`, `test_patient_directory_http_supports_manual_registration` |
| diário/check-in | paciente é dono; visibilidade amarela exige pedido e concessão; privada impede pedido; terapeuta desvinculado é negado | `test_sharing_traffic_light_yellow_request_grant_and_revoke_flow`, `test_therapist_cannot_request_access_to_private_red_entry`, `test_unlinked_therapist_cannot_request_access_to_yellow_entry`, `test_checkin_http_flow_submit_and_history` |
| metas/exercícios | metas são do paciente; compartilhamento controla visão do terapeuta. Várias views de exercício são GET/POST por ramificação sem decorator de método, razão para mantê-las explicitamente pendentes | `test_goal_panel_http_flow`, `test_goal_access_denied_after_revocation`, `test_exercise_http_flow` |
| conteúdo editorial | callbacks autenticados delegam o gate de admin, tenant, estado editorial, autoria/revisor e credencial a services; IDs estrangeiros são não enumeráveis (404 em vários fluxos) | `test_editorial_http_surface_supports_complete_versioned_workflow`, `test_editorial_direct_ids_are_non_enumerating_and_tenant_scoped`, `test_editorial_surface_requires_clinic_admin_role` |
| cursos | autoria exige admin; participante exige matrícula ativa e curso/aula do tenant. Certificado do participante não tem decorator de método; verificação por código é GET público e minimizado | `test_participant_quiz_http_is_tenant_safe_idempotent_and_accessible`, `test_lesson_page_denies_unenrolled_member`, `test_participant_certificate_http_requires_completion_and_verifies_publicly` |
| analytics e relatórios | dashboards revalidam papel em services; relatório individual é do paciente, operacional é do admin; download requer chave e validade | `test_patient_dashboard_requires_patient_role`, `test_therapist_dashboard_cross_clinic_denied`, `test_operational_report_requires_admin`, `test_report_download_wrong_actor_denied` |
| finanças | lista e mutações passam por papel financeiro e tenant; preço é mais restrito (`clinic.manage`). Objeto de outra clínica é negado | `test_set_service_price_requires_admin`, `test_charge_cross_clinic_denied`, `test_charge_list_http` |
| `/design-system/` | autenticado mais `is_staff`; aceita GET e POST para o formulário de referência, embora a matriz marque método não verificado. Não é uma funcionalidade clínica | testes de componentes e `test_visual_reference_uses_only_the_duralux_foundation`; sem aceite visual |
| Django Admin | 35 callbacks são gerados pelo framework. Autenticação, MFA de entrada e alguns modelos estão cobertos, mas método e permissão por callback/objeto não foram auditados um a um | `test_django_admin_login_uses_account_entrypoint`; lacuna explícita |

## Contratos de templates

Todos os 97 templates compilam no JUnit por casos parametrizados de
`tests.test_template_compilation::test_application_template_compiles[...]`. Há
includes literais para os componentes de formulário, tabela, paginação, estados,
cards, navegação, mensagens, player de aula, calendário do diário e decisão de
consentimento. Não foi encontrado include cujo nome do arquivo seja calculado em
runtime.

O principal contrato dinâmico é `{% extends layout_template %}`. Ele aparece nas
páginas de domínio e exige que a view forneça um nome de layout confiável. As views
inspecionadas fornecem `layouts/vertical.html` ou uma variante allowlisted do
workspace. A compilação isolada não prova que todo caminho de erro fornece esse
contexto, nem que cada estado vazio, inválido, proibido e paginado renderiza.

Os context processors fornecem valores compartilhados, mas os `only` usados na
maioria dos includes de componentes estreitam corretamente seus contratos. A
exceção deliberada é `consents/partials/document_decision.html`, incluído sem
`only`, e portanto dependente também do contexto do centro de consentimentos.

## Jornadas críticas por perfil

| Perfil | Jornada auditada | Gates observados | Evidência funcional existente |
| --- | --- | --- | --- |
| paciente | login/MFA → clínica ativa → workspace → agenda → diário/check-in → metas → conteúdo/curso/relatório individual | identidade não enumerável, sessão/MFA, papel patient vigente, titularidade, matrícula/audiência, tenant | `test_login_uses_canonical_email_rotates_session_and_selects_active_tenant`, `test_appointment_request_http_flow`, `test_journal_views_create_and_list_flow`, `test_goal_panel_http_flow`, `test_participant_quiz_http_is_tenant_safe_idempotent_and_accessible`, `test_patient_dashboard_http` |
| terapeuta | login/MFA → dashboard → pacientes vinculados → agenda → conteúdo recomendado → diário compartilhado | papel therapist, vínculo ativo por paciente, visibilidade/consentimento, tenant | `test_active_therapist_must_enroll_mfa_before_workspace`, `test_dashboard_http_renders_cards_table_and_chart`, `test_therapist_opens_linked_patient_ficha_and_audits`, `test_therapist_denied_unlinked_patient_ficha`, `test_therapist_dashboard_excludes_non_shareable_checkins` |
| administrador de clínica | login/MFA → setup/white-label → profissionais/pacientes → agenda operacional → consentimentos → editorial/financeiro/analytics | papel clinic_admin vigente, ação específica, clínica ativa, reautenticação em ação sensível, isolamento | `test_identity_stage_posts_to_active_tenant_and_advances`, `test_professional_directory_http_is_accessible_and_permission_scoped`, `test_clinic_admin_consumes_revocation_work_queue_through_http`, `test_editorial_surface_requires_clinic_admin_role`, `test_operational_report_requires_admin` |
| administrador técnico | `/admin/login/` → login central → enrollment/challenge MFA → Django Admin | `is_staff`, MFA verificado e permissões Django por modelo/objeto; papel de clínica não substitui staff | `test_framework_staff_access_requires_mfa_without_clinic_role`, `test_admin_mfa_challenge_returns_to_original_admin_destination`, `test_django_admin_login_uses_account_entrypoint` |

## Lacunas que impedem declarar conclusão

1. Não existe evidência request-by-request para os 147 callbacks próprios; o JUnit
   contém ampla cobertura, mas não uma correspondência comprovada de 1:1 entre
   cada rota, método permitido, redirect e resposta esperada.
2. Os 35 callbacks do Admin não têm matriz de permissões por modelo/objeto e método.
3. Quinze callbacks próprios estão sem decorator de método: home,
   password-reset-complete, admin-login redirect, certificado do participante,
   criação editorial, referência visual, cinco views de exercícios, dois
   workspaces e dois health checks. O comportamento por método precisa ser
   confirmado ou documentado como intencional.
4. Compilação dos 97 templates não cobre todos os contextos e estados. Falta uma
   evidência automatizada que relacione rota, template usado, chaves mínimas,
   include/extends e ao menos happy path + forbidden/not-found/form-error onde
   aplicável.
5. A cobertura global registrada é 86%, abaixo do gate de 90%; não foi analisada
   cobertura específica das branches de autorização desta auditoria.
6. Não houve aceite visual. Os testes de classes, estrutura e compilação não
   comprovam fidelidade Duralux, responsividade, contraste, teclado, leitor de tela
   ou os quatro perfis em navegador.

