# Integração Django — design_system

## Build reproduzível

Na raiz do repositório:

```sh
npm --prefix design_system ci --ignore-scripts --no-audit --no-fund
npm --prefix design_system run build
```

Tailwind **3.4.17**, fixado em package.json e package-lock.json, é compatível com
`tailwind.config.js` CommonJS.
Os arquivos publicados em `static/design_system/` são cópias de serviço do pacote:
páginas (`index.html`, `login.html`, `mobile-*.html`), componentes, JS de showcase
e assets são sincronizados do pacote (paridade visual total; o showcase pode usar
o Tailwind do CDN e as fontes da Google, liberados na CSP). `css/tokens.css` e
`css/custom.css` publicados são as cópias do pacote (diretivas `@theme` v4 e
import de fontes).

Os insumos do build ficam em `src/`: `src/tokens.local.css` e `src/custom.local.css`
(sem `@theme` e sem fontes remotas) são importados por `src/aurora.css` junto com
`src/shell.css` e compilados em `static/design_system/css/aurora.css`; incluir esse
resultado no deploy. O CSS compilado não pode conter `@theme`, `@tailwind` nem
`fonts.googleapis.com` (contrato de teste).
Sem Node, CDN, compilador Tailwind ou fonte Google no navegador dos shells.

A referência visual é exclusivamente **design_system/**. O Bootstrap/Duralux já
publicado permanece somente como compatibilidade de formulários, dropdowns e
navegação existentes. O build desativa preflight e limita utilitários à classe
`aurora-utilities`; não instalar outra cópia de Bootstrap. O CSS legado
`static/css/aurora-theme-override.css` ainda está carregado pelo workspace.

## Superfícies integradas

- `accounts/auth_base.html`, `accounts/auth_form.html`: formulário real preservado,
  sem credenciais demo, preenchimento automático nem scripts inline.
- `layouts/base.html`, header/navigation e workspace/home: CSS compilado local,
  cards e labels sem métricas ou monitoramento simulados.
- `psychiatry/base_aurora.html`, dashboard e login: herança do shell compartilhado,
  menu responsivo com JS local, seletor canônico, avatar identificado como IA
  indisponível. Login legado aponta ao login de contas, não simula autenticação.

Rotas existentes, não alteradas: `account_login`, `account_set_language`,
`workspace_vertical`, `workspace_detached`, `psychiatry:dashboard`,
`psychiatry:login` e links de navegação previamente disponíveis.

## i18n / CSP / limites

O idioma vem de gettext/get_current_language. O seletor existente continua usando
POST com CSRF em `account_set_language` e a persistência de accounts. Não há
tradução automática de registros clínicos. Strings novas precisam entrar nos
catálogos pt_BR/en/es pelo integrador; renderizar `lang=en` não comprova catálogo
traduzido. `ui-strings.json` lista msgids das superfícies alteradas.

O JS do shell aceita `script-src self`. Os blocos extra_js/page_scripts foram
preservados; templates filhos ainda não migrados podem conter código inline ou
mockups e exigem revisão separada. Os HTMLs estáticos históricos de showcase em
design_system e as prévias mobile web não são uma implementação clínica e ainda
não foram migrados neste recorte. Não publicá-los como atendimento real.

Nenhum template foi excluído; atualizar os escopos i18n e os manifests de runtime
no integrador. Não houve alteração em backend, settings, locale, mobile ou
static/duralux nesta tarefa.
