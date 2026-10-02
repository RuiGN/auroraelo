#!/usr/bin/env bash
# Executa os protótipos Aurora Elo no Simulador iOS deste Mac (Intel x86_64).
#
# Uso:
#   mobile/scripts/run-mac-simulator.sh recuperacao [nome-do-simulador]
#   mobile/scripts/run-mac-simulator.sh clinica     [nome-do-simulador]
#
# O que este script faz:
#   1. gera ios/ com `expo prebuild` (na primeira vez) e roda `pod install` se preciso;
#   2. compila em Release para iphonesimulator, sem assinatura, em build/DerivedData-Sim;
#   3. sobe o simulador, instala e abre o app.
#
# Notas deste Mac (detalhes em mobile/README.md):
# - O runtime iOS 26.5 já está instalado no Xcode; não baixar plataforma de novo.
# - O Xcode 26 falha ao compilar o fmt 11 do React Native sem o workaround
#   FMT_USE_CONSTEVAL=0 em Pods/fmt/include/fmt/base.h.
# - Se o xcodebuild terminar com "build.db: disk I/O error" mas o .app estiver
#   completo (binário + main.jsbundle + hermes.framework), o script segue e instala.
# - A instalação é feita sem a janela do Simulator.app; abra-a depois, se quiser
#   (variável ABRIR_SIMULADOR=1 abre automaticamente ao final).
#
# Requisitos: Xcode, Node/npm, CocoaPods e o runtime iOS instalado.

set -euo pipefail

ALVO="${1:-recuperacao}"
SIMULADOR="${2:-iPhone 17}"

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$ALVO" in
  recuperacao|recuperação|b2c)
    PROJETO="$RAIZ/b2c"
    ESQUEMA="AuroraEloRecuperao"
    APP="AuroraEloRecuperao.app"
    BUNDLE="br.med.auroraelo.recuperacao"
    ;;
  clinica|clínica|connected)
    PROJETO="$RAIZ/connected"
    ESQUEMA="AuroraEloClnica"
    APP="AuroraEloClnica.app"
    BUNDLE="br.med.auroraelo.clinica"
    ;;
  *)
    echo "Alvo inválido: $ALVO" >&2
    echo "Use: recuperacao | clinica" >&2
    exit 2
    ;;
esac

# 1. Projeto nativo e pods
if [ ! -d "$PROJETO/ios" ]; then
  echo "==> Gerando ios/ com expo prebuild..."
  (cd "$PROJETO" && EXPO_NO_DOTENV=1 CI=1 npx expo prebuild --platform ios --no-install)
fi
if [ ! -d "$PROJETO/ios/Pods" ]; then
  echo "==> Rodando pod install..."
  (cd "$PROJETO/ios" && pod install)
fi

# 2. Build Release para o simulador
cd "$PROJETO/ios"
echo "==> Compilando $ESQUEMA para o simulador ($SIMULADOR)..."
if ! EXPO_NO_DOTENV=1 xcodebuild \
  -workspace "$ESQUEMA.xcworkspace" \
  -scheme "$ESQUEMA" \
  -configuration Release \
  -sdk iphonesimulator \
  -destination "platform=iOS Simulator,name=$SIMULADOR" \
  -derivedDataPath build/DerivedData-Sim \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY="" \
  -quiet build; then
  echo "AVISO: xcodebuild terminou com erro; verificando se o produto ficou completo..." >&2
fi

APP_PATH="build/DerivedData-Sim/Build/Products/Release-iphonesimulator/$APP"
if [ ! -d "$APP_PATH" ] || [ ! -f "$APP_PATH/main.jsbundle" ]; then
  echo "App ausente ou incompleto em $APP_PATH. Rode o script de novo." >&2
  exit 1
fi

# 3. Simulador: UDID pelo nome, boot e instalação
UDID="$(xcrun simctl list devices available \
  | sed -n "s/^ *$SIMULADOR (\([0-9A-F-]\{36\}\)) (.*/\1/p" | head -1)"
if [ -z "$UDID" ]; then
  echo "Simulador '$SIMULADOR' não encontrado. Veja: xcrun simctl list devices available" >&2
  exit 1
fi

echo "==> Preparando o simulador $SIMULADOR ($UDID)..."
xcrun simctl bootstatus "$UDID" -b

if ! xcrun simctl install "$UDID" "$APP_PATH"; then
  echo "AVISO: instalação falhou; reiniciando o simulador e tentando novamente..." >&2
  xcrun simctl shutdown "$UDID" 2>/dev/null || true
  xcrun simctl bootstatus "$UDID" -b
  xcrun simctl install "$UDID" "$APP_PATH"
fi

echo "==> Abrindo $APP..."
xcrun simctl launch "$UDID" "$BUNDLE"
if [ "${ABRIR_SIMULADOR:-0}" = "1" ]; then
  open -a Simulator
fi

echo "Pronto: $APP em execução no simulador $SIMULADOR ($BUNDLE)."
