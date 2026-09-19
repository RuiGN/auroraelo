# Componentes compartilhados — S07.05 e S07.08

Verificação em 2026-09-08, no destino Mindcare e com dados sintéticos.

## Alterações e contratos

- Campos preservam atributos, classes, campos ocultos, valores, widgets de domínio
  e formatos personalizados. Somente widgets padrão recebem adaptação estrutural.
- Grupos usam `fieldset`/`legend`; os links de erro apontam para opções focáveis.
  Erros de campos ocultos permanecem no resumo, sem links inacessíveis.
- O catálogo passa explicitamente o token CSRF ao incluir o formulário com `only`.
  GET seguido de POST real, com proteção CSRF ativa, foi validado.
- Após erro, o foco vai para o primeiro controle inválido visível; erros gerais
  usam o resumo focável. O retorno pelo histórico preserva botões originalmente
  desabilitados e recupera aqueles bloqueados apenas durante o envio.
- Checkboxes/rádios mantêm proporções nativas dentro de rótulos clicáveis de 44 px.
  A paginação acomoda textos completos, inclusive sob o seletor do layout Duralux.
- Cards de tabela no celular mostram cada campo uma vez e preservam ordenação,
  direção atual, próxima direção e ações. Tabelas vazias apresentam texto explícito.
- Cards e estados usam hierarquia compacta; tendência neutra não sugere crescimento.

## Evidência reproduzível

- Testes focados: **53 passed**, registrados durante implementação em
  `.migration-runtime/component-focused.log` (temporário/ignorado). Os mesmos
  casos integram o JUnit final versionado desta entrega.
- `scripts/verify-duralux-components.cjs`: **9 cenários aprovados**, em 390/1440 px,
  claro/escuro, no preview local descartável. Resultados e capturas estão em
  `visual-components/`. Inclui POST inválido/válido, foco, modal/offcanvas por
  teclado, vazio, desabilitado, estados de conteúdo e quatro negativas HTTP 403
  para um paciente sem acesso ao catálogo interno.
- Uma página isolada de teste no navegador comprova restauração por `pageshow`
  e foco em erros gerais. Isso complementa os POSTs reais ao servidor.
- `../component-review.md` registra revisão independente e correções de widgets,
  duplicação móvel e informação de ordenação. Não houve alteração de política.
- `../runtime-assets.md` contém os hashes atuais dos 16 assets, incluindo o CSS
  exclusivo da autenticação. A coleta local contém 146 arquivos com Django Admin.

## Limites

Estes resultados validam os seis componentes e seu catálogo. Não representam
aceite automático de todos os consumidores, domínios, layouts ou templates.
As tarefas visuais restantes, licenças, cobertura global e homologação integrada
continuam discriminadas em `DURALUX.prd` e `latest-verification.json`.
