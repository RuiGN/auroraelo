# Roteiro ponta a ponta (app × servidor real)

O `npm test` fala com um servidor falso que responde pelo OpenAPI. Este roteiro usa o
**mesmo código do app** (cliente HTTP, sessão, loaders e ações) contra o Django em
execução, com dados criados pelos serviços de domínio que as telas da equipe usam.

```sh
cd mobile/posalta
bash tests/e2e/run.sh        # ou: npm run test:e2e
```

O que ele percorre (`live.e2e.ts`): ativar a conta com o código do convite; os 18
loaders contra respostas reais; aceite dos documentos obrigatórios; cuidado (dose, plano,
hábito, exercício, pouca energia); diário, meta, vontade de usar e pedido de acesso da
equipe; agenda (pedir, cancelar, pedir de novo, remarcar); plano de recaída, plano
urgente e contatos; consentimento opcional e direito do titular; renovação do token,
reuso do token de renovação (derruba a sessão) e saída.

Notas: o banco é descartável (SQLite em arquivo, `config.settings.test`); o `runserver`
não lê corpo "chunked", então o transporte de teste envia `Content-Length` (o `fetch`
real do app já envia). Não roda em aparelho nem exercita a interface: para isso, ver
"Não verificado" no README do app.
