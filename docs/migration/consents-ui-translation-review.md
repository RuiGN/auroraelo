# Revisão independente — tradução da interface de consentimentos

Data: 2026-09-08. Revisão estática e restrita ao escopo declarado em
`docs/migration/consents-ui-scope.json`; nenhum teste foi executado porque a
regressão PostgreSQL principal estava em andamento.

## Veredito

**Aprovado quanto à especificação e à qualidade, com uma recomendação de
cobertura não bloqueante.** O recorte traduz apenas textos fixos da interface,
rótulos de apresentação, mensagens de validação e os nomes conhecidos das
finalidades. Não foi encontrada alteração semântica em autorização, isolamento
por clínica, manifestações, evidências ou operações de revogação.

## Evidência revisada

- Os seis templates marcam o texto fixo com `translate` ou `blocktranslate`.
  Título, versão, conteúdo, consequência da recusa, alternativa e contato do
  documento continuam sendo campos do `ConsentDocument`; nenhum desses campos
  é enviado ao mecanismo de tradução. A autoescapagem do template continua
  ativa, inclusive com `linebreaks`, que escapa o conteúdo antes de inserir os
  parágrafos.
- A finalidade usa um catálogo fechado: `gettext_noop` marca apenas o rótulo e
  `gettext` o resolve no idioma ativo. A chave canônica, como `communication`,
  permanece no documento e nas manifestações.
- Os valores submetidos e persistidos continuam `accepted`, `refused` e
  `revoked`. `consent_center` traduz somente os rótulos exibidos. As ações de
  auditoria continuam códigos estáveis como `consent_accept`, `consent_refuse`,
  `consent_revoke` e `permission_change`.
- `tests/test_consents_ui_translations.py` compara `publication_payload` antes e
  depois das decisões, verifica a sequência canônica e os hashes da manifestação,
  impede opção previamente marcada e confirma que erros não criam manifestação
  adicional.
- A autorização continua aplicada antes da apresentação: os seletores exigem
  vínculo ativo e filtram audiência e clínica; a fila exige `clinic_admin`; e o
  reconhecimento busca o item pelo identificador e pela clínica ativa. Os testes
  cobrem paciente proibido, administrador autorizado e item de outra clínica
  recusado sem mudança de estado.
- A fila monta `PAT-` a partir de HMAC limitado à clínica e não entrega UUID ou
  e-mail do titular. Ela apresenta somente referência pseudonimizada, rótulo da
  finalidade, título/versão do documento, identificador do despacho e data. O
  motivo privado não faz parte de `RevocationWorkRow`; somente seu digest é
  persistido na manifestação. O teste afirma que motivo, UUID e e-mail não
  aparecem na fila.
- Os templates de erro exibem mensagens fixas de validação e rótulos de campos,
  sem renderizar `request.POST`, `cleaned_data`, motivo ou referência informada.
  O erro da fila recebe apenas as mensagens fechadas de
  `acknowledge_revocation_work_item`; nenhuma delas incorpora dados privados.

## Achado acionável

**Baixa prioridade — cobertura explícita da confidencialidade nos erros.** O teste
afirma que `Motivo original privado.` não aparece na central nem na fila, mas não
repete uma asserção negativa sobre o motivo submetido na resposta 400/409 de
`consent_revoke`. O código atual não vaza esse valor: o template renderiza apenas
rótulos e erros, e as mensagens do serviço não interpolam o motivo. Ainda assim,
uma asserção negativa nessa resposta tornaria o contrato de privacidade resistente
a regressões futuras. A mesma proteção pode ser aplicada à referência operacional
na resposta de erro da fila.
