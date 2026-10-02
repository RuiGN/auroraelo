import React, { useState } from "react";
import { Linking, StyleSheet, View } from "react-native";
import { BreathingExercise } from "../components/Breathing";
import { Button } from "../components/Button";
import { Card, ListRow } from "../components/Card";
import { Alert } from "../components/Feedback";
import { Screen, Section } from "../components/Layout";
import { Text } from "../components/Text";
import { EMERGENCY_NUMBERS } from "../config";
import { useStore } from "../data/store";
import { useI18n } from "../i18n";

/** Remove espaços, hífens e parênteses; mantém + e dígitos. */
export function dialable(phone: string): string {
  return phone.replace(/[^\d+]/g, "");
}

const GROUNDING_STEPS = [
  "help.grounding.step5",
  "help.grounding.step4",
  "help.grounding.step3",
  "help.grounding.step2",
  "help.grounding.step1",
] as const;

/**
 * Ajuda imediata. Tudo aqui é local e iniciado pela própria pessoa: os números
 * abrem o discador do aparelho e nenhuma informação é enviada à clínica. A tela
 * diz, sem rodeios, que ninguém é avisado e que o app não é serviço de emergência.
 */
export function UrgentHelpScreen() {
  const { t } = useI18n();
  const { snapshot, mode } = useStore();
  const [openFailed, setOpenFailed] = useState(false);

  const open = (url: string) => {
    setOpenFailed(false);
    Linking.openURL(url).catch(() => setOpenFailed(true));
  };

  const numbers = [
    {
      key: "medical",
      number: EMERGENCY_NUMBERS.medical,
      label: t("help.number.medical"),
    },
    {
      key: "emotional",
      number: EMERGENCY_NUMBERS.emotionalSupport,
      label: t("help.number.emotional"),
    },
    {
      key: "fire",
      number: EMERGENCY_NUMBERS.fire,
      label: t("help.number.fire"),
    },
    {
      key: "police",
      number: EMERGENCY_NUMBERS.police,
      label: t("help.number.police"),
    },
  ] as const;

  const plan = snapshot?.urgentPlan ?? null;

  return (
    <Screen testID="screen-urgent-help" banner={false}>
      <Alert tone="warning">
        <Text variant="bodySm">{t("help.disclaimer")}</Text>
        <Text variant="label" testID="help-no-one-notified">
          {t("help.noOneNotified")}
        </Text>
      </Alert>

      {mode === "preview" ? (
        <Alert tone="info">{t("help.preview.note")}</Alert>
      ) : null}

      {openFailed ? (
        <Alert tone="danger" live>
          {t("help.openFailed")}
        </Alert>
      ) : null}

      <Section title={t("help.emergency")}>
        {numbers.map((item) => (
          <Button
            key={item.key}
            testID={`call-${item.number}`}
            label={`${item.label} — ${item.number}`}
            accessibilityLabel={t("help.number.call", {
              label: item.label,
              number: item.number,
            })}
            icon="phone"
            variant={item.key === "medical" ? "danger" : "secondary"}
            onPress={() => open(`tel:${item.number}`)}
            fullWidth
          />
        ))}
      </Section>

      <Section title={t("help.people")}>
        {plan && plan.contacts.length > 0 ? (
          plan.contacts.map((contact) => (
            <Card key={contact.id} testID={`urgent-contact-${contact.id}`}>
              <ListRow
                icon="heart"
                title={contact.name}
                subtitle={contact.relationship}
              />
              <View style={styles.actions}>
                <Button
                  label={t("common.call")}
                  icon="phone"
                  size="sm"
                  onPress={() => open(`tel:${dialable(contact.phone)}`)}
                  style={styles.action}
                />
                <Button
                  label={t("help.people.sms")}
                  icon="message"
                  size="sm"
                  variant="secondary"
                  onPress={() =>
                    open(
                      `sms:${dialable(contact.phone)}?body=${encodeURIComponent(contact.messageTemplate)}`,
                    )
                  }
                  style={styles.action}
                />
              </View>
            </Card>
          ))
        ) : (
          <Text variant="bodySm" tone="muted">
            {t("help.people.none")}
          </Text>
        )}
      </Section>

      <Section title={t("help.breathing.title")}>
        <Card>
          <BreathingExercise />
        </Card>
      </Section>

      <Section title={t("help.grounding.title")}>
        <Card>
          {GROUNDING_STEPS.map((key, index) => (
            <View key={key} style={styles.step}>
              <Text variant="title3" tone="primary" style={styles.stepNumber}>
                {5 - index}
              </Text>
              <Text variant="body" style={styles.stepText}>
                {t(key)}
              </Text>
            </View>
          ))}
          <Text variant="bodySm" tone="muted">
            {t("help.grounding.note")}
          </Text>
        </Card>
      </Section>

      {plan ? (
        <Section title={t("help.plan")}>
          <Card testID="urgent-plan">
            {plan.personalInstructions ? (
              <Text variant="body">{plan.personalInstructions}</Text>
            ) : null}
            {plan.calmingStrategies.length > 0 ? (
              <>
                <Text variant="label">{t("help.calm")}</Text>
                {plan.calmingStrategies.map((strategy) => (
                  <Text key={strategy} variant="body">
                    • {strategy}
                  </Text>
                ))}
              </>
            ) : null}
          </Card>
        </Section>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: "row", gap: 8 },
  action: { flex: 1 },
  step: { flexDirection: "row", alignItems: "center", gap: 12 },
  stepNumber: { width: 24, textAlign: "center" },
  stepText: { flex: 1 },
});
