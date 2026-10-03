import React from "react";
import { StyleSheet, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { useFonts } from "expo-font";
// Importa só os 4 pesos usados (o índice do pacote empacotaria todos os 7).
import { Manrope_500Medium } from "@expo-google-fonts/manrope/500Medium";
import { Manrope_600SemiBold } from "@expo-google-fonts/manrope/600SemiBold";
import { Manrope_700Bold } from "@expo-google-fonts/manrope/700Bold";
import { Manrope_800ExtraBold } from "@expo-google-fonts/manrope/800ExtraBold";
import { DeepLinkProvider } from "./src/api/deepLinks";
import { SessionProvider } from "./src/api/session";
import { BrandMark } from "./src/components/Layout";
import { StoreProvider } from "./src/data/store";
import { I18nProvider } from "./src/i18n";
import { RootNavigator } from "./src/navigation/RootNavigator";
import { ThemeProvider } from "./src/theme/ThemeProvider";
import { lightColors } from "./src/theme/tokens";

export default function App() {
  const [fontsLoaded, fontError] = useFonts({
    Manrope_500Medium,
    Manrope_600SemiBold,
    Manrope_700Bold,
    Manrope_800ExtraBold,
  });
  const ready = fontsLoaded || fontError !== null;

  return (
    <SafeAreaProvider>
      <ThemeProvider fontsLoaded={fontsLoaded}>
        <StatusBar style="light" />
        {ready ? (
          <I18nProvider>
            {/* Sessão (live) → links do app → dados: cada um lê o anterior. */}
            <SessionProvider>
              <DeepLinkProvider>
                <StoreProvider>
                  <RootNavigator />
                </StoreProvider>
              </DeepLinkProvider>
            </SessionProvider>
          </I18nProvider>
        ) : (
          <View style={styles.splash} accessibilityLabel="Aurora Elo">
            <BrandMark size={96} />
          </View>
        )}
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: lightColors.surface,
  },
});
