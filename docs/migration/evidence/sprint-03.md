# Evidência de aceite — Sprint 3

Data da revisão: 08/09/2026.

A auditoria inicial confrontou as asserções com a suíte anterior de 1.268 testes.
As duas lacunas identificadas foram fechadas com testes adicionais de expiração
TOTP e superusuário sem vínculo clínico. Todos os identificadores de testes
citados abaixo foram reencontrados no JUnit final `destination-components-final-pytest.xml`,
com **1.286 aprovados, zero falhas, erros ou ignorados**. As evidências de código
novas estão em `../identity-boundary-report.md`.

Os casos HTTP dependentes de templates não são uma pendência desta Sprint: o
próprio aceite determina sua reexecução depois da Sprint 8 (S08.08). Esta
análise considera somente os contratos de backend e as asserções HTTP já
presentes.

## Resultado recomendado

| ID | Estado recomendado | Resultado |
| --- | --- | --- |
| S03.01 | concluída | Cadastro por convite, autenticação, recuperação, logout, sessões, reautenticação, limites e descarte de redirect externo possuem asserções diretas fresh-passed. |
| S03.02 | concluída | Expiração de código ainda não consumido comprovada por relógio controlado, seguida de aceitação de código corrente; demais contratos preservados. |
| S03.03 | concluída | Superusuário sem vínculo recebe 403 e negativa explícita da política clínica; seleção, matriz de papéis e white-label preservados. |
| S03.04 | concluída | Cadastros de pacientes e profissionais, relacionamento assistencial e acesso/negação ao registro por vínculo são afirmados diretamente. |
| S03.05 | concluída | Versão, integridade, revogação, fila, comando, propagação e efeitos de acesso/compartilhamento estão afirmados diretamente. |
| S03.06 | concluída | Cadeia de auditoria, exportação, eliminação, retenção, reautenticação, download temporário e redação de logs estão afirmados diretamente. |

## S03.01

> Validar cadastro, autenticação, recuperação, logout, sessões, reautenticação
> e limites de tentativas; preservar redirects seguros.

Casos fresh-passed e comportamento efetivamente afirmado:

- `tests.test_accounts_authentication::test_new_recipient_accepts_http_invitation_and_creates_membership`: cria a identidade pelo convite, redireciona ao login e persiste o vínculo esperado.
- `tests.test_accounts_authentication::test_login_uses_canonical_email_rotates_session_and_selects_active_tenant`: autentica por e-mail canônico, gira a chave da sessão e seleciona a clínica ativa.
- `tests.test_accounts_authentication::test_logout_is_post_only_flushes_session_and_is_audited`: recusa GET, encerra por POST, troca a sessão e registra auditoria.
- `tests.test_accounts_authentication::test_password_recovery_response_is_generic_for_known_and_unknown_email`: mantém resposta não enumerável e só envia mensagem para a identidade existente.
- `tests.test_accounts_authentication::test_password_reset_is_single_use_and_invalidates_all_existing_sessions`: troca a senha, invalida todas as sessões e rejeita reutilização do link.
- `tests.test_accounts_authentication::test_login_rate_limit_is_configurable_and_non_enumerating` e `test_password_recovery_rate_limit_is_configurable`: retornam 429 e `Retry-After` nos respectivos limites.
- `tests.test_account_session_mfa::test_registered_session_has_minimized_device_data_and_enforced_expiry`: minimiza origem/dispositivo e rejeita a sessão expirada.
- `tests.test_account_session_mfa::test_revoking_all_other_sessions_requires_current_password` e `test_sensitive_reauthentication_is_rate_limited_per_identity`: exigem senha atual e limitam tentativas de reautenticação.
- `tests.test_account_session_mfa::test_mfa_enroll_post_confirms_factor_once_and_keeps_local_continue_url`: injeta um `mfa_next` externo e afirma que o destino resultante é o workspace local.

Não foi encontrada lacuna de backend que impeça o aceite. A verificação visual e
de acessibilidade dos formulários continua no marco S08.08, conforme o PRD.

## S03.02

> Validar matrícula/verificação de MFA, QR Code local, segredo criptografado,
> recuperação, expiração e prevenção de reutilização.

Casos fresh-passed e comportamento efetivamente afirmado:

- `tests.test_account_session_mfa::test_totp_enrollment_requires_confirmation_and_recovery_codes_are_single_use`: mantém o fator não confirmado até um TOTP válido, afirma que o segredo não é armazenado em claro, emite oito códigos de recuperação, consome cada código uma vez e rejeita reutilização do mesmo passo TOTP.
- `tests.test_account_session_mfa::test_mfa_enroll_get_renders_local_qr_and_manual_key_without_cache`: afirma QR SVG local, chave manual, URI `otpauth` válida somente no contexto e cabeçalhos `no-store`/`noindex`.
- `tests.test_account_session_mfa::test_enrollment_confirmation_consumes_the_totp_step` e `test_confirmed_enrollment_cannot_issue_another_recovery_set`: impedem replay da confirmação e nova emissão indevida do conjunto de recuperação.
- `tests.test_account_session_mfa::test_totp_confirmation_and_verification_are_rate_limited`: afirma orçamento de tentativas para matrícula e verificação.
- `tests.test_account_session_mfa::test_administrative_mfa_reset_is_scoped_audited_and_ends_target_sessions`: cobre recuperação administrativa autorizada, auditada e com encerramento das sessões do alvo.

Lacuna fechada por `tests.test_identity_migration_boundaries::test_expired_totp_challenge_does_not_grant_mfa_session`.
O código submetido está expirado e ainda não foi consumido; um código corrente
é aceito em seguida. A política existente de confiança da sessão foi preservada.

## S03.03

> Validar seleção e troca de clínica, vínculos ativos, matriz de papéis e
> white-label; comprovar que superusuário técnico não substitui vínculo clínico
> exigido.

Casos fresh-passed e comportamento efetivamente afirmado:

- `tests.test_tenant_middleware::test_authenticated_explicit_session_selection_resolves_membership` e `test_header_takes_precedence_over_session_and_is_reauthorized`: resolvem uma seleção explícita somente após reautorizar o vínculo.
- `tests.test_tenant_middleware::test_inactive_expired_or_future_membership_is_rejected`: rejeita vínculos inativo, expirado ou ainda não vigente.
- `tests.test_workspace_foundation::test_switching_clinic_changes_workspace_actions`: troca a clínica ativa e afirma a mudança das ações conforme o papel no novo tenant.
- `tests.test_clinic_role_matrix::test_role_action_matrix_applies_least_privilege`: compara cada ação com a matriz completa esperada para cada papel.
- `tests.test_whitelabel::test_whitelabel_tenant_isolation_and_permissions`: recusa gestão por terapeuta e operações cross-tenant sobre domínio/tema.
- `tests.test_clinic_setup::test_saved_branding_is_applied_to_the_active_tenant_workspace`: afirma aplicação da marca da clínica ativa no workspace.

Lacuna fechada por `tests.test_identity_migration_boundaries::test_technical_superuser_without_membership_has_no_clinical_scope`.
A resposta HTTP e a política clínica negam acesso ao superusuário sem vínculo.

## S03.04

> Validar pacientes, profissionais, relacionamentos, cadastros e acesso aos
> registros por ator autorizado.

Casos fresh-passed e comportamento efetivamente afirmado:

- `tests.test_patient_management::test_admin_registers_minimized_tenant_patient_and_blocks_exact_duplicate`: cadastra paciente no tenant com dados minimizados e bloqueia duplicidade exata.
- `tests.test_professional_management::test_admin_registers_complete_professional_profile_with_safe_photo_and_audit`: cadastra profissional, valida foto privada e registra auditoria.
- `tests.test_patient_management::test_admin_creates_and_closes_explicit_patient_professional_link`: cria e encerra relacionamento assistencial explícito.
- `tests.test_patient_authorization::test_clinical_access_requires_active_therapist_patient_relationship`: nega sem vínculo, permite com vínculo ativo e volta a negar após inativação.
- `tests.test_patient_authorization::test_administrative_staff_can_read_demographics_but_not_clinical_data`: limita equipe administrativa a dados demográficos.
- `tests.test_patient_management::test_therapist_opens_linked_patient_ficha_and_audits` e `test_therapist_denied_unlinked_patient_ficha`: permitem a ficha ao terapeuta vinculado, auditam a leitura e negam o não vinculado.

Não foi encontrada lacuna de backend que impeça o aceite.

## S03.05

> Validar consentimentos versionados, revogação, filas e comandos de
> propagação, além dos efeitos sobre acesso e compartilhamento.

Casos fresh-passed e comportamento efetivamente afirmado:

- `tests.test_versioned_consents::test_published_document_has_integrity_hash_and_cannot_be_silently_changed` e `test_current_documents_respect_audience_version_and_effective_date`: afirmam integridade imutável e seleção da versão vigente por público/data.
- `tests.test_consent_access_lifecycle::test_revocation_is_prospective_append_only_and_audited`: acrescenta manifestação de revogação, bloqueia novo acesso à finalidade, cria obrigação pendente e audita.
- `tests.test_consent_access_lifecycle::test_clinic_admin_consumes_revocation_work_queue_through_http`: expõe a fila somente ao administrador e persiste reconhecimento explícito.
- `tests.test_consent_access_lifecycle::test_pending_revocation_dispatches_have_an_operational_command`: executa o comando, falha enquanto falta reconhecimento e confirma depois da evidência operacional.
- `tests.test_consent_access_lifecycle::test_revocation_creates_one_obligation_per_configured_destination`: cria uma obrigação para cada destino configurado.
- `tests.test_versioned_consents::test_purpose_gate_denies_unknown_but_never_blocks_basic_rights`: nega finalidade protegida sem base e preserva direitos básicos documentados.
- `tests.test_routines_medications::test_medication_sharing_consent_and_audit`: nega compartilhamento antes do consentimento, permite após concessão, volta a negar após revogação e audita ambos os eventos.

Não foi encontrada lacuna de backend que impeça o aceite.

## S03.06

> Validar trilha de auditoria, exportação/eliminação conforme políticas
> existentes, reautenticação e downloads temporários; impedir exposição de
> dados sensíveis em logs.

Casos fresh-passed e comportamento efetivamente afirmado:

- `tests.test_audit_trail::test_recorded_event_is_minimized_tenant_scoped_and_chain_verified` e `test_chain_verification_detects_out_of_band_tampering`: afirmam minimização, escopo tenant, encadeamento e detecção de adulteração.
- `tests.test_audit_trail::test_controlled_export_is_minimized_and_audited`: exporta campos controlados, exclui conteúdo clínico e audita a exportação.
- `tests.test_data_subject_rights::test_export_requires_recent_reauthentication_and_is_encrypted`: rejeita senha incorreta, exige provas distintas de reautenticação para gerar e baixar, cifra o artefato, marca expiração e impede reutilização da prova.
- `tests.test_data_subject_rights::test_lifecycle_propagates_to_every_destination_and_documents_retention`: propaga eliminação a banco, armazenamento e arquivo regulado, registra confirmações e justifica retenção legal.
- `tests.test_data_subject_rights::test_failed_destination_keeps_request_open_for_reprocessing`: impede conclusão falsa quando um destino não elimina os dados.
- `tests.test_security_controls::test_private_download_grant_is_tenant_bound_and_expires`: permite o objeto somente no tenant correto e rejeita a concessão depois do prazo.
- `tests.test_observability::test_json_logging_contains_only_safe_structured_context`: afirma que corpo clínico, senha, token, dados privados e identificador bruto do ator não aparecem no log JSON.
- `tests.test_account_session_mfa::test_full_enrollment_exception_report_redacts_every_provisioning_frame` e `test_mfa_verify_exception_report_redacts_submitted_code`: impedem vazamento de segredo, URI, recuperação e código submetido em relatórios de exceção.

Não foi encontrada lacuna de backend que impeça o aceite.

## Escopo da conclusão

S03.01 a S03.06 possuem evidência de backend e HTTP aprovada no destino.
Isso não fecha automaticamente as dependências do quadro, os templates clínicos,
a cobertura de 90% nem o aceite integrado de S08.08/Sprint 12. Não houve ação
em produção ou transferência de dados operacionais.
