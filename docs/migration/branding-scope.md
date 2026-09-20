# Aurora Elo — escopo de marca e exceções

## Política atual e limites

**Aurora Elo** é o nome público; `auroraelo` é a convenção para identificadores
novos. A marca anterior, **Mindcare**, não deve aparecer como identidade ativa
na aplicação, nos exemplos novos ou nos documentos operacionais atuais.
Uma referência negativa em teste ou uma evidência histórica não é marca ativa.

Esta entrega cobre README, glossário operacional, runbook de instalação,
manifestos de assets, testes de configuração/fundação estática e os dois SVGs
de autenticação. Não altera templates, código clínico, configurações, mobile,
vendors, migrations, dados ou infraestrutura. A branch confirmada foi `hermes`;
o checkout tinha alterações de outros responsáveis, que foram preservadas.

Os arquivos `static/duralux/images/auth/aurora-elo-peace-{light,dark}.svg` foram
renomeados sem modificar seus bytes. O módulo de configuração passou a
`tests/test_aurora_configuration.py`. O manifesto operacional mantém SHA-256 de
todos os arquivos do namespace, e os testes continuam exigindo inventário exato,
resolução de URLs locais, coleta com manifest storage, vetor no favicon e
preservação da identidade configurada por clínica. Foram adicionadas guardas
case-insensitive contra a marca anterior nos templates e no favicon.

## Instalações novas não são migrações de produção

O README foi confrontado com `compose.test.yml`: projeto `auroraelo-test`,
PostgreSQL 17, banco/usuário `auroraelo`, credencial exclusivamente sintética e
porta local 55439. `docker-compose.yml` usa a imagem `auroraelo:latest`,
PostgreSQL 17 e defaults de banco/usuário para instalações novas. Nenhum serviço
foi iniciado nesta tarefa; essas são constatações estáticas dos manifests.

Não se pode inferir desses nomes que bancos, usuários, volumes ou a VPS foram
renomeados. Preserve os identificadores e strings de conexão já implantados até
uma migração separada, com autorização, backup, ensaio e rollback. Trocar o nome
do projeto Compose pode selecionar outros volumes. Nunca apagar volumes para
adequar uma marca. Não foram lidos `.env`, bancos, uploads ou dados clínicos.

## Exceções justificadas e história preservada

| Categoria | Arquivos/identificadores | Motivo e tratamento |
|---|---|---|
| Histórico de migração | `docs/migration/baseline.md`, `decisions.md`, `execution-status.md`, `final-acceptance.md` | Relatam revisões, decisões ou ambientes anteriores. Nomes, resultados, datas e comandos executados não foram reescritos como se pertencessem à release atual. |
| Inventários/revisões históricos | `docs/migration/backend-matrix.md`, `routes-matrix.md`, `templates-matrix.md`, `i18n-matrix.md`, `contract-audit.md`, `foundation-review.md` | Paridade, inventários e revisão da migração original, não prova de aceitação atual. |
| Relatórios de execução | `docs/migration/auth-template-report.md`, `coverage-report.md`, `identity-boundary-report.md`, `language-backend-report.md`, `i18n-local-fix-review.md`, `docs/duralux/input-presentation-verification.md` | Bancos sintéticos, comandos e artefatos que identificam execuções passadas; substituí-los falsificaria proveniência. Não copiar como configuração de uma instalação nova. |
| Histórico importado | PRDs anteriores, `docs/**/evidence/**`, snapshots e migrations | Excluídos da busca operacional e integralmente preservados. Não há afirmação de ausência da marca nessas áreas. |
| Ponte para documento atual | `docs/duralux/runtime-asset-manifest.md` | Só o apontador inicial foi atualizado; corpo do baseline, hashes históricos e avisos de licença permanecem intactos. |
| Diretório histórico | `.hermes.md:5` | Identifica outro checkout, não a marca do produto atual; arquivo fora desta tarefa. |
| Namespace de cache | `config/settings/base.py:216`, default `mindcare` | Identificador de compatibilidade fora do escopo. Não mudar silenciosamente caches existentes; qualquer transição exige decisão explícita do principal. |
| Guarda de banco isolado | `scripts/verify_mfa_removal.py:4,27`, `mindcare_mfa_verification` | Nome literal protege uma verificação destrutiva contra bancos não isolados. Não remover/relaxar a guarda; eventual mudança exige revisão coordenada do script e de seu procedimento. |
| Variáveis dos probes | `scripts/provision_test_session.py`, `verify-language-selector-contrast.cjs`, `verify-runtime-languages.cjs`, família `MINDCARE_*` | Contrato de ferramentas fora do escopo. Preferir nomes novos com aliases legados explicitamente documentados, se ainda houver consumidores. Não imprimir senhas para demonstrar a transição. |
| Guardas negativas | `tests/test_duralux_static_foundation.py` | O nome anterior existe somente como termo proibido. Remover essa referência enfraqueceria a prevenção de regressões. |
| Este registro | `docs/migration/branding-scope.md` | Citações literais identificam exceções; não são exemplos de marca ativa. |

## Inventário textual e contagens

Inventário Python case-insensitive (`re.I`), com arquivos rastreados e não
rastreados não ignorados obtidos por `git ls-files`, deduplicados, e filtro
adicional `git check-ignore --no-index`. Antes de ler, exclui vendors, pacote
fonte Duralux, dependências, evidências, snapshots, PRDs, migrations, `.env`,
chaves, bancos, uploads e demais diretórios privados. Arquivos binários e links
simbólicos não são tratados como texto. As contagens são de ocorrências, não
linhas; aliases/guardas/história têm categorias próprias. Não varre Git history.

O inventário inicial, antes das alterações desta tarefa, registrou **118
ocorrências em 47 arquivos**. A leitura final, incluindo este registro,
registrou **94 ocorrências em 41 arquivos**:

| Categoria | Ocorrências |
|---|---:|
| Identidade operacional dentro do escopo entregue | 0 |
| Guardas negativas dos testes de branding | 2 |
| Histórico preservado em documentos textuais e contexto | 38 |
| Compatibilidade fora do escopo (cache/guarda MFA) | 3 |
| Referências operacionais fora do escopo, pendentes dos responsáveis | 47 |
| Citações justificadas neste registro | 4 |

Este documento é contado separadamente como registro de exceções. As contagens
são um retrato local durante trabalho concorrente, não um gate estável nem uma
certificação de ausência global. Os arquivos JSON de inventário e o script
reproduzível ficaram no scratch local do agente, não nas evidências históricas:
`/Users/rgnsystems/.hermes/cache/scratch/aurora-branding-{before,after}.json` e
`aurora-branding-inventory.py`.

## Integração fora do escopo — ações do principal/UI

| Local observado | Ajuste necessário |
|---|---|
| `static/duralux/css/auth.css:6,15` | Resolvido na integração: URLs apontam aos SVGs novos, hash recalculado e coleta com manifest storage passou. |
| `static/duralux/images/favicon.svg:1` | Resolvido na integração: reutilizado o vetor Aurora Elo de `static/images/favicon.svg`, com título/rótulo acessível e hash recalculado. Não equivale a aprovação visual. |
| `static/duralux/js/language-selector.js:3,25`, `form-behaviors.js:96` | Coordenar prefixo de chave/evento entre produtor e consumidor, usando `auroraelo`; avaliar necessidade de compatibilidade de storage. Atualizar os hashes. |
| `tests/test_workspace_foundation.py:1,60` | Resolvido pelo principal: docstring/expectativa Aurora Elo, preservando verificações de papéis, clínica e links; sete casos passaram no ciclo rápido. |
| `tests/test_duralux_wcag_and_responsive.py:71` | Corrigir referência de marca no comentário sem alterar a asserção de contraste. |
| `scripts/verify-duralux-shell.cjs:28` | Atualizar expectativa de título para Aurora Elo. |
| `scripts/provision_test_session.py:26-28` | Confrontar defaults descartáveis com o Compose atual, sem alterar conexão de instalação existente. As variáveis legadas precisam da decisão de compatibilidade acima. |
| `scripts/check_djangojs_catalogs.py:31`, `check_ui_catalogs.py:38`, `verify-input-presentation.cjs:66,69` | Atualizar prefixos dos novos artefatos temporários; não renomear evidências já produzidas. |
| `locale/{en,es,pt_BR}/LC_MESSAGES/django.po:4,8,9` e `djangojs.po:3,7,8` | Atualizar metadados da marca/equipe; recompilar `.mo` e executar gates, sem mudar mensagens clínicas. |
| `package-lock.json:2` | Reconciliar o nome do pacote raiz com seu manifesto e com Aurora Elo. |
| `design_system_duralux/` | Excluído pelo usuário da referência e do aceite da nova versão. Não recuperar nem exigir o pacote. O teste atual verifica sanitização do runtime e preserva inventário/hashes/URLs/coleta, sem depender dessa fonte. |

## Validação realmente executada

- Baseline dos dois módulos originais: **14 passaram, 2 falharam**. Falhas:
  fonte Duralux ausente e tabela SHA-256 desatualizada.
- Ciclo vermelho antes do renome dos SVGs: inventário exato rejeitou os nomes
  antigos; novo contrato de marca rejeitou o favicon anterior.
- Após renomes, atualização do manifesto e testes: **13 passaram, 4 falharam**,
  incluindo o novo teste que compara credenciais sintéticas do README/Compose.
  As falhas restantes são favicon anterior, fonte ausente e duas verificações
  da URL antiga em `auth.css` (URLs locais e `collectstatic`).
- O teste de hashes e o inventário exato passaram. A tabela foi recalculada
  por SHA-256; hashes previamente divergentes de `auth.css` e Feather CSS foram
  reconciliados com os bytes existentes, sem editar esses ativos.
- Ruff check/format dos dois módulos e `git diff --check` (incluindo índice)
  passaram. Nenhum teste foi removido, ignorado ou relaxado.

Comando focado: `DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m
pytest tests/test_aurora_configuration.py tests/test_duralux_static_foundation.py
--no-cov -q`. A execução usou TMPDIR explícito no scratch local e JUnit
`aurora-branding-focused.xml` no mesmo diretório. Não houve validação visual,
execução PostgreSQL, commit, push ou deploy. Reexecutar os testes e recalcular
hashes após os ajustes de UI/principal antes de aceitar a integração.

### Verificação posterior da integração pelo principal

As quatro falhas acima foram reproduzidas antes dos ajustes. Após a correção de
CSS/favicon, atualização dos hashes, expectativa Aurora Elo no workspace e
recuperação da fonte original do tema, os três módulos de configuração, assets
e workspace passaram: **24 testes, 0 falhas**, com `--nomigrations --no-cov`.
A coleta/post-processamento real e a igualdade de SHA-256 fazem parte desse
conjunto. Os sete avisos apontam ausência do diretório global `staticfiles/`;
o teste de coleta usa seu próprio diretório temporário.

Evidência local: `/Users/rgnsystems/.hermes/cache/scratch/aurora-branding-integration.xml`.
Esse ciclo não valida migrations, aparência no navegador, produção, os demais
testes ou as referências operacionais restantes. A licença de redistribuição
Duralux continua bloqueando a aprovação comercial.

### Correção de escopo posterior

O usuário determinou não considerar `design_system_duralux/`. A tentativa de
reintroduzir essa referência foi abandonada, sua documentação nova foi retirada
e o arquivo restaurado não está presente. A execução em andamento sob o critério
anterior foi cancelada. A referência visual é exclusivamente `design_system/`,
registrada também em `.hermes.md` e `novaversao.prd`.

Os resultados anteriores ficam como registro de execução, não como exigência de
recuperar o pacote novamente. O teste de derivação pela fonte foi substituído
por sanitização do CSS ativo; todos os controles de inventário, hashes e coleta
continuam. A exclusão do pacote de referência não dispensa as licenças de
dependências que de fato continuarem no runtime.
