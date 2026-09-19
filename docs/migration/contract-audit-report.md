# Relatório da auditoria contratual

## Escopo executado

Auditoria documental limitada às tarefas S00.03, S00.04 e S00.06 do
`DURALUX.prd`. Foram lidos o PRD, `execution-status.md`, `routes-matrix.md`,
`templates-matrix.md` e `backend-matrix.md`; inspecionados decorators de views,
middleware implícito, políticas, services e seletores transitivos dos fluxos
críticos; e reconciliados nomes de testes com o JUnit já existente.

Arquivos produzidos:

- `docs/migration/contract-audit.md`: conclusão, exceções por rota, contratos de
  contexto, jornadas críticas e lacunas.
- `docs/migration/contract-audit-report.md`: este registro de escopo, evidência,
  limitações e proposta de atualização do PRD.

Nenhum arquivo de runtime, matriz, PRD ou checkout de origem foi alterado. Nenhum
teste foi executado e nenhum commit foi criado.

## Evidência usada

- inventário de 182 rotas em `docs/migration/routes-matrix.md` e snapshot
  `docs/migration/evidence/runtime-routes.json`;
- inventário de 97 templates em `docs/migration/templates-matrix.md`;
- contratos de domínio registrados em `docs/migration/backend-matrix.md`;
- resultado anterior em
  `docs/migration/evidence/destination-final-pytest.xml`: 1.253 testes, zero
  failures, zero errors, executado em PostgreSQL;
- código atual do destino em views, middlewares, context processors, policies,
  selectors e services;
- nomes de casos presentes no JUnit, citados individualmente em
  `contract-audit.md`.

## Limitações

- A revisão aprofundou as jornadas e exceções de maior risco; não refez
  manualmente o grafo completo de cada um dos 147 callbacks próprios.
- Não houve nova execução de pytest, cobertura, browser ou banco. O resultado de
  1.253 testes é evidência herdada e identificada pela data do JUnit, não um teste
  desta tarefa.
- Os callbacks gerados pelo Django Admin permaneceram sob contrato do framework;
  permissões por modelo/objeto e métodos não foram enumerados individualmente.
- Compilação de template não equivale a renderização de todos os contextos e
  estados.
- Nenhuma aceitação visual foi realizada ou inferida.

## Proposta de atualização do PRD

Não marcar S00.03, S00.04 ou S00.06 como concluídas ainda. Acrescentar, sob cada
tarefa, uma nota de progresso apontando para `docs/migration/contract-audit.md`:

- **S00.03:** “Inventário de 182 rotas reconciliado e exceções críticas auditadas.
  Pendente: contrato explícito dos callbacks sem method decorator, matriz do
  Django Admin e prova 1:1 rota/método/perfil/resposta.”
- **S00.04:** “Inventário de 97 templates, includes literais, forms, context
  processors e `layout_template` reconciliado. Pendente: renderização dos
  contextos e estados por rota, inclusive erro, vazio, forbidden e not-found.”
- **S00.06:** “Jornadas funcionais dos quatro perfis ligadas a testes existentes.
  Pendente: aceite visual e acessível em navegador por perfil e estados não
  felizes.”

Para o aceite futuro, criar uma evidência gerada que tenha uma linha por callback
próprio e registre métodos aceitos, perfil, gate transitivo, status/redirect,
template e teste correspondente. Separadamente, registrar uma matriz de
renderização dos 97 templates e a evidência visual por perfil. Só então reavaliar
as caixas do PRD.

## Auto-revisão

O relatório distingue inventário, evidência funcional anterior e trabalho ainda
pendente; não transforma o passe da suíte em cobertura de rota 1:1 nem em aceite
visual. As afirmações de autorização foram limitadas aos caminhos inspecionados e
as lacunas foram mantidas explícitas.
