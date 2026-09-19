# Revisão limitada — disponibilidade local de idiomas

## Parecer

**Sem findings acionáveis identificados no escopo desta correção.** A mudança atende ao contrato de disponibilizar `pt-br`, `en` e `es` em development, preservando apenas `pt-br` em base/produção. Parecer favorável à correção local, não à entrega integral das traduções nem à publicação em produção.

## Escopo e método

Revisão estática de `/tmp/mindcare-i18n-review.diff`, `tests/test_runtime_language_publication.py`, `scripts/verify-runtime-languages.cjs` e `.dockerignore`, com leitura dos pontos de integração e dos artefatos de evidência existentes. Nenhum teste, navegador, build, banco de dados ou implantação foi executado nesta revisão; nenhum `.env` foi lido. A única escrita foi este relatório. Não houve edição de código, commit ou push.

Arquivos Python inspecionados: `config/settings/development.py`; `config/settings/production.py`; trecho de idiomas de `config/settings/base.py:192-201`; `tests/test_runtime_language_publication.py`; `tests/test_language_preferences.py:1-290`; `accounts/language_preferences.py`; `accounts/context_processors.py`. Também foram consultados `Dockerfile`, `docker-compose.yml`, `compose.test.yml`, `pyproject.toml`, o trecho do gate em `.github/workflows/quality.yml` e a inicialização de tema em `static/duralux/js/product-shell.js:19-23`.

## Conformidade da correção

- **Separação dos ambientes:** `config/settings/development.py:62-67` define explicitamente os três idiomas e deixa de importar `LANGUAGES` de base. `config/settings/base.py:196-198` mantém somente português; `config/settings/production.py:19` continua importando essa lista restrita. Não há ampliação da publicação em produção.
- **Causa do seletor ausente:** `accounts/language_preferences.py:11-13` e `accounts/context_processors.py:23-37` derivam as opções de `settings.LANGUAGES`. A correção altera essa origem, sem modificar persistência, permissões ou catálogos.
- **Regressão representativa:** `tests/test_runtime_language_publication.py:21-87` inicializa Django em subprocesso com `config.settings.development`, sem sobrescrever a lista de idiomas. Verifica opções, negociação HTTP, idioma HTML, título traduzido, troca por POST, cookie, recarga, preservação de `next`, rejeição de idioma inválido e CSRF. O ambiente explícito usa valores sintéticos e não herda credenciais do processo pai. O contrato distinto de produção permanece em `tests/test_language_preferences.py:66-96`.
- **Verificação de navegador delimitada:** `scripts/verify-runtime-languages.cjs:5-6,22-24,26-82` restringe a URL inicial a loopback, usa contextos novos por cenário, realiza a troca pelo seletor real e registra resultados incrementais e erros. A matriz cobre o login anônimo e o endpoint de catálogo JavaScript; não demonstra consumo dinâmico desse catálogo nem aceitação visual/editorial de todos os domínios. O tema solicitado corresponde à preferência de sistema usada pela inicialização atual da aplicação.
- **Contexto de build:** `.dockerignore:2-5,20-27` exclui arquivos de ambiente, repositório, ambiente virtual, dados locais e evidências do `COPY . /app` em `Dockerfile:22`. A injeção de configuração por `docker-compose.yml:11-16` permanece separada do contexto de build. A ausência de `.env`/`.venv` na nova imagem foi informada pelo agente executor, não reinspecionada aqui; a exclusão não remove esses arquivos de imagens anteriores.

## Evidência existente conferida, sem reexecução

- `docs/migration/evidence/recheck-runtime-red.log` registra a falha da lista observada `['pt-br']` contra `['pt-br', 'en', 'es']`; `recheck-runtime-green.log` registra **3 testes aprovados**.
- A leitura e agregação de `docs/migration/evidence/recheck-pytest.xml` confirmou **1.432 casos**, sem falhas, erros ou skips, incluindo os três casos novos. Isso descreve a execução registrada, não uma nova execução desta revisão.
- A agregação de `docs/migration/evidence/runtime-languages/results.json` confirmou **18 combinações únicas**, sem combinações ausentes ou inesperadas e com `errors: []`: `pt-br/en/es × 320/390/1440 × light/dark`. As flags registradas são coerentes com as asserções do script. As capturas não foram avaliadas visualmente nesta revisão.
- `docs/migration/evidence/recheck-coverage.json` registra **86,101%**. `recheck-coverage-gate.log` registra reprovação no mínimo de **90%**, e `.github/workflows/quality.yml:76` mantém `--cov-fail-under=90`. Portanto, a suíte registrada sem falhas **não equivale a gate de qualidade aprovado**.

## Pendências separadas — não são regressões deste fix

As lacunas de tradução, extração, formulários, avisos, notificações, apresentação de datas/valores, consumidores JavaScript e revisão humana permanecem descritas em `docs/migration/i18n-recheck-audit.md`. Elas não impedem a prévia local solicitada, mas impedem declarar a interface integralmente traduzida ou liberar EN/ES em produção.

A reconciliação de S14.05–S14.12 e C11 no PRD cabe ao agente responsável; este relatório não altera nem certifica essa reconciliação. A reprovação de cobertura permanece uma pendência independente, sem redução do gate. Este parecer se limita ao defeito de disponibilidade local relacionado a S14.03 e não autoriza commit, push ou implantação.
