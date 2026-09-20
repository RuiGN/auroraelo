# Validação local desta integração

- TDD vertical: primeiro ciclo 4 falhas de CSS/runtime → 4 aprovados após build.
  Segundo ciclo 2 falhas de login demo → 6 aprovados, com migrações normais.
  Terceiro ciclo idioma/estado honesto/menu e quarto ciclo entradas sem mockups:
  falhas observadas antes das mudanças e verificações posteriores aprovadas.
- `npm --prefix design_system ci --ignore-scripts --no-audit --no-fund` e
  `npm --prefix design_system run build`: executados com sucesso. Aviso de
  Browserslist/caniuse-lite desatualizado; não houve atualização automática.
- `npm --prefix design_system test`: **2 testes Node aprovados**, DOM sintético,
  cobrindo menu móvel/Escape/foco, aria-expanded e mudança de layout/viewport.
- `DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest
  tests/test_aurora_design_system.py tests/test_layouts.py
  tests/test_duralux_wcag_and_responsive.py -q --no-cov --nomigrations --tb=short`:
  **46 aprovados**. Avisos: diretório staticfiles ainda não coletado.
- Ruff check/format do novo teste Python aprovados. `node --check` e
  `git diff --check` também passaram.
- Suíte completa com migrações interrompida por timeout de ferramenta, antes de
  terminar, sem JUnit final. Log parcial:
  `/Users/rgnsystems/.hermes/cache/scratch/aurora-design-final.log`.
  Tentativas finais focadas com migrações normais também excederam 300/240 s;
  não se declara aprovação da suíte completa ou migrações finais.
- Evidência renderizada Django: shell, login real com CSRF/campos, idioma ativo
  pt-br/en/es e seletor canônico. Não houve inspeção visual no browser, auditoria
  WCAG completa, build mobile ou verificação em produção.

Pendências do integrador: catálogos pt_BR/en/es, escopo i18n, manifesto de assets
(`runtime-assets.json` contém hashes locais), validação CSP dos templates filhos,
reexecução integrada das migrações/suíte completa e auditoria das páginas clínicas
legadas ainda com mockups. Nenhum template foi apagado.

## Verificação posterior do integrador

O build/npm e os 46 testes Django foram reexecutados com sucesso. O Dockerfile
agora recompila o CSS em estágio separado: build `ui-build` executado, hash igual
ao do host, sem alegar aprovação da imagem Python final. O novo teste de contrato
do Dockerfile passou após um ciclo vermelho/verde.

Chrome isolado exercitou snapshots Django sintéticos de login, workspace e portal
nas larguras 390/1440: seis casos, sem overflow horizontal nem erros capturados;
abertura/Escape/ARIA/foco dos menus móveis passaram. O ensaio foi em pt-BR e não
comprova autenticação/persistência ou aprovação estética das capturas. Detalhes e
artefatos em `docs/migration/aurora-ui-browser-validation.md` na raiz do repo.
