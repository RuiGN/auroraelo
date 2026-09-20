import React from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Switch,
  Pressable,
} from "react-native";
import { Locale, localeLabels } from "../../../shared/i18n";
import { useLocale } from "../hooks/useLocale";
import { DIGITAL_SUPPORT } from "../../../shared/safety";

export function HomeScreen() {
  const { t, locale, busy, storageError, selectLocale } = useLocale();
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text accessibilityRole="header" style={styles.brand}>
        {t.brand}
      </Text>
      <Text style={styles.subtitle}>{t.b2c}</Text>
      <Text style={styles.status}>{t.local}</Text>
      <Text style={styles.body}>{t.intro}</Text>
      <View style={styles.card}>
        <Text accessibilityRole="header" style={styles.title}>
          {t.areas}
        </Text>
        <Text style={styles.item}>{t.substances}</Text>
        <Text style={styles.item}>{t.gambling}</Text>
        <Text style={styles.item}>{t.gaming}</Text>
        <Text style={styles.body}>{t.areasNote}</Text>
      </View>
      <View style={styles.card}>
        <View
          accessible
          accessibilityRole="image"
          accessibilityLabel={t.avatar}
          style={styles.avatar}
        >
          <Text style={styles.avatarText}>{t.aiBadge}</Text>
        </View>
        <Text accessibilityRole="header" style={styles.title}>
          {t.aiTitle}
        </Text>
        <Text style={styles.body}>{t.aiOff}</Text>
        <Text style={styles.item}>{t.consent}</Text>
        <Switch
          accessibilityLabel={t.consent}
          accessibilityState={{ disabled: true, checked: false }}
          value={DIGITAL_SUPPORT.consent}
          disabled
        />
        <Text style={styles.body}>{t.consentNote}</Text>
        <Pressable
          testID="ai-start"
          accessibilityRole="button"
          accessibilityState={{ disabled: !DIGITAL_SUPPORT.enabled }}
          disabled={!DIGITAL_SUPPORT.enabled}
          style={styles.disabled}
        >
          <Text style={styles.buttonText}>{t.aiStart}</Text>
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text accessibilityRole="header" style={styles.title}>
          {t.help}
        </Text>
        <Text style={styles.item}>{t.nobody}</Text>
        <Text style={styles.body}>{t.helpDetail}</Text>
      </View>
      <View style={styles.card}>
        <Text accessibilityRole="header" style={styles.title}>
          {t.language}
        </Text>
        {Object.entries(localeLabels).map(([code, label]) => (
          <Pressable
            key={code}
            testID={"language-" + code}
            accessibilityRole="button"
            accessibilityState={{ selected: locale === code, disabled: busy }}
            disabled={busy}
            style={styles.languageButton}
            onPress={() => void selectLocale(code as Locale)}
          >
            <Text style={styles.buttonText}>
              {locale === code ? "✓ " : ""}
              {label}
            </Text>
          </Pressable>
        ))}
        {busy && (
          <Text accessibilityLiveRegion="polite" style={styles.body}>
            {t.loading}
          </Text>
        )}
        {storageError && (
          <Text accessibilityRole="alert" style={styles.body}>
            {t.storageError}
          </Text>
        )}
      </View>
      <Text style={styles.body}>{t.privacy}</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f0f7ff" },
  content: {
    padding: 20,
    paddingBottom: 40,
    width: "100%",
    maxWidth: 720,
    alignSelf: "center",
    gap: 16,
  },
  brand: { color: "#0c3c6e", fontSize: 30, fontWeight: "800" },
  subtitle: { color: "#165968", fontSize: 18 },
  status: { color: "#334155", fontSize: 14, fontWeight: "600" },
  card: {
    backgroundColor: "#ffffff",
    borderColor: "#cbd5e1",
    borderWidth: 1,
    borderRadius: 20,
    padding: 20,
    gap: 12,
  },
  title: { color: "#0c3c6e", fontSize: 22, fontWeight: "700" },
  body: { color: "#334155", fontSize: 16, lineHeight: 24 },
  item: { color: "#0c3c6e", fontSize: 17, fontWeight: "600", lineHeight: 25 },
  avatar: {
    backgroundColor: "#0c3c6e",
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: "#ffffff", fontSize: 22, fontWeight: "800" },
  disabled: {
    minHeight: 48,
    padding: 12,
    backgroundColor: "#e2e8f0",
    borderRadius: 12,
    justifyContent: "center",
  },
  languageButton: {
    minHeight: 48,
    padding: 12,
    borderWidth: 1,
    borderColor: "#64748b",
    borderRadius: 12,
    justifyContent: "center",
  },
  buttonText: { color: "#334155", fontSize: 16, fontWeight: "600" },
});
