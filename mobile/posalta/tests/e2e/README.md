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

## Ambiente fiel ao de produção (`npm run test:e2e:staging`)

`run-staging.sh` repete o roteiro num ambiente descartável parecido com o da VPS:

- PostgreSQL 17 e Redis 8 de `compose.test.yml` (tmpfs; as imagens precisam estar no Docker);
- **settings de produção** (`config.settings.production`, chaves geradas na hora);
- **gunicorn com 3 processos**, como o `Dockerfile` (o limite de tentativas de login passa
  pelo Redis compartilhado);
- um servidor SMTP de captura (`smtp_sink.py`): o convite e a recuperação de senha saem
  por SMTP de verdade e o teste lê o código da mensagem recebida.

Cobre, além dos passos acima, a recuperação de senha por e-mail e o limite de tentativas.
Tudo é derrubado no fim.

Para testar o app num simulador ou aparelho contra esse ambiente, use
`npm run e2e:serve` (deixa o ambiente de pé e imprime o código de convite lido do
e-mail) e abra o app com `EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8766`.
