# Mindcare — assets de runtime

Estado verificado em 2026-09-09. Este manifesto substitui o baseline histórico
de `docs/duralux/runtime-asset-manifest.md` para o projeto Mindcare.

## Seleção e carregamento

21 arquivos ativos em runtime (17 originais + 3 SVGs de bandeiras usadas no seletor + 1 script vanilla do customizer). Bootstrap CSS 5.3.3, tema Duralux sanitizado, ponte CSS própria, estilos de autenticação,
Feather CSS e suas três fontes; Bootstrap bundle 5.3.3/Popper 2.11.8; sete scripts
próprios (incluindo `theme-customizer.js` que renderiza a roldana Duralux sem
jQuery, com armazenamento isolado em `localStorage["mindcare:duralux-theme"]`
e sem alterar o `data-bs-theme` do produto); ApexCharts 3.52.0 somente nas
páginas com gráficos; favicon Mindcare e três bandeiras SVG locais
(Brasil/EUA/Espanha), copiadas do diretório de referência
`design_system_duralux/assets/vendors/img/flags/4x3/`.
O seletor expõe agora cada idioma com sua bandeira e o código em maiúsculas, em
substituição do globo Feather. A mudança preserva o glifo do Feather somente nos
demais ícones da interface. A roldana Duralux só é renderizada em shells
autenticados (incluída em `templates/layouts/base.html`); o login permanece
sem roldana para não atrapalhar o formulário.
As bases carregam product-shell antes dos estilos para restaurar o tema, depois
Bootstrap CSS → Feather (nas bases autenticadas/autenticação) → theme → integração.
O bundle Bootstrap e o `theme-customizer.js` são diferidos. Formulários, aulas e
gráficos carregam scripts pelos seus consumidores. Não há Google Fonts, CDN,
sourcemaps, inicializador demo ou jQuery no runtime. Fontes do texto: pilha
system-ui local.

Os logos RGN importados foram inspecionados e retirados do runtime. O monograma M
é SVG próprio; `layouts/partials/brand.html` preserva o logo configurado da clínica
e usa Mindcare no fallback. O pacote de referência original permanece intacto.

## Licenças e proveniência

Bootstrap, Popper e ApexCharts mantêm avisos versionados em `docs/duralux/licenses/`.
O CSS do tema mantém o cabeçalho original; não há documento de licença Duralux
no pacote local. Os créditos Feather constam da documentação do fornecedor,
mas não há texto de licença Feather arquivado nessa pasta. Esses pontos permanecem
pendentes em S07.01; este manifesto não atesta autorização de redistribuição.
O antigo manifesto conserva a proveniência das distribuições normalizadas.

## Coleta e validação

`STATICFILES_DIRS` aponta para `static/`; `STATIC_ROOT` para `staticfiles/`.
A coleta local e os testes de manifest storage usam saída gerada ou temporária.
O conjunto inclui ainda os arquivos do Django Admin; não inclui a pasta de referência.
`tests/test_duralux_static_foundation.py` confere seleção, hashes, referências CSS,
coleta e post-processamento. Evidências atuais: `evidence/collectstatic-foundation.log`
e `evidence/foundation-focused.log`. A coleta local não é publicação/deploy.

## SHA-256

| Arquivo relativo a static/duralux | SHA-256 |
|---|---|
| `css/auth.css` | `518c5b8552b2cf1a88dce50e8a776cc9233a1276e816838d355c34291954c2ff` |
| `css/bootstrap.min.css` | `26db49828d6701fcfce37a96da6ec3f0ed481abae49c8c9969a575b064413cad` |
| `css/product-integration.css` | `70fc92e6bd8be6c7c3d166c28f79ed15c62e15df727bad5929c508a2da4c0dd0` |
| `css/theme.min.css` | `71257c55b10217bf94a0f71c3fda141545ad500a6bebec5bbeb29ee65c5d0be9` |
| `images/auth/mindcare-peace-light.svg` | `d4f881a389dd01f3a07714c290af8023aed416e343a7ab1b951b53e717740b75` |
| `images/auth/mindcare-peace-dark.svg` | `b7fe6b9fe36a1c0c9da95f73dd709e303e7fc7d8cd2c3395d3657fec06eb2472` |
| `images/favicon.svg` | `c25f91807314d0c2af9077f98d890e5e7d9bcbcea8ac3c4a98b5478c1c8fa724` |
| `images/flags/br.svg` | `fc872e714b4664158f200f0967861e260dbaf6ac32c9e3fa9a6628e9c4631342` |
| `images/flags/us.svg` | `553867d379deaaf0d8379531cc1f8ef3002cd13e5e006523ddc49a0204932d6c` |
| `images/flags/es.svg` | `6fe80291cd9be7f06d9f205081c3a5264da531b49e40ddbe63bda08a83c1afd9` |
| `js/bootstrap.bundle.min.js` | `073254afbfc06331b8b548b7fc0532b4ffe2cfdd588368dcc338e7abd50810e1` |
| `js/dashboard-charts.js` | `155d4235c74c1660c02c9ec274b3b87ab43dd4f701918b72f8f4f220540ec047` |
| `js/form-behaviors.js` | `7576ead48d793e4ff00eab29332ede7cfdc0c26d352b0c7269f8c55b4aaf87ab` |
| `js/language-selector.js` | `f3f8e0f7056594794561e2ea22e57f2f044e3812932726ded8a8f0704666446d` |
| `js/lesson-player.js` | `ea7ec89f8b738db3d7cb467466c2a5803cdad380f7656855bd2d514ddc6169a7` |
| `js/product-shell.js` | `2780dbd87feb28348abe41547a3d6cd78ff8aebc7e918cd20aae853d75f949e8` |
| `js/visual-reference-charts.js` | `afc6d2e5cebba8d32aa999b55129f9610cd3a2c1426babbf93d14ba6ecf32715` |
| `vendors/apexcharts/apexcharts.min.js` | `dacc69f7eb21440e4b331ce1831f9fa5e40f218d995a005db789a9e55d989fe1` |
| `vendors/css/feather.min.css` | `fc163d4b37fa11a3457978e56d33b1efe45f713fd7bb7f0a7ef0ff7ea6401ed6` |
| `vendors/fonts/feather.eot` | `2495770aa8837a3afb8084ea275c469d18965228579231ec5fae6e86d5c2cc84` |
| `vendors/fonts/feather.ttf` | `3bcfe225579659dbaf31019171840d5f4e4b02e63481706aa8f9a3841f450e7e` |
| `vendors/fonts/feather.woff` | `5495042500a1bbf616f91d717aa3637efca7eb4c646683818f5c6c1998500ff9` |
