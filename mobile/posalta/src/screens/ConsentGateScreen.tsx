import React from "react";
import { StyleSheet, View } from "react-native";
import { useSession } from "../api/session";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Alert, FeedbackAlert, useRunAction } from "../components/Feedback";
import { Screen } from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import { useStore } from "../data/store";
import { useI18n } from "../i18n";
import { useNav } from "../navigation/useNav";

/**
 * Aceite obrigatório no primeiro acesso (live): documentos vigentes da clínica que o
 * paciente ainda não decidiu. Sem aceitar não há dados do cuidado; a saída é sair. A
 * Ajuda urgente continua no cabeçalho. O servidor guarda cada aceite com a versão.
 */
export function ConsentGateScreen() {
  const { t } = useI18n();
  const nav = useNav();
  const session = useSession();
  const store = useStore();
  const { feedback, run, pending } = useRunAction();
  const pendingDocs = (store.snapshot?.consents ?? []).filter(
    (item) => item.mandatory && item.status === "pending",
  );
  const total = pendingDocs.length;
  const doc = pendingDocs[0];
  return (
    <Screen testID="screen-consent-gate">
      <Text variant="title1" header>
        {t("gate.consent.title")}
      </Text>
      <Text variant="body" tone="muted">
        {t("gate.consent.intro")}
      </Text>
      {doc ? (
        <>
          <Card testID={`gate-consent-${doc.purpose}`}>
            <Text variant="caption" tone="muted">
              {t("gate.consent.progress", { current: 1, total })}
            </Text>
            <Text variant="title2" header>
              {doc.title ?? doc.purpose}
            </Text>
            <Text variant="bodySm" tone="muted">
              {t("gate.consent.version", { version: doc.documentVersion })}
            </Text>
            {doc.content ? (
              <Text variant="body" testID="gate-consent-content">
                {doc.content}
              </Text>
            ) : null}
          </Card>
          {doc.refusalConsequence ? (
            <Alert tone="info">
              {t("gate.consent.refusal", { text: doc.refusalConsequence })}
            </Alert>
          ) : null}
          <FeedbackAlert feedback={feedback} />
          <View style={styles.actions}>
            <Button
              label={t("gate.consent.accept")}
              testID="gate-consent-accept"
              loading={pending}
              onPress={() =>
                run(
                  mutations.setConsent({ id: doc.id, granted: true }),
                  "common.done",
                )
              }
              fullWidth
            />
            <Button
              label={t("gate.consent.signout")}
              testID="gate-consent-signout"
              variant="secondary"
              onPress={() => {
                void session.logout();
              }}
              fullWidth
            />
          </View>
        </>
      ) : null}
      <Button
        label={t("help.title")}
        icon="lifebuoy"
        variant="danger"
        testID="gate-help"
        onPress={() => nav.navigate("UrgentHelp")}
        fullWidth
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { gap: 8 },
});
