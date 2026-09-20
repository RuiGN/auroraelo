# Catálogos das novas UIs Aurora Elo

## Escopo e limites

Referência exclusiva: `design_system/INTEGRATION.md` e
`design_system/ui-strings.json`. Integração técnica local, com dados sintéticos;
**não é revisão humana/clínica, aceite de publicação nem autorização de IA**.
Nenhum relato foi enviado a tradutores/APIs. Não foram alterados templates,
settings, backend, JavaScript, rotas, mobile ou outros testes nesta tarefa.

Os catálogos mantêm os avisos de IA indisponível, avatar que não representa um
profissional de saúde e ausência de monitoramento contínuo. A linguagem aborda
álcool/outras substâncias, jogos de azar e jogos digitais sem atribuir diagnóstico
ou estigma. As traduções continuam sendo rascunhos técnicos. SAMU **192** e CVV
**188** permanecem explicitamente relacionados ao **Brasil**, nos três idiomas;
outros países são orientados a procurar o serviço local de emergência. Nenhum
número é inferido do idioma ou trocado automaticamente por localização presumida.

## Inventário da etapa inicial (151 arquivos)

O resultado mais recente, após sanitização de outras nove telas de psiquiatria,
está em **Delta das nove telas sanitizadas**, abaixo. As contagens e execuções
anteriores são preservadas como histórico; não descrevem o gate atual.

Contagens calculadas por Python/PO parser e confirmadas por GNU gettext, não por
busca textual aproximada:

| Recorte | Resultado |
| --- | --- |
| `ui-strings.json` | 9 templates, 90 msgids únicos |
| Extração Django dos mesmos templates | 93 mensagens, 94 chaves compiladas |
| Mensagens adicionais encontradas pela extração | 3 (abaixo) |
| Plural/contexto nas novas superfícies | 1 mensagem plural, nenhum contexto |
| Escopo cumulativo | 148 → 151 arquivos; nenhum removido |
| Escopo cumulativo extraído | 1.418 mensagens, 1.422 chaves incluindo plurais; 4 mensagens plurais e 1 contextual |
| Baseline do escopo anterior | 18 chaves faltantes por idioma, oriundas dos templates novos já listados |
| Baseline das nove superfícies | 29 msgids faltantes em cada idioma |
| Acréscimos em `django.po` | 29 por idioma; nenhuma tradução/flag anterior alterada |
| Acréscimos em `djangojs.po` | 0; metadados atualizados e MO recompilados |
| Resultado cumulativo | 0 faltantes, 0 divergências de placeholders, 0 MO desatualizados |
| Auditoria dos seis PO | 0 fuzzy e 0 entradas ativas sem tradução |

As mensagens não cobertas pela lista simples foram preservadas e verificadas:

- `%(count)s revogação operacional pendente` /
  `%(count)s revogações operacionais pendentes` — header/navigation;
- `Olá, %(name)s.` — workspace;
- `Acesse seus recursos em %(clinic_name)s.` — workspace.

A extração cumulativa também preserva `pgettext("person full name", "Nome")`.
Os verificadores existentes comparam placeholders e todas as formas compiladas;
os testes novos verificam interpolação renderizada e `ngettext` real.
Identidades legítimas como “Horizontal” não são confundidas com fallback. Os
avisos de segurança em inglês/espanhol são comparados com textos traduzidos
explícitos, não apenas com `lang=en/es` ou com uma chamada gettext que poderia
retornar português.

Foram adicionados ao escopo somente:

- `psychiatry/templates/psychiatry/base_aurora.html`;
- `psychiatry/templates/psychiatry/dashboard.html`;
- `psychiatry/templates/psychiatry/login.html`.

Os seis templates restantes e suas dependências já pertenciam ao escopo
cumulativo. Todas as entradas existentes, inclusive obsoletas e seus fallbacks,
foram mantidas. Metadados `Project-Id-Version`, `Last-Translator` e
`Language-Team` agora identificam Aurora Elo e revisão pendente, sem inventar
contato ou aprovação. Os demais metadados/plurais foram preservados.

## TDD e verificação

Evidências desta execução ficam em
`/Users/rgnsystems/.hermes/cache/scratch/aurora-i18n-*` (temporárias, não pacote de
produção). O inventário completo `aurora-i18n-inventory-audit.json` contém cada
msgid, referências, plurais, contexto, traduções, preservação das entradas antigas
e SHA-256 dos nove templates para detectar deltas concorrentes.

1. RED: os testes gettext de login/avatar/limites/crise falharam **14 vezes** em
   en/es por devolver português; pt-br passou nos 7 casos.
2. GREEN: após inclusão das primeiras traduções e `msgfmt`, **21 passaram**.
3. Segundo RED: **9 falhas**, por escopo ausente, metadados antigos e prompt do
   login de psiquiatria sem tradução; **34 passaram**, 3 casos HTTP não executados
   nesse ciclo sem banco.
4. Segundo GREEN sem banco: **43 passaram**, 3 casos HTTP não executados nesse
   recorte. Não houve supressão de warnings nem relaxamento de placeholders/fuzzy.
5. Execução rápida integrada com `--nomigrations`: **79 passaram, 2 falharam,
   1 teste de migração não executado e 15 warnings**. Todos os 46 testes novos
   passaram, inclusive HTML renderizado pt-br/en/es e POST/CSRF/cookie. As duas
   falhas fora do escopo e o warning estão detalhados abaixo.

Comandos utilizados (todos na raiz do checkout):

```sh
export TMPDIR=/Users/rgnsystems/.hermes/cache/scratch
for language in pt_BR en es; do
  for domain in django djangojs; do
    msgfmt --check --statistics locale/$language/LC_MESSAGES/$domain.po \
      -o locale/$language/LC_MESSAGES/$domain.mo || exit
  done
done
.venv/bin/python scripts/check_ui_catalogs.py \
  --scope docs/migration/translated-ui-scope.json \
  --output "$TMPDIR/aurora-i18n-final.json" \
  --pot-output "$TMPDIR/aurora-i18n-final.pot"
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest \
  tests/test_aurora_ui_translations.py tests/test_language_preferences.py \
  tests/test_aurora_design_system.py --no-cov --nomigrations -k 'not migration' \
  --junitxml="$TMPDIR/aurora-i18n-fast.xml"
.venv/bin/python -m ruff check tests/test_aurora_ui_translations.py
.venv/bin/python -m ruff format --check tests/test_aurora_ui_translations.py
```

`msgfmt --check --statistics`: 1.420 mensagens ativas traduzidas em cada
`django.po`, 4 mensagens em cada `djangojs.po`, sem warnings. Ambos os gates
passaram. `check_djangojs_catalogs.py` escreve temporários em `.migration-runtime`
relativo ao próprio arquivo; para não gravar fora do escopo, foi executada uma
**cópia byte a byte inalterada** em
`$TMPDIR/aurora-i18n-js-gate/scripts/check_djangojs_catalogs.py`, com `locale` como
symlink para os catálogos reais. Seu resultado está em
`$TMPDIR/aurora-i18n-djangojs-final.json` e seus três MO de comparação no scratch.
Ruff check/format e `git diff --check` do recorte passaram.

## Pendências e integração do principal

- `tests/test_language_preferences.py::test_only_reviewed_portuguese_is_published_by_default`
  e `test_runtime_languages_separate_local_acceptance_from_production[config.settings.production-expected_languages1]`
  falham porque `config/settings/base.py` publica pt-br/en/es e production importa
  essa lista; os testes/README esperam apenas pt-br fora do desenvolvimento.
  As alterações deste recorte não tocam essa política. O diff atual de base
  adiciona `clinical_operations`, não altera `LANGUAGES`: a divergência de idiomas
  é anterior à tarefa. O principal deve conciliar política/testes sem interpretar
  estes rascunhos como autorização de publicação.
- Warning preservado: WhiteNoise/Django informa ausência de
  `/Users/rgnsystems/projects/auroraelo/staticfiles/`. Não foi criado diretório
  fictício nem silenciado o aviso para aparentar sucesso.
- Tentativas com migrações normais excederam limites de execução; o probe com
  faulthandler aponta preparação Django em `apps/registry.py:lazy_model_operation`.
  O probe isolado permaneceu na preparação após 560 segundos e foi encerrado;
  nenhum processo desta tarefa foi deixado em execução. Não se atribui a causa
  raiz apenas a esse frame. `--nomigrations` comprova comportamento dos testes,
  **não valida migrações**. A execução normal ainda deve ser concluída/confirmada
  pelo principal.
- Não se declara suíte global, PostgreSQL, navegador real, implantação ou revisão
  clínica aprovados. A evidência renderizada é Django `render_to_string`/Client,
  com formulários reais, CSRF e persistência de idioma existentes.
- Reextrair após o merge dos trabalhos concorrentes em `ai_assistant`,
  `psychiatry`, `clinical_operations` e mobile. Este snapshot só incorpora as nove
  superfícies estabilizadas do agente UI; não transforma textos não marcados,
  protótipos históricos ou respostas de API em UI integralmente traduzida.
- A necessidade de revisão humana de linguagem de saúde/crise permanece aberta;
  avatar/IA desativada não é psicólogo humano, atendimento ou plantão. O pipeline
  de tradução não habilita IA nem monitora crises.

## Delta das nove telas sanitizadas

O principal ampliou cumulativamente o escopo de **151 para 160 arquivos**, sem
remoções. Esta etapa apenas completou os catálogos e sua validação: não modificou
settings, templates, URLs, design, política de publicação ou integração clínica.

Telas cobertas em `psychiatry/templates/psychiatry/`:
`addiction_dashboard.html`, `anamnesis.html`, `beds.html`, `crisis_protocol.html`,
`mobile_b2c.html`, `mobile_connected.html`, `patients.html`,
`telepsychiatry_room.html` e `twelve_steps_anamnesis.html`.

### Delta e preservação verificados

Fonte exata: `$TMPDIR/aurora-parent-i18n-delta.json` e seu `.pot`, gerados após a
sanitização. A auditoria Python compara o conjunto de mensagens de cada idioma
com esse JSON, sem estimar faltantes por busca textual.

| Verificação atual | Resultado |
| --- | --- |
| Acréscimos `django.po`/MO | 23 msgids exatos por idioma (`pt_BR`, `en`, `es`) |
| `django.po` ativo por idioma | 1.443 mensagens; 4 plurais; 1 contextual |
| MO completo `django`, sem metadados | 1.447 chaves incluindo formas plurais |
| Gate cumulativo | 160 arquivos; 1.445 chaves requeridas |
| Faltantes / placeholders / MO desatualizados | 0 / 0 / 0 |
| Fuzzy / valores compilados vazios | 0 / 0 |
| Preservação dos PO anteriores | Prefixo completo byte a byte, inclusive obsoletos, flags e metadados |
| Preservação dos MO anteriores | Todas as chaves/valores e metadados anteriores iguais |
| `djangojs` | 4 mensagens / 5 chaves por idioma; PO/MO sem alteração líquida |

O MO completo contém duas chaves além das exigidas pelo escopo. Não foram removidas
entradas anteriores para fazer as contagens coincidirem. Os seis catálogos foram
recompilados com `msgfmt --check --statistics`, **sem warnings**; os três pares
`djangojs.po`/MO permaneceram byte a byte iguais ao snapshot desta etapa.
Metadados continuam declarando rascunho técnico e revisão humana pendente.

As traduções preservam a indisponibilidade de formulários, gravação, notificações,
monitoramento/intervenção, SOS, prescrições, agenda, vídeo, internação e assinaturas.
As listas são apresentadas como somente leitura, limitadas a 15/50 registros, sem
inferir total da clínica. SAMU **192** e CVV **188** continuam restritos ao **Brasil**,
com orientação explícita para o serviço local de emergência em outros países.
Não há promessa de atendimento, plantão, ajuda enviada ou operação clínica.

### TDD e HTML renderizado

`tests/test_psychiatry_ui_translations.py` mantém a asserção original de inclusão
no escopo e passa a conter **106 casos**:

- 1 contrato de escopo cumulativo;
- 69 verificações das 23 mensagens × 3 idiomas: valor literal esperado no MO e
  `gettext` real; presença explícita no MO impede fallback silencioso em pt-br;
- 27 renderizações das 9 telas × 3 idiomas com `render_to_string` e RequestFactory;
- 9 renderizações adicionais com listas/perfil vazios, sem inventar pacientes.

O HTML é inspecionado com `HTMLParser`, incluindo avisos literais traduzidos,
formulários apenas do seletor de idioma, ausência de formulário clínico ativo,
links `tel:192`/`tel:188` e rótulos localizados no Brasil. Os contextos usam
`AnonymousUser` e `SimpleNamespace` inteiramente sintéticos, com nome contendo
markup para verificar escape. Nenhum modelo é salvo ou consultado. A proteção
padrão do pytest-django contra acesso ao banco permanece ativa: estes testes não
usam `django_db`, `db` nem desbloqueio do banco. Objetos de contexto **não simulam
uma autorização clínica bem-sucedida**; autorização/API pertencem a outras suítes.

Resultados locais, com totais recontados por Python a partir do JUnit:

| Execução | Resultado |
| --- | --- |
| RED antes de editar PO/MO | 93 falhas esperadas, 13 passaram; nenhum erro/skip; 9,28 s |
| GREEN novo arquivo, sem banco e sem `--nomigrations` | 106 passaram; nenhum warning; 6,92 s |
| Regressão dos 46 anteriores + 106 atuais, SQLite em memória, `--nomigrations` | 152 passaram, 3 warnings; nenhum erro/falha/skip; 19,11 s |
| Ruff check/format dos dois arquivos de testes | Aprovados |
| Gates UI e djangojs | Aprovados |

As 93 falhas RED foram ausência das 69 entradas compiladas e fallback de idioma
em 24 renderizações en/es. O teste de escopo já passava após a ampliação feita
pelo principal. Os 3 warnings da execução combinada vêm dos testes HTTP anteriores:
WhiteNoise informa a ausência de `staticfiles/`. Não foram silenciados.

Comandos desta etapa, na raiz do checkout:

```sh
export TMPDIR=/Users/rgnsystems/.hermes/cache/scratch
export DJANGO_SETTINGS_MODULE=config.settings.test
export TEST_DATABASE=sqlite SQLITE_NAME=:memory:

# Primeiro RED; depois repetir após compilar os catálogos para GREEN.
.venv/bin/python -m pytest tests/test_psychiatry_ui_translations.py \
  --no-cov -q --tb=short -o faulthandler_timeout=45 \
  --junitxml="$TMPDIR/aurora-psychiatry-i18n-green.xml"

for language in pt_BR en es; do
  for domain in django djangojs; do
    msgfmt --check --statistics "locale/$language/LC_MESSAGES/$domain.po" \
      -o "locale/$language/LC_MESSAGES/$domain.mo" || exit
  done
done

.venv/bin/python -m pytest tests/test_aurora_ui_translations.py \
  tests/test_psychiatry_ui_translations.py --no-cov --nomigrations -q \
  --tb=short -o faulthandler_timeout=45 \
  --junitxml="$TMPDIR/aurora-psychiatry-i18n-combined.xml"

.venv/bin/python scripts/check_ui_catalogs.py \
  --scope docs/migration/translated-ui-scope.json \
  --output "$TMPDIR/aurora-psychiatry-i18n-final.json" \
  --pot-output "$TMPDIR/aurora-psychiatry-i18n-final.pot"

# Executa o verificador djangojs inalterado, com temporários só no scratch.
.venv/bin/python -c 'import os, shutil; from pathlib import Path; root=Path.cwd(); mirror=Path(os.environ["TMPDIR"])/"aurora-psychiatry-i18n-js-gate"; (mirror/"scripts").mkdir(parents=True, exist_ok=True); source=root/"scripts/check_djangojs_catalogs.py"; target=mirror/"scripts/check_djangojs_catalogs.py"; shutil.copyfile(source, target); assert source.read_bytes()==target.read_bytes(); link=mirror/"locale"; link.exists() or link.symlink_to(root/"locale", target_is_directory=True); assert link.resolve()==root/"locale"'
.venv/bin/python "$TMPDIR/aurora-psychiatry-i18n-js-gate/scripts/check_djangojs_catalogs.py" \
  --output "$TMPDIR/aurora-psychiatry-i18n-djangojs-final.json"

.venv/bin/python -m ruff check \
  tests/test_aurora_ui_translations.py tests/test_psychiatry_ui_translations.py
.venv/bin/python -m ruff format --check \
  tests/test_aurora_ui_translations.py tests/test_psychiatry_ui_translations.py
```

Evidências adicionais no scratch: `aurora-psychiatry-i18n-red.xml`/`.log`,
`aurora-psychiatry-i18n-green.xml`, `aurora-psychiatry-i18n-combined.xml`,
`aurora-psychiatry-i18n-results.json` (contagens JUnit e gates),
`aurora-psychiatry-i18n-audit.py`/`.json` (delta, preservação e hashes das telas),
e `aurora-psychiatry-i18n-before/` (somente os 12 arquivos PO/MO anteriores).
Nenhum artefato desta etapa foi escrito na `.migration-runtime` do checkout.

### Limitações que continuam abertas

- A execução combinada rápida **não valida migrações** nem PostgreSQL. As
  migrações SQLite normais não foram repetidas depois dos timeouts já registrados.
  O PostgreSQL descartável na porta 55439 não foi usado em paralelo ao principal.
- As duas divergências preexistentes de política de idiomas (base/production
  publicam três, README/testes esperam pt-br) continuam fora do escopo; esses
  testes não foram alterados nem reexecutados nesta etapa. Os testes de HTML
  sobrescrevem `LANGUAGES` apenas para exercitar os três catálogos, sem publicar.
- A evidência é gettext real e renderização Django local, não navegador real,
  revisão humana/clínica, funcionamento de atendimento, avaliação de todos os
  endpoints, suíte global, aceite de produção ou liberação de idiomas.
- Reextrair se as fontes mudarem após este snapshot. Não houve commit, push,
  deploy, acesso a `.env`, credenciais ou bancos reais.

