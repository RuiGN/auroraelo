# Interface de consentimentos — tradução

Data: 2026-09-08. Escopo restrito à interface existente de consentimentos da migração Duralux.

Os seis templates usam `translate`/`blocktranslate` para títulos, instruções, ações, estados vazios, fila e erros. Os rótulos de finalidade usam `gettext_noop` no catálogo estático e `gettext` durante a requisição, preservando o retorno `str` e o nome público `purpose_label_pt_br`. Os rótulos de decisões são traduzidos na apresentação, sem alterar os valores persistidos `accepted`, `refused` e `revoked` nem os modelos. Os formulários traduzem decisões, revogação e identificador da solicitação; o template de erro apresenta os rótulos dos campos, sem expor as chaves internas de `form.errors`. As mensagens fixas já marcadas nos serviços são incluídas na entrega dos catálogos.

Título, versão, conteúdo, consequências da recusa, alternativas e contato da clínica continuam no idioma original da publicação. A renderização mantém o escape dos dados, inclusive conteúdo com marcação HTML, e não chama tradução sobre os campos do documento. Nenhuma regra de permissão, confirmação, manifestação, revogação, hash, auditoria ou isolamento foi alterada. Nenhuma migration, edição de catálogo compartilhado, commit ou deploy foi realizada por este recorte.

`tests/test_consents_ui_translations.py` contém 13 casos parametrizados que cobrem pt-br/en/es: interface e documento original; recusa, aceite e revogação com códigos e evidência canônicos; erros de formulário e de serviço sem manifestação adicional; fila e confirmação com escopo de papel/clínica, referência minimizada do titular e ausência do motivo privado; resolução da finalidade após mudanças sucessivas de idioma. O teste de erro também verifica revogação antes de haver aceite (409 e nenhuma manifestação).

Validação:

- `.venv/bin/python -m ruff check consents tests/test_consents_ui_translations.py`: aprovado.
- `.venv/bin/python -m mypy consents/policies.py consents/forms.py consents/views.py tests/test_consents_ui_translations.py`: aprovado, quatro arquivos.
- Execução integrada do agente principal, registrada em `evidence/resume-focused.log` e `evidence/resume-focused.xml`: 51 testes aprovados em 13,11 s, incluindo 13 casos deste arquivo. As asserções adicionais finais sobre revogação sem aceite devem constar da regressão final do agente principal.
- Tentativa isolada `TEST_DATABASE=sqlite .venv/bin/python -m pytest tests/test_consents_ui_translations.py --no-cov -q --tb=short`: interrompida durante preparação do banco após 146,88 s, sem testes executados. Não representa aprovação nem reprovação funcional; a execução integrada em PostgreSQL fornece a evidência focada.

A entrega `evidence/consents-ui-translations.json` contém 46 mensagens com traduções en/es, no formato já usado por pessoas. O agente principal integra os catálogos, executa a matriz visual, atualiza o escopo cumulativo e executa a regressão completa. Este relatório não constitui aceite visual nem conclusão da Sprint 8 ou 14.
