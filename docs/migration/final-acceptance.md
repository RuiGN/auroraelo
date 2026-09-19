# Mindcare — Aceite final reaberto

Retificação: 09/09/2026. Branch `codex/duralux-migration`, base de revisão `fe3e5e9`
mais alterações locais não comitadas. As declarações anteriores de conclusão
integral foram invalidadas por lacunas de tradução comprovadas.

## Resultado atual

- **Inglês e espanhol disponíveis na homologação local** em
  http://localhost:8000/accounts/login/, pelo seletor de globo, junto a pt-br.
- **Produção permanece somente pt-br**; disponibilização local de catálogos em
  elaboração não equivale a aceite editorial, clínico, jurídico ou comercial.
- **1.432 testes aprovados**, 0 falhas/erros/skips, PostgreSQL isolado, 220,21 s.
- **Cobertura 86,10134116646698%**; gate de 90% reprovado (exit 2), não reduzido.
- Ruff check e format aprovados (491 arquivos); mypy sem erros (591 arquivos);
  `manage.py check` limpo e `makemigrations --check --dry-run` sem alterações.
- **18 cenários reais de navegador** aprovados no login local: pt-br/en/es,
  320/390/1440 px, claro/escuro, POST com CSRF, cookie, retorno, foco, overflow e
  catálogo JavaScript. Não abrangem todos os perfis, domínios ou revisão visual manual.
- Gate de catálogos aprovado apenas no escopo declarado: 100 templates e 26
  arquivos Python, 1.250 chaves marcadas, incluindo formas plurais. Não verifica
  mensagens não marcadas, todo o Python nem todos os consumidores JavaScript.

## Lacunas que bloqueiam o aceite integral

`i18n-recheck-audit.md` registra arquivos/linhas e contraexemplos: campos da agenda,
metas e financeiro; textos de analytics e CMS; labels de choices; datas e parsing
dos formulários reais; notificações de conteúdo; cobertura incompleta do gate.

S14.05–S14.12 e C11 foram reabertos, junto às dependências de homologação final.
O inventário de 100 templates não comprova que seus contextos Python estejam
traduzidos. As entregas funcionais anteriores são preservadas, não reimportadas.

## Artefato local

- Docker Compose: PostgreSQL, Redis e web saudáveis; somente o web foi reconstruído
  e recriado nesta correção, preservando volumes e dados existentes.
- Nova imagem exclui `.env`, `.venv`, `.git`, dados privados e artefatos locais via
  `.dockerignore`. Imagens/cache antigos não foram apagados; não redistribuí-los.
- Nenhum commit, push, deploy em produção, reset de senha ou transferência
  operacional realizado nesta correção.

Evidências: `evidence/i18n-runtime-recheck.md`, `evidence/recheck-pytest.xml`,
`evidence/recheck-coverage.json`, `evidence/recheck-coverage-gate.log`,
`evidence/recheck-i18n-catalogs.json`, `evidence/runtime-languages/results.json`.
