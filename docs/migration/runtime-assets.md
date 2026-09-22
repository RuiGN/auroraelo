# Aurora Elo — assets de runtime

Manifesto operacional de `static/duralux/`, com hashes calculados dos bytes do
checkout. Substitui o baseline histórico de
`docs/duralux/runtime-asset-manifest.md`; não reescreve evidências anteriores nem
comprova publicação em produção. A política de marca está em
[branding-scope.md](branding-scope.md).

## Seleção e carregamento

22 arquivos em `static/duralux/`: quatro CSS, seis SVGs, sete JavaScripts e cinco
arquivos vendorizados. O conjunto contém Bootstrap CSS/bundle 5.3.3 com Popper
2.11.8, tema Duralux sanitizado, integração própria, estilos de autenticação,
Feather CSS/fontes e ApexCharts 3.52.0. As bandeiras locais representam
Brasil/EUA/Espanha; as duas ilustrações de autenticação usam os nomes
`aurora-elo-peace-light.svg` e `aurora-elo-peace-dark.svg`.

`product-shell.js` fixa o tema claro neste checkout e aplica a identidade
configurada da clínica. Não há `theme-customizer.js` no conjunto publicado:
a descrição anterior da roldana e de sua chave de armazenamento não descrevia
os arquivos atuais. Formulários, aulas, idiomas e gráficos têm scripts próprios.
Não há Google Fonts, CDN, sourcemaps, inicializador demo ou jQuery neste conjunto.
As fontes de texto usam a pilha system-ui local.

O contrato da identidade de fallback é **Aurora Elo**, preservando o logo e o
nome configurados por clínica em `layouts/partials/brand.html`. O teste de marca
exige favicon vetorial com rótulo acessível correto, ausência da marca anterior
nos templates e preservação dos pontos de integração por clínica. Um hash válido
não é aprovação visual: favicon, CSS consumidor das ilustrações e templates
precisam passar juntos pelos testes após a integração dos responsáveis.

O favicon deste namespace reutiliza os elementos vetoriais já presentes em
`static/images/favicon.svg`, com título e rótulo acessível Aurora Elo. Não foi
reconstruído a partir do antigo monograma nem contém imagem raster embutida.

Este manifesto cobre somente `static/duralux/`, não todos os namespaces estáticos
nem os builds mobile. O design system e os templates têm validação própria.

## Licenças e proveniência

Bootstrap, Popper e ApexCharts mantêm avisos versionados em `docs/duralux/licenses/`.
O CSS do tema mantém o cabeçalho original; não há documento de licença Duralux
no pacote local. Os créditos Feather constam da documentação do fornecedor,
mas não há texto de licença Feather arquivado nessa pasta. Esses pontos permanecem
pendentes em S07.01; este manifesto não atesta autorização de redistribuição.
O antigo manifesto conserva a proveniência das distribuições normalizadas.

Por decisão do usuário, `design_system_duralux/` não é referência visual nem
insumo de validação desta versão. A referência exclusiva é `design_system/`.
O namespace de runtime aqui inventariado permanece somente por compatibilidade;
as licenças dos componentes efetivamente distribuídos continuam relevantes.

## Coleta e validação

`STATICFILES_DIRS` aponta para `static/`; `STATIC_ROOT` para `staticfiles/`.
A coleta local e os testes de manifest storage usam saída gerada ou temporária.
O conjunto coletado inclui também os arquivos do Django Admin; não inclui a pasta
de referência. `tests/test_duralux_static_foundation.py` confere igualdade exata
do inventário, SHA-256, referências CSS, coleta e post-processamento.

Os logs `evidence/collectstatic-foundation.log` e `evidence/foundation-focused.log`
são evidências históricas, não resultados desta atualização. O teste de runtime
verifica sanitização sem depender do pacote de referência excluído. Os contratos
de inventário, SHA-256, URLs locais e coleta com manifest storage permanecem.
A coleta local não é deploy. Recalcule esta tabela sempre que os bytes de um
ativo forem alterados.

## SHA-256

| Arquivo relativo a static/duralux | SHA-256 |
|---|---|
| `css/auth.css` | `f857eda094d63ffa84356caf6d171387ad481cbd3b867f8c716d54e60057aa05` |
| `css/bootstrap.min.css` | `26db49828d6701fcfce37a96da6ec3f0ed481abae49c8c9969a575b064413cad` |
| `css/product-integration.css` | `70fc92e6bd8be6c7c3d166c28f79ed15c62e15df727bad5929c508a2da4c0dd0` |
| `css/theme.min.css` | `71257c55b10217bf94a0f71c3fda141545ad500a6bebec5bbeb29ee65c5d0be9` |
| `images/auth/aurora-elo-peace-dark.svg` | `b7fe6b9fe36a1c0c9da95f73dd709e303e7fc7d8cd2c3395d3657fec06eb2472` |
| `images/auth/aurora-elo-peace-light.svg` | `d4f881a389dd01f3a07714c290af8023aed416e343a7ab1b951b53e717740b75` |
| `images/favicon.svg` | `39df9d29e4b9ed3d6443037e862f03863b85b2279790f42019ea8b0541c1534d` |
| `images/flags/br.svg` | `fc872e714b4664158f200f0967861e260dbaf6ac32c9e3fa9a6628e9c4631342` |
| `images/flags/es.svg` | `6fe80291cd9be7f06d9f205081c3a5264da531b49e40ddbe63bda08a83c1afd9` |
| `images/flags/us.svg` | `553867d379deaaf0d8379531cc1f8ef3002cd13e5e006523ddc49a0204932d6c` |
| `js/bootstrap.bundle.min.js` | `073254afbfc06331b8b548b7fc0532b4ffe2cfdd588368dcc338e7abd50810e1` |
| `js/dashboard-charts.js` | `155d4235c74c1660c02c9ec274b3b87ab43dd4f701918b72f8f4f220540ec047` |
| `js/form-behaviors.js` | `7576ead48d793e4ff00eab29332ede7cfdc0c26d352b0c7269f8c55b4aaf87ab` |
| `js/htmx.min.js` | `e209dda5c8235479f3166defc7750e1dbcd5a5c1808b7792fc2e6733768fb447` |
| `js/language-selector.js` | `f3f8e0f7056594794561e2ea22e57f2f044e3812932726ded8a8f0704666446d` |
| `js/lesson-player.js` | `ea7ec89f8b738db3d7cb467466c2a5803cdad380f7656855bd2d514ddc6169a7` |
| `js/product-shell.js` | `2780dbd87feb28348abe41547a3d6cd78ff8aebc7e918cd20aae853d75f949e8` |
| `js/visual-reference-charts.js` | `afc6d2e5cebba8d32aa999b55129f9610cd3a2c1426babbf93d14ba6ecf32715` |
| `vendors/apexcharts/apexcharts.min.js` | `dacc69f7eb21440e4b331ce1831f9fa5e40f218d995a005db789a9e55d989fe1` |
| `vendors/css/feather.min.css` | `c6d18124f922a020ebaba31b091d8269cbb56d869e02244d382af5acfd03452c` |
| `vendors/fonts/feather.eot` | `2495770aa8837a3afb8084ea275c469d18965228579231ec5fae6e86d5c2cc84` |
| `vendors/fonts/feather.ttf` | `3bcfe225579659dbaf31019171840d5f4e4b02e63481706aa8f9a3841f450e7e` |
| `vendors/fonts/feather.woff` | `5495042500a1bbf616f91d717aa3637efca7eb4c646683818f5c6c1998500ff9` |
