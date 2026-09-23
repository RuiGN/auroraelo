# Master responsivo e administração separada

Escopo local no checkout Git `auroraelo`, branch `gemini`. Sem commit, push ou deploy.
Referência visual exclusiva: `design_system/`.

## Rotas e responsabilidades

- `/master/login/`: autenticação existente; espaçamento de ícones corrigido por
  seletor CSS que prevalece sobre as utilitárias Tailwind. CSS recompilado e
  backdrop recortado sem bloquear a rolagem vertical. O login respeita `next`
  local validado pelo helper existente; destinos externos são rejeitados.
- `/master/`: indicadores de tenants, tenants recentes e navegação para cadastro,
  listagem e detalhe de clínicas. Sem gestão de identidades ou gráficos de usuários.
- `/administracao/`: administração global de usuários/equipe para staff ativo.
  Filtros de clínica, papel e situação; convites, vínculos e revogação usam os
  serviços existentes, sem criação de senha administrativa ou concessão de staff.
- `/administracao/convites/`: convidar ou vincular identidade existente.
- `/administracao/vinculos/<uuid>/`: editar papel, unidade, vigência e situação.
- `/administracao/convites/<uuid>/revogar/`: revogação via POST com CSRF.
- URLs antigas `/master/users/...` preservam apenas redirecionamentos GET/HEAD.
  POST legado responde 405 e não executa mutações. Links/formulários novos apontam
  ao namespace `administration`.
- A gestão restrita à clínica continua nas rotas de equipe de `accounts`, sem
  ampliar privilégios de administradores de clínica para o painel global.

## Implementação visual

Shell compartilhado com navegação própria por área, menu móvel com Escape e foco,
KPIs empilháveis e tabelas com scroll local. O wrapper da tabela tem posição
relativa para conter o rótulo absoluto de acessibilidade e não expandir a página.
Controles com nomes de clínicas longos respeitam a largura disponível.

Fontes CSS: `design_system/src/master.css` e `master-login.css`, importadas por
`aurora.css`. Artefato compilado em `static/design_system/css/aurora.css`;
JavaScript próprio em `static/master_panel/js/panel.js`. Manifesto de hashes
atualizado. Nenhuma migration ou alteração de modelo.

Novas strings estáticas incluídas nos catálogos pt_BR/en/es; escopo cumulativo
ampliado. Traduções técnicas de interface, não revisão de terminologia clínica.

## Evidência local

Artefatos desta execução em
`/Users/rgnsystems/.hermes/cache/scratch/master-ui/` (scratch, não arquivo durável).

- Baseline focado antes das mudanças: 40 testes aprovados.
- Pytest completo final, settings `config.settings.test`, SQLite, migrations
  normais: 2.710 aprovados, 29 ignorados, zero falhas/erros. Os skips exigem
  PostgreSQL real (locks/concorrência) ou Redis descartável explicitamente configurado.
- Recorte de rotas, autorização, tenants, equipe e templates: 63 aprovados.
- Recorte final de design system, templates e catálogos: 66 aprovados.
- Após a revisão, adicionados 16 casos de autorização/sessão; execução isolada
  de `tests/test_administration_routes.py` com migrations normais: 34 aprovados.
  Não houve alteração de runtime após a suíte completa, apenas esses testes.
- `npm run test -- --reporter=line`: 37 aprovados, incluindo 15 casos de geometria
  (login, Master e administração × 320/390/768/1024/1440 px).
- As provas de geometria usam templates reais com dados sintéticos e assets locais,
  CSP sem scripts inline, checagem de console/recursos, padding, overflow e menu.
  Não são sessões reais de produção; persistência/autorização são cobertas por pytest.
- `npm --prefix design_system run build`: aprovado.
- Gate cumulativo de catálogos: aprovado, 1.446 chaves requeridas.
- `manage.py check`, `makemigrations --check --dry-run`, `git diff --check`: aprovados.
- Ruff dos Python alterados: aprovado. Ruff global mantém 120 diagnósticos e
  format mantém 19 arquivos fora do padrão, iguais ao HEAD extraído para scratch.
- Mypy global mantém 754 diagnósticos, iguais ao HEAD com o mesmo ambiente e
  configuração. Comparação por caminho/mensagem/código, normalizando linhas;
  nenhum novo diagnóstico. Esses gates globais continuam reprovados por dívida
  preexistente, não foram enfraquecidos.

Limites: não houve homologação PostgreSQL/Redis nesta entrega, acesso a dados reais,
validação visual humana ou verificação/publicação da nova versão em produção.

## Revisão independente

Revisão somente leitura de rotas, isenção de tenant, autenticação, sessão, CSRF
e redirects: nenhum achado crítico, alto ou médio. O revisor identificou lacunas
informativas de cobertura; foram acrescentadas e executadas provas específicas:

- `clinic_admin` ativo sem staff é recusado diretamente pelas quatro views via
  RequestFactory, sem depender de middleware tenant.
- Com `ACCOUNT_SESSION_ALLOW_UNKNOWN=False`, sessão desconhecida, revogada ou
  expirada é recusada em todos os endpoints. Controle positivo usa login real
  sintético e confirma acesso antes da revogação/expiração.
- A cobertura anterior de POST sem CSRF e de redirects externos permanece.

Ruff/mypy dos novos testes não introduziram diagnósticos. Nenhuma proteção foi
relaxada para obter esses resultados. O parecer não equivale a pentest ou
homologação de produção.
