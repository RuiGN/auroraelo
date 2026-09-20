# Aurora Elo — verificação renderizada da integração visual

Referência visual exclusiva: `design_system/`. `design_system_duralux/` não foi
usado nesta verificação. O runtime legado permanece somente por compatibilidade.

## Execução local confirmada pelo integrador

- `npm --prefix design_system ci --ignore-scripts --no-audit --no-fund`: aprovado.
- `npm --prefix design_system run build`: aprovado; Tailwind 3.4.17 fixado.
- `npm --prefix design_system test`: dois testes Node aprovados.
- Testes Django de `test_aurora_design_system.py`, `test_layouts.py` e
  `test_duralux_wcag_and_responsive.py`: 46 aprovados com `--nomigrations`, antes
  da adição do teste de build Docker. O novo teste passou separadamente após o
  ciclo vermelho/verde do Dockerfile.
- `docker build --target ui-build -t auroraelo-ui-test:local .`: aprovado.
  O Dockerfile compila o CSS em estágio Node separado e copia o resultado para
  a imagem Python. Isso não equivale a um build aprovado da imagem final.
- CSS gerado no container e no host: 53.980 bytes, SHA-256 idêntico:
  `8b724f9721ecb28569b87eca5d2e03a84bed02ce91d285884c6776ff8eba6da1`.
- Ruff, `node --check` e whitespace dos arquivos de UI/build verificados passaram.

## Navegador real, dados sintéticos

Chrome 153.0.8010.52, headless, perfil isolado no scratch; nenhum perfil pessoal
ou login real foi usado. A ferramenta de navegador não conseguiu copiar o perfil
pessoal aberto, então o ensaio utilizou CDP com uma instância independente, sem
fechar o Chrome do usuário nem alterar sua configuração global.

Foram renderizados HTMLs Django reais de login e workspace com clientes de teste,
e o template do portal de psiquiatria com o contexto sintético do workspace.
A base SQLite estava somente em memória e foi criada sem executar migrations.
Os snapshots foram servidos localmente com os headers de segurança capturados da
resposta Django e os assets atuais do checkout.

Matriz completa: três páginas × duas larguras, **seis casos**:

| Superfície | Larguras CSS | Resultado observado |
|---|---|---|
| Login | 1440 e 390 | CSS e imagens carregados; formulário/CSRF presentes; sem overflow horizontal |
| Workspace | 1440 e 390 | CSS e imagens carregados; conteúdo principal visível; sem overflow horizontal |
| Portal de psiquiatria | 1440 e 390 | CSS e avatar carregados; estado da IA desativado; sem overflow horizontal |

Zero erros JavaScript/console e zero respostas HTTP >= 400 capturados nos seis
casos. Nos dois menus móveis, abertura, Escape, estado ARIA e restauração do foco
passaram. Escape foi enviado pelo protocolo de entrada do navegador, não por um
evento disparado no nó errado do DOM. Foram salvas seis capturas PNG.

## Evidências locais

Diretório: `/Users/rgnsystems/.hermes/cache/scratch/aurora-ui-browser/`.

- `rendered-results.json`: matriz, medições, imagens, interações e erros.
- `snapshot-metadata.json`: origem sintética e headers aplicados.
- `login-{1440,390}.png`, `workspace-{1440,390}.png`,
  `psychiatry-{1440,390}.png`: capturas renderizadas.
- Script do ensaio: `../aurora-ui-browser-check.cjs`.
- Log de build: `../aurora-ui-docker-build.log`.

## Limites e pendências

O ensaio mede layout/DOM e interações reais, mas não é aprovação estética por
inspeção humana das imagens, auditoria WCAG completa ou teste em dispositivo.
Os snapshots não executam autenticação, envio de formulário ou persistência;
nenhum sucesso desses fluxos é inferido do navegador. O ensaio foi em pt-BR;
catálogos e percursos completos en/es ainda precisam de validação integrada.

Não valida migrations, todas as páginas clínicas filhas, prévias mobile, a imagem
Docker final nem produção. Templates legados ainda podem ter mockups ou scripts
inline; não estão aprovados por este relatório. IA comercial continua desativada.
