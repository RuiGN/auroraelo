# Aurora Elo — aplicativos mobile

Dois projetos Expo independentes: `b2c` (recuperação e apoio pessoal) e
`connected` (vínculo com o cuidado, ainda **sem integração clínica**).

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
