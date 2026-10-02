# Aurora Elo — aplicativos mobile

Três projetos Expo independentes: `b2c` (recuperação e apoio pessoal), `connected`
(vínculo com o cuidado, ainda **sem integração clínica**) e `posalta` (app do
paciente depois da alta; ver [`posalta/README.md`](posalta/README.md)).

## O que funciona localmente

- Interface Aurora Elo para recuperação relacionada a álcool/outras substâncias,
  apostas/jogos de azar e jogos digitais.
- Idiomas `pt-br` (padrão), `en` e `es`, com seletor e persistência **somente do
  idioma** no aparelho. Relatos e prontuários não são traduzidos.
- Mensagens explícitas de indisponibilidade; nenhum SOS, dose, consulta, compra,
  paciente, assinatura, sequência de dias ou sincronização fictícios.
- Avatar identificado como IA, mas **IA desativada**, inclusive offline. Não há
  conversa LLM. Consentimento não é presumido, coletado ou persistido.

## Execução local

Em cada diretório (`mobile/b2c` e `mobile/connected`):

```sh
npm ci
npm run format:check
npm run typecheck
npm test
EXPO_NO_DOTENV=1 npx expo install --check
EXPO_NO_DOTENV=1 npx expo-doctor
npm run export
npm start
```

`export` gera JS web e bytecode Hermes iOS/Android em `dist/`. **Não gera APK,
AAB ou IPA, não valida dispositivo e não publica nada.** Não há configuração EAS.
Os scripts Expo não carregam `.env`. Não inserir segredos em `EXPO_PUBLIC_*`.

## Executar neste Mac (Simulador iOS)

Este Mac é Intel x86_64 e tem o runtime iOS 26.5 instalado no Xcode. Para compilar
e abrir o protótipo no Simulador, sem assinatura e sem aparelho físico:

```sh
chmod +x mobile/scripts/run-mac-simulator.sh   # apenas uma vez
mobile/scripts/run-mac-simulator.sh recuperacao
mobile/scripts/run-mac-simulator.sh clinica
```

O script compila em Release para `iphonesimulator` usando `build/DerivedData-Sim`
(separado do build de dispositivo), gera `ios/` e roda `pod install` se faltarem, e
depois instala e abre o app no simulador indicado. O primeiro build compila os pods
do zero e é demorado (mais de uma hora neste Intel i5); os seguintes são
incrementais. Nada é publicado, nada é assinado e nenhum dado real é usado.

Notas específicas deste Mac (Xcode 26 + Intel):

- O runtime iOS 26.5 já está instalado; não rode `xcodebuild -downloadPlatform iOS`,
  que trava neste ambiente.
- O Xcode 26 não compila o `fmt` 11 do React Native por causa do `consteval`; o
  workaround aplicado é forçar `#define FMT_USE_CONSTEVAL 0` em
  `Pods/fmt/include/fmt/base.h` (diretório gerado; se perde em um novo `pod install`).
- Alguns builds de simulador terminam com `build.db: disk I/O error` depois de gerar
  o `.app` completo; o script detecta o produto válido e continua.
- A instalação é feita com o simulador em modo headless; abra o Simulator.app depois,
  ou use `ABRIR_SIMULADOR=1 mobile/scripts/run-mac-simulator.sh recuperacao`.

## API: infraestrutura preparada, integração bloqueada

`src/services/publicApi.ts` em cada app lê `EXPO_PUBLIC_API_BASE_URL` no bundle:
origem HTTPS explícita, DNS ASCII minúsculo, porta opcional, sem usuário/senha,
path, query ou fragmento. Sem valor, chamadas falham com `configuration`.
Não há endereço padrão/localhost nem autenticação inventada.

O transporte compartilhado é somente GET público, com timeout, status, validação
JSON e erros tipados. **Não é chamado pela UI**: os contratos backend ainda não
foram homologados. Nenhum token é guardado em AsyncStorage; não há sessão mobile.
Não habilitar endpoints clínicos adicionando uma URL. Ver os gates e resultados
reais em [mobile-readiness](../docs/migration/mobile-readiness.md).
