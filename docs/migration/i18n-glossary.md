# Mindcare launch-language glossary

Reviewed proposal for S14.01, dated 2026-09-08. These terms guide fixed product UI
for Brazilian Portuguese (`pt-br`), English (`en`) and Spanish (`es`). Context wins
over mechanical substitution; translators must use `pgettext` where the same source
word has different clinical or product meanings.

| Concept / context | pt-BR | English | Español | Review note |
| --- | --- | --- | --- | --- |
| product name | Mindcare | Mindcare | Mindcare | Brand; never translate. |
| patient / person receiving care | paciente | patient | paciente | Prefer “pessoa atendida” only where person-first wording is deliberately required. |
| therapist / treating professional | terapeuta | therapist | terapeuta | Do not broaden to physician. Use “profissional” / “professional” / “profesional” when role-neutral. |
| clinic / tenant organization | clínica | clinic | clínica | Organization, not a physical room. |
| professional | profissional | professional | profesional | Generic licensed/authorized care worker. |
| appointment | consulta | appointment | cita | Use “agendamento” / “scheduling” / “programación” for the act or schedule slot. |
| schedule / calendar | agenda | schedule / calendar | agenda / calendario | “Calendar” for visual calendar; “schedule” for availability. |
| consent (concept/document) | consentimento | consent | consentimiento | Surrounding UI only unless a localized legal version is explicitly published. |
| accept / refuse consent | aceitar / recusar | accept / decline | aceptar / rechazar | Avoid “reject” in supportive UI. Stable decision codes remain unchanged. |
| revoke consent | revogar consentimento | revoke consent | revocar consentimiento | Revocation stops future use; it does not erase evidence. |
| required | obrigatório | required | obligatorio | Agreement may use “aceite necessário” when legally reviewed. |
| optional authorization | autorização opcional | optional authorization | autorización opcional | Must never imply preselection. |
| workspace | área de trabalho | workspace | espacio de trabajo | Product shell/home context. Do not use “tenant”. |
| clinic switch | trocar de clínica | switch clinic | cambiar de clínica | Language change must not change clinic/authorization. |
| dashboard | painel | dashboard | panel | Prefer natural UI term; avoid untranslated “dashboard” in pt-BR/es. |
| account | conta | account | cuenta | Identity/login account. |
| sign in / sign out | entrar / sair | sign in / sign out | iniciar sesión / cerrar sesión | Use consistently in authentication UI. |
| multi-factor authentication | autenticação multifator | multi-factor authentication | autenticación multifactor | Abbreviation MFA may remain after first expansion. |
| recovery code | código de recuperação | recovery code | código de recuperación | Security credential; never log or translate the code itself. |
| session | sessão | session | sesión | Authenticated device/browser session. |
| journal | diário | journal | diario | Patient-authored content inside it stays unchanged. |
| check-in | check-in | check-in | registro de estado | Product term may remain “check-in” in pt-BR after UX review. |
| goal | meta | goal | objetivo | Care/self-management objective. |
| exercise | exercício | exercise | ejercicio | Therapeutic assignment context, not necessarily physical exercise. |
| low-energy mode | modo de baixa energia | low-energy mode | modo de baja energía | Supportive wording; avoid diagnostic claims. |
| waitlist | lista de espera | waitlist | lista de espera | Scheduling context. |
| reminder | lembrete | reminder | recordatorio | Fixed notification shell is translated; service/name/time data is preserved. |
| message / conversation | mensagem / conversa | message / conversation | mensaje / conversación | Never translate user-authored message bodies. |
| notification | notificação | notification | notificación | Translate fixed event text; preserve stable event kind. |
| content / recommendation | conteúdo / recomendação | content / recommendation | contenido / recomendación | Authored content is preserved; fixed recommendation-state UI is translated. |
| report (analytics) | relatório | report | informe | For abuse report use “denúncia” / “report” / “denuncia”; add context. |
| invoice | fatura | invoice | factura | Presentation term; fiscal/legal document naming needs jurisdiction review. |
| receipt | recibo | receipt | recibo | Document type code remains stable. |
| charge | cobrança | charge | cobro | Do not confuse with card/financial fee. |
| amount / total | valor / total | amount / total | importe / total | Format by locale while preserving numeric value. |
| currency | moeda | currency | moneda | Currency is an independent setting; never infer it from language. |
| time zone | fuso horário | time zone | zona horaria | Independent setting; language switches cannot alter instants. |
| date / time | data / horário | date / time | fecha / hora | Localize presentation and parsing only under an explicit field contract. |
| privacy | privacidade | privacy | privacidad | Legal text requires human/legal review. |
| audit trail | trilha de auditoria | audit trail | registro de auditoría | Audit action/resource/outcome codes are not translated. |
| access denied | acesso negado | access denied | acceso denegado | Avoid exposing authorization details. |
| required field | campo obrigatório | required field | campo obligatorio | Framework/form UI. |
| invalid value | valor inválido | invalid value | valor no válido | Keep stable API/error codes unchanged. |
| save / cancel / continue | salvar / cancelar / continuar | save / cancel / continue | guardar / cancelar / continuar | Preferred core actions. |
| back | voltar | back | volver | Navigation action. |

## Stable values that are never translated

Keep enum values, permission/role codes, status codes, audit actions, resource types,
API error codes, URL names, HTTP methods, UUIDs, hashes, document numbers, cache keys,
CSS/DOM hooks and database values unchanged. Translate their display labels through
an explicit mapping. Currency codes such as `BRL`, `USD`, `EUR` remain ISO codes;
format symbols and separators from the selected display locale without converting
the amount or changing the configured currency.

## Authored and regulated content

Language selection applies to product UI. It does not translate journal/check-in
text, clinical notes, chat, clinic/editor-authored learning content, communication
templates, uploaded documents or other free text. Clearly label the content's own
language when the product later supports that metadata.

Consent UI and consent documents are separate. Buttons, errors and explanations
around a consent can follow the selected UI language. A consent title/body and the
exact version accepted remain immutable. Any pt-BR/en/es legal translations require
separately identified versions, provenance, legal/clinical review and an explicit
acceptance relationship; they are not interchangeable strings in a UI catalog.

## Review state

This glossary is approved as the engineering proposal for catalog work by the
S14.01 inventory reviewer. It is not clinical or legal approval of translated
consent language, nor proof that English or Spanish catalogs are complete. Flag
country-specific legal, fiscal and professional-title variants for a native
language reviewer before publication.

