import React from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Icon } from "../components/Icon";
import { Text } from "../components/Text";
import { useStore } from "../data/store";
import { firstName } from "../domain/logic";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import { RootStackParamList } from "./types";

interface HeaderActionsProps {
  showHelp?: boolean;
  showProfile?: boolean;
}

/**
 * Ações do cabeçalho: “Ajuda” (sempre disponível, funciona sem conexão) e perfil.
 * O botão de ajuda abre orientações locais; não envia nenhum alerta.
 */
export function HeaderActions({
  showHelp = true,
  showProfile = true,
}: HeaderActionsProps) {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { colors } = useTheme();
  const { t } = useI18n();
  const { snapshot, mode } = useStore();
  const initial = snapshot
    ? firstName(snapshot.patient.displayName).charAt(0).toUpperCase()
    : "";
  return (
    <View style={styles.row}>
      {mode === "preview" ? (
        <View
          testID="header-demo"
          accessibilityLabel={t("mode.preview.banner")}
          style={[styles.demo, { backgroundColor: colors.warningSoft }]}
        >
          <Text variant="caption" tone="warning" style={styles.demoText}>
            DEMO
          </Text>
        </View>
      ) : null}
      {showHelp ? (
        <Pressable
          testID="header-help"
          accessibilityRole="button"
          accessibilityLabel={t("help.title")}
          hitSlop={{ top: 6, bottom: 6, left: 4, right: 4 }}
          onPress={() => navigation.navigate("UrgentHelp")}
          style={[styles.help, { backgroundColor: colors.danger }]}
        >
          <Icon name="lifebuoy" size={16} color={colors.onDanger} />
          <Text variant="label" tone="onDanger">
            {t("nav.help")}
          </Text>
        </Pressable>
      ) : null}
      {showProfile ? (
        <Pressable
          testID="header-profile"
          accessibilityRole="button"
          accessibilityLabel={t("nav.profile")}
          hitSlop={{ top: 2, bottom: 2, left: 2, right: 2 }}
          onPress={() => navigation.navigate("Profile")}
          style={[
            styles.avatar,
            { backgroundColor: colors.navBgHover, borderColor: colors.navLine },
          ]}
        >
          {initial ? (
            <Text variant="label" tone="nav">
              {initial}
            </Text>
          ) : (
            <Icon name="patient" size={18} color={colors.navInk} />
          )}
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 8, paddingRight: 4 },
  help: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    minHeight: 36,
    paddingHorizontal: 12,
    borderRadius: radius.full,
  },
  demo: {
    paddingHorizontal: 8,
    height: 24,
    borderRadius: radius.full,
    justifyContent: "center",
  },
  demoText: { letterSpacing: 0.4 },
  close: {
    width: 44,
    height: 44,
    borderRadius: radius.full,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 8,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: radius.full,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});

/** Primeira tela de cada situação: abas, entrada, sem configuração, abrindo a conta. */
type HomeRoute = "Tabs" | "SignIn" | "ConfigMissing" | "Restoring";

function isHomeRoute(name: string): name is HomeRoute {
  return (
    name === "Tabs" ||
    name === "SignIn" ||
    name === "ConfigMissing" ||
    name === "Restoring"
  );
}

/**
 * Fechar a ajuda urgente. No iOS o modal também fecha ao arrastar, mas um botão
 * visível é necessário (acessibilidade e quem abriu a tela por link na web).
 */
export function CloseButton() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { colors } = useTheme();
  const { t } = useI18n();
  return (
    <Pressable
      testID="help-close"
      accessibilityRole="button"
      accessibilityLabel={t("common.close")}
      hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}
      onPress={() => {
        if (navigation.canGoBack()) {
          navigation.goBack();
          return;
        }
        // Aberta por link ou sem tela abaixo: volta para a primeira tela do app, que
        // é a de entrada quando não há sessão (a Ajuda urgente não depende de login).
        const home = navigation
          .getState()
          .routeNames.find((name): name is HomeRoute => isHomeRoute(name));
        navigation.navigate(home ?? "Tabs");
      }}
      style={[styles.close, { borderColor: colors.navLine }]}
    >
      <Icon name="close" size={20} color={colors.navInk} />
    </Pressable>
  );
}
