# Modelos de desenvolvimento — Aurora Elo

## Escopo

Configuração do Hermes no perfil local `default`, em
`/Users/rgnsystems/.hermes/config.yaml`, aplicada por `hermes config set`.
É uma configuração do perfil, não uma configuração isolada por repositório:
vale também para novas sessões desse perfil abertas em outros projetos.
Os outros perfis não foram modificados. Chats existentes não devem ser
considerados reconfigurados automaticamente; abra uma nova sessão para carregar
o conjunto completo e as instruções `.hermes.md`.

Não altera modelos da aplicação `ai_assistant`, credenciais, banco, infraestrutura
ou produção. Os probes enviaram apenas prompts e imagens sintéticos.

## Análise que fundamenta a escolha

O projeto declara Python 3.14 e Django 6.1 (`README.md:9`,
`requirements.txt:4`), backend modular com serviços/políticas de autorização,
UI Django/Duralux e dois clientes Expo. O app Connected declara Expo 52,
React 18.3.1, React Native 0.76.5 e TypeScript 5.3 (`mobile/connected/package.json`).
Essas são versões declaradas, não uma certificação do ambiente instalado.

O domínio de saúde mental torna isolamento entre clínicas, consentimento,
autorização e veracidade das confirmações mais importantes que economizar tokens
em toda tarefa. O principal coordena mudanças transversais; um modelo de outra
família revisa decisões críticas. Modelos auxiliares recebem trabalho delimitado.
A seleção é uma decisão operacional, não o resultado de benchmark comparativo.

## Roteamento aplicado e preservado

| Papel | Provedor | Modelo | Situação |
|---|---|---|---|
| Principal: arquitetura, implementação e integração | `openai-codex` | `gpt-6-astra` | Mantido |
| Delegação comum: testes, código e análises delimitadas | `openai-codex` | `gpt-6-astra` | Retomado após bloqueio de saldo do OpenCode Go |
| Revisão independente via `/review` | `commandcode-anthropic` | `claude-sonnet-5` | Fixado, com `anthropic_messages` |
| Visão: layouts e screenshots não sensíveis | `commandcode-anthropic` | `claude-sonnet-5` | Substitui a rota experimental DeepSeek Vision |
| Compressão de contexto | `opencode-go` | `qwen3.8-max` | Mantido |
| Busca de skills | `opencode-go` | `glm-5.3-flash` | Substitui Sonnet neste trabalho auxiliar |
| Títulos e reescrita de busca de memória | `opencode-go` | `glm-5.3-flash` | Mantido |
| Roteamento MCP | `opencode-go` | `deepseek-v4.1-flash` | Mantido |
| Especificação e decomposição de tarefas Kanban | `opencode-go` | `glm-5.3` | Substitui Flash para planejamento |
| Julgamento de objetivos | `commandcode-anthropic` | `claude-sonnet-5` | Mantido |

A revisão pós-turno (`auxiliary.background_review`) continua em Sonnet e serve à
manutenção de memória/skills; não substitui revisão de código. Aprovações,
limites de concorrência e demais controles de segurança não foram alterados.

### Disponibilidade e contingência

A delegação visual em `glm-5.3` foi interrompida por HTTP 402
(`Insufficient account funds`). A delegação comum foi então transferida para
`openai-codex / gpt-6-astra` por `hermes config set`; a releitura confirmou os dois
valores. Um novo probe sintético respondeu `OK`, e o log da sessão
`20260920_132634_db280d` confirmou modelo e provedor solicitados.
A tarefa visual foi redistribuída, mas isso não comprova a entrega da interface.

Após o bloqueio, uma credencial fornecida pelo usuário foi cadastrada no pool
local do Hermes para `opencode-go`, com prioridade zero e releitura verificada,
sem gravá-la no repositório ou na configuração da aplicação. O probe CLI da
sessão `20260920_134156_739d59` respondeu `OK`; os logs confirmaram
`provider=opencode-go`, `model=glm-5.3` e nenhuma falha/fallback nessa sessão.
A delegação permanece em Astra para não mudar o trabalho já redistribuído.

Os demais slots, aliases e fallbacks OpenCode Go abaixo continuam configurados.
O novo probe confirma GLM-5.3, não revalida todos os demais modelos. O alias
`aurora-worker` continua apontando para GLM-5.3. Não foram comprados créditos nem
alteradas credenciais ou modelos da aplicação comercial.

Cadeia de fallback principal preservada:

1. `opencode-go / glm-5.3`
2. `commandcode / deepseek/deepseek-v4-pro`
3. `openai-codex / gpt-5.6-sol`
4. `opencode-go / kimi-k3`

Claude usa o transporte Anthropic do CommandCode, separado da cadeia principal.
Não foram adicionados provedores, assinaturas ou credenciais. Modelos não
testados não são declarados disponíveis apenas por aparecerem em catálogo.

## Atalhos adicionados

- `/model aurora`: GPT-6 Astra.
- `/model aurora-review`: Claude Sonnet 5.
- `/model aurora-worker`: GLM-5.3.
- `/model aurora-fast`: GLM-5.3 Flash.
- `/model aurora-context`: Qwen 3.8 Max.
- `/model aurora-alt`: DeepSeek V4 Pro.

Esses aliases trocam o modelo da conversa; não são um roteador automático por
especialidade. Para revisão independente, prefira `/review`. Para trabalho
paralelo, delimite os arquivos e não deixe implementador e revisor alterarem o
mesmo trecho simultaneamente. Evite trocar o modelo principal no meio de um
contexto longo sem necessidade, pois isso perde o cache do prompt.

## Verificação realmente executada

- Chamadas CLI reais para o principal, os quatro modelos de fallback, Sonnet,
  GLM Flash, Qwen e DeepSeek Flash. Logs por ID de sessão confirmaram a rota
  solicitada; o sucesso não foi inferido apenas da resposta final.
- Chamadas de ferramenta sintética em GLM-5.3 e Sonnet, com validação dos
  argumentos JSON. Nenhuma ferramenta sintética foi executada.
- Sonnet reconheceu a cor de uma imagem PNG gerada para o teste.
- Após gravar a configuração, chamadas auxiliares sem overrides de provedor/modelo
  validaram os slots de compressão, visão, skills, títulos, MCP, especificação,
  decomposição e julgamento de objetivos. Todos retornaram pela rota configurada.
- O teste sintético de compressão preservou identificadores e `consent=False`.
- As chaves alteradas foram relidas pelo carregador do Hermes e conferidas.

Os testes comprovam conectividade, roteamento e capacidades mínimas; não provam
superioridade entre modelos, qualidade clínica, suporte a todo contexto possível
ou funcionamento de todas as transições de fallback sob falha induzida.
A suíte Django, builds mobile e produção não foram executados nesta configuração.

## Pendências encontradas na análise estática

Estas observações não foram corrigidas nesta tarefa e não representam um pentest
ou confirmação do comportamento de um deploy remoto.

1. **Autorização e isolamento em psiquiatria.** `psychiatry/api.py:75-106` consulta
   pacientes com `objects.all()` sem filtro de clínica; `psychiatry/api.py:144-181`
   grava anamnese com `csrf_exempt` e sem autorização local. As rotas são ligadas
   diretamente em `psychiatry/urls.py:24-30`, montadas em `config/urls.py:39`.
   `clinics/middleware.py:41-42` e `accounts/middleware.py:27-30` deixam requisições
   anônimas prosseguir. Priorizar testes negativos HTTP, autenticação e escopo
   de clínica antes de tratar essas APIs como seguras.
2. **Confirmações sem operação correspondente.** `psychiatry/api.py:245-290`
   responde que adesão foi sincronizada e que o plantão foi notificado sem
   implementar essas operações. O app mostra a confirmação em
   `mobile/connected/src/screens/HomeScreen.tsx:28-40`. Não usar essas respostas
   como evidência de persistência, atendimento ou entrega de mensagem.
3. **Mobile incompleto.** Há comentários HTML inválidos em TSX, por exemplo
   `mobile/connected/src/screens/HomeScreen.tsx:60`. O manifest oferece scripts
   de inicialização Expo, não gates de build, teste ou typecheck. Verificar
   entrypoint, autenticação, integração e compilação antes da aceitação.
4. **Cobertura desigual.** `psychiatry` não está nas listas explícitas de
   cobertura e mypy em `pyproject.toml`. A análise não localizou o workflow
   `.github/workflows/quality.yml` exigido por testes históricos. Um eventual
   resultado verde da suíte atual não certifica todos os módulos novos.

## Gates para futuras mudanças

Partir dos comandos do checkout, não dos comandos de outro projeto histórico:

- `DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest`
- `.venv/bin/python -m ruff check .`
- `.venv/bin/python -m ruff format --check .`
- `.venv/bin/python -m mypy`
- `git diff --check`

Verificar primeiro se `.venv` e dependências estão disponíveis. Para testes
específicos de banco, seguir o fluxo descartável do `README.md:32-45`;
`compose.test.yml:5` declara PostgreSQL 17 neste checkout, não PostgreSQL 18.
Não iniciar serviços de produção nem reutilizar bancos reais.
Mudanças de UI também exigem os verificadores de catálogos do projeto e
validação renderizada. Os apps mobile precisam de gates próprios verificáveis.

## Referências do Hermes

- https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models
- https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation

A documentação explica o contrato de configuração; a implementação instalada e
as chamadas reais confirmam os campos e transportes utilizados neste ambiente.
