# Readiness mobile — Aurora Elo

## Decisão de entrega

**Base local verificável; não pronta para distribuição clínica ou comercial.**
Os dois apps abrem uma interface local de recuperação e indisponibilidade segura.
Não existe integração operacional com prontuário, medicação, SOS, teleconsulta,
pagamento, login mobile ou LLM. IA comercial permanece **DESATIVADA** por decisão
expressa do produto até API própria, revisão clínica independente e consentimento
versionado. Não há chave LLM, token persistido, chamada simulada ou conversa falsa.

## Stack e correções

Manifests originais conferidos: Expo `~52.0.0`, React `18.3.1`, RN `0.76.5`.
Mantido SDK 52; `expo install --fix` escolheu RN `0.76.9`. AsyncStorage `1.23.1`,
safe-area-context `4.12.0`, expo-asset `~11.0.5`, react-dom `18.3.1` e
react-native-web `~0.19.13` foram instalados pelo resolvedor Expo. Não houve
`--force`, `--legacy-peer-deps`, upgrade major nem SDK nativo baixado.

- Entrypoints reais `index.js` com `registerRootComponent`, TS estrito, scripts de
  typecheck, teste, formatação e export; um `package-lock.json` por app.
- Removidos comentários HTML inválidos em TSX e bibliotecas sem uso no protótipo.
- Safe areas via provider; texto dimensionável e controles com altura mínima 48.
- Marca Aurora Elo, foco álcool/substâncias, apostas/jogos de azar e jogos digitais.
- Removidos pacientes, doses, consultas, preços, dias de progresso e sucessos falsos.
- Sem permissões declaradas de câmera, microfone, localização ou notificações;
  `blockedPermissions` previne inclusão por dependências Android. Isso não
  substitui inspeção de um manifesto nativo final, ainda não produzido.
- Ícone apontava para arquivo inexistente; referência removida. Ícones de loja
  definitivos, assinatura e metadados de publicação permanecem pendentes.
- Metro observa somente a raiz do app e `mobile/shared`, não a árvore Django.

## Idiomas, consentimento e indisponibilidade

Catálogo tipado compartilhado `mobile/shared/i18n.ts`: `pt-br`, `en`, `es`.
As chaves devem existir nos três idiomas. A preferência usa exclusivamente
`aurora-elo.ui-language` no AsyncStorage de cada app; não é compartilhada entre
instalações. Leitura inicial e gravação bloqueiam o seletor temporariamente;
falhas de armazenamento aparecem na UI. Não se grava preferência automaticamente
na primeira abertura. Não há tradução de conteúdo clínico nem coleta de relatos.
Traduções precisam de aceitação humana/terminológica antes da distribuição.

`mobile/shared/safety.ts` expõe política imutável `{enabled: false, consent: false}`.
Nenhuma variável pública, status de rede ou toggle pode habilitar IA. Avatar é
rotulado como inteligência artificial, não pessoa. O consentimento está desmarcado
**e indisponível**: não representa consentimento jurídico nem acesso autorizado.
Mesmo chamada direta a `startDigitalSupport()` rejeita `unavailable` sem transporte.
A UI comunica que não há conversa, monitoramento nem alternativa LLM offline.

A ajuda urgente informa **“Ninguém foi notificado”** e orienta procurar emergência
local/pessoa de confiança. Não solicita localização, não apresenta envio pendente,
não promete plantão. Connected informa que nenhuma dose foi registrada/sincronizada.

## Contratos backend inspecionados e não integrados

Inspeção estática inicial em `config/urls.py`, `psychiatry/urls.py` e
`psychiatry/api.py` revelou, sob `/psiquiatria/api/v1/patient/`:

| Rota histórica | Evidência no início da tarefa | Decisão mobile |
|---|---|---|
| `summary/` GET | Dados literais de paciente, medicamentos e consulta | Não consumir |
| `medications/log/` POST | Resposta de sucesso sem persistência correspondente | Rejeitar localmente |
| `sos/` POST | Mensagem de sucesso sem entrega demonstrada | Rejeitar localmente; ninguém notificado |

Essas implementações podem ser endurecidas pelo agente principal durante a mesma
migração. A tabela documenta a razão da remoção, **não homologa o backend atual**.
`AuroraApiService` mantém os nomes das operações, mas todas rejeitam `unavailable`
sem HTTP. Não aceita payload clínico nem oferece autenticação improvisada.

O catálogo público de recuperação ainda estava sob implementação pelo principal.
Nenhuma URL de catálogo, schema, disponibilidade JWT ou entrega SOS foi inventada.
A UI não faz qualquer chamada API ao abrir, trocar idioma ou tocar na IA bloqueada.

### Transporte disponível para uma integração futura

`mobile/shared/http.ts` + `src/services/publicApi.ts` em cada app:

- `EXPO_PUBLIC_API_BASE_URL` é origem pública HTTPS explícita (DNS ASCII minúsculo,
  porta opcional de 1 a 65535, barra final opcional). Sem credenciais, path/query/hash.
  Ausente/inválida gera erro `configuration`, nunca fallback para localhost.
- Somente GET de caminhos absolutos com segmentos alfanuméricos/hífen/underscore e
  barra final. Sem query, traversal, URL absoluta externa ou headers de autenticação.
- `credentials: omit`, `redirect: error`, timeout padrão 8 segundos abrangendo
  leitura JSON; AbortController e limite local mesmo se transporte ignorar abort.
- Status não-2xx gera `http` com status; rede, timeout e conteúdo inválido têm códigos
  próprios. Não exibe corpo, URL sensível ou erro bruto do servidor.
- JSON exige content-type esperado, URL final exata e validador de schema fornecido.
- A URL global do RN 0.76 tem getters não implementados. Um teste usando essa
  implementação real falhou com `URL.protocol is not implemented`; a validação usa
  gramática restrita independente da URL do Node, sem acrescentar polyfill pesado.
- **Limite conhecido:** o fetch nativo/polyfill pode seguir redirect antes da
  validação final. `redirect: error` não é promessa de bloqueio em dispositivo.
  Este transporte não deve ser reutilizado para dados autenticados/sensíveis.
  Os testes de HTTP injetam transporte sintético; TLS, XHR nativo, redirects e
  conectividade real em iOS/Android ainda não foram homologados.

Não há sessão/token para proteger nesta entrega. Antes de autenticação será
necessário contrato de login/refresh/revogação/expiração, autorização paciente-clínica
no servidor, SecureStore para segredos, tratamento de 401 sem loop, política de
backup/logs e testes cross-tenant. Não usar AsyncStorage para tokens.

## Evidência executada

Ambiente observado: macOS, Node `v24.21.0`, npm `11.19.0`, Python `3.14.7`.
Todos os dados de testes são sintéticos. Não foi lido `.env`, banco ou prontuário.

| Verificação | B2C | Connected | O que comprova |
|---|---:|---:|---|
| `npm ci --no-fund` | Passou | Passou | Reinstalação pelos locks |
| `npm run format:check` | Passou | Passou | Prettier no escopo fonte/teste/config |
| `npm run typecheck` | Passou | Passou | TS incluindo módulos compartilhados |
| `npm test` | 22 passaram | 25 passaram | Jest-expo em Node, componentes renderizados por React Test Renderer |
| `EXPO_NO_DOTENV=1 npx expo install --check` | Passou | Passou | Compatibilidade do SDK instalado |
| `EXPO_NO_DOTENV=1 npx expo-doctor` | 18/18 | 18/18 | Verificações Expo, não auditoria de segurança |
| `CI=1 npm run export` | Passou | Passou | JS web e bytecode Hermes Android/iOS |

A suíte inclui abertura sem dados fictícios/rede, gate de IA, consentimento falso,
idiomas en/es com remount e persistência, falha de gravação, status 401/403/429/500/503,
timeout/abort, JSON incompatível, destino inválido e URL parcial do RN. Connected
adiciona três operações clínicas bloqueadas. Casos compartilhados reexecutados nos
dois apps não representam funcionalidades distintas nem plataformas nativas testadas.

TDD: observado vermelho para ausência de scripts/entrypoints, branding/IA, seletor,
persistência, bloqueio clínico, HTTP, URL nativa e configuração/permissões; depois
verde. O primeiro export identificou falta de `expo-asset`, corrigida com Expo.
Jest teve timeout de transformação inicial em execuções concorrentes; orçamento por
teste aumentado para 30s, sem remover asserções. Execução final não teve warnings React.

Teste de contrato Python, sem banco:

```sh
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest tests/test_mobile_recovery_contract.py -q --no-cov
.venv/bin/python -m ruff check tests/test_mobile_recovery_contract.py
.venv/bin/python -m ruff format --check tests/test_mobile_recovery_contract.py
git diff --check -- mobile tests/test_mobile_recovery_contract.py docs/migration/mobile-readiness.md
```

Quatro testes Python passaram. Ruff passou. `git diff --check` mobile passou depois
da formatação. A suíte backend completa é responsabilidade da integração principal.

Tentativa adicional de browser: o helper recusou o perfil Chrome real por lock;
não encerramos o Chrome do usuário nem alteramos configuração Hermes. Chrome
headless com perfil temporário teve timeout de 45s. Os exports foram servidos
localmente e responderam HTTP 200, mas **não se declara aceitação visual/browser**.
A evidência renderizada entregue é dos componentes React no Jest, não screenshot,
VoiceOver/TalkBack, acessibilidade nativa ou fluxo em aparelho.

### Artefatos exportados e verificáveis

Arquivos em `mobile/<app>/dist/` (ignorados no Git); verificados no disco após export.
Não são binários nativos instaláveis. SHA-256 dos bundles:

| App/plataforma | Arquivo relativo a dist | Bytes | SHA-256 |
|---|---|---:|---|
| B2C web | `_expo/static/js/web/index-6feb722fa81e5b849d3dd7cd516b203f.js` | 320325 | `c690c349436255aa6f1c6561084ba89c9c961250c6c4971b32804f9c3c531206` |
| B2C iOS | `_expo/static/js/ios/index-20e00c9331408fcd72d9e2b5a386c744.hbc` | 1573723 | `8430df8e8241c398d4cf447ad2a4cce52cc14825d574f5d5f9bb19cf54af7269` |
| B2C Android | `_expo/static/js/android/index-3f400720ec7f1597a123da7b7d2ff2a8.hbc` | 1583730 | `c877df4ec6bd96e95393d417c1c0a2d761746630fd96bb96164641e2c3cefbe3` |
| Connected web | `_expo/static/js/web/index-b4ec3ddf010b1b87239c248bbb282551.js` | 320520 | `8db0fed8ce9fe3e6663320b265c9cf7aa4ad3b990dcc41cdce848ba9ab3b187a` |
| Connected iOS | `_expo/static/js/ios/index-7a1fcefb6ada090c31f825e5ff4e996f.hbc` | 1574014 | `3cb92992309391c20ca007037ae8ac353d164618650e330f6ac0af7a77237165` |
| Connected Android | `_expo/static/js/android/index-f922acb58ed9d33efcb7b05d3733a1db.hbc` | 1584021 | `762895df32b05db055149a81d5468edbb3698b26f29c5635d41f5e338e1fab44` |

## Bloqueios de distribuição

1. `npm audit`/`npm ci` reportam **24 vulnerabilidades por app: 12 moderadas,
   11 altas e 1 crítica**. Entre dependências transitivas: tar, xmldom, image-size,
   postcss e uuid. O relatório sugere mudanças major de Expo/RN para vários itens.
   Doctor verde não elimina esses achados. Não foi feito audit-fix forçado/override
   indiscriminado. Necessária triagem e atualização/backports revisados antes de
   distribuir, inclusive do tooling que manipula arquivos externos.
2. Homologar contrato público/schema/versionamento antes de ligar catálogo remoto.
3. Para qualquer dado clínico: sessão mobile, consentimentos, autorização/tenant,
   auditoria, persistência real e mensagens de falha sem otimismo enganoso.
4. Para SOS: operação real, responsabilidade e horário de atendimento, entrega com
   recibo verificável e estados distintos registrado/enviado/entregue/atendido.
5. IA própria exige revisão clínica, política de dados, limites, revogação e testes
   de segurança. Nenhuma dessas condições foi substituída por flag local.
6. Build nativo local assinado/instalável, aparelho iOS/Android, storage real,
   acessibilidade, idioma/tamanho de fonte e conectividade permanecem **não testados**.
   Não houve download Xcode/Android SDK, build EAS pago, publicação, commit ou deploy.
