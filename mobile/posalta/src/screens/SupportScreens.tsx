import React, { useState } from "react";
import { StyleSheet, View } from "react-native";
import { Button } from "../components/Button";
import { Card, Divider, ListRow } from "../components/Card";
import {
  Alert,
  Badge,
  FeedbackAlert,
  useActionFeedback,
} from "../components/Feedback";
import { CheckRow } from "../components/Form";
import { Icon, IconName } from "../components/Icon";
import { EmptyState, Screen, Section, WithData } from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import { ContentKind, SupportScope } from "../domain/types";
import { useI18n } from "../i18n";
import { RootScreenProps } from "../navigation/types";
import { useNav } from "../navigation/useNav";
import { useTheme } from "../theme/ThemeProvider";

// ── Hub ─────────────────────────────────────────────────────────────────────

export function SupportHubScreen() {
  const { t } = useI18n();
  const nav = useNav();
  return (
    <Screen testID="screen-support">
      <WithData>
        {(snapshot) => {
          const recommended = snapshot.content.filter(
            (item) => item.recommendedByName && !item.read,
          ).length;
          return (
            <Card>
              <ListRow
                testID="support-network"
                icon="heart"
                title={t("support.network")}
                subtitle={t("support.network.subtitle")}
                onPress={() => nav.navigate("Network")}
              />
              <Divider />
              <ListRow
                testID="support-learn"
                icon="book"
                title={t("support.learn")}
                subtitle={t("support.learn.subtitle")}
                trailing={
                  recommended > 0 ? (
                    <Badge label={`${recommended}`} tone="info" />
                  ) : undefined
                }
                onPress={() => nav.navigate("Learn")}
              />
            </Card>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Rede de apoio ───────────────────────────────────────────────────────────

const SCOPES: SupportScope[] = [
  "view_goals",
  "view_routine",
  "view_appointments",
  "receive_alerts",
];

export function NetworkScreen() {
  const { t } = useI18n();
  const { feedback, report } = useActionFeedback();
  const [confirming, setConfirming] = useState<string | null>(null);
  return (
    <Screen testID="screen-network">
      <Text variant="body" tone="muted">
        {t("network.intro")}
      </Text>
      <Alert tone="info">{t("network.diary")}</Alert>
      <FeedbackAlert feedback={feedback} />
      <WithData>
        {(snapshot, store) =>
          snapshot.supportNetwork.length === 0 ? (
            <EmptyState icon="heart" text={t("network.none")} />
          ) : (
            <>
              {snapshot.supportNetwork.map((person) => (
                <Card key={person.id} testID={`network-${person.id}`}>
                  <View style={styles.between}>
                    <View style={styles.flex}>
                      <Text variant="title3">{person.name}</Text>
                      <Text variant="bodySm" tone="muted">
                        {person.relationship}
                      </Text>
                    </View>
                    {!person.active ? (
                      <Badge label={t("network.revoked")} tone="neutral" />
                    ) : null}
                  </View>
                  {person.active ? (
                    <>
                      {SCOPES.map((scope) => (
                        <CheckRow
                          key={scope}
                          testID={`scope-${person.id}-${scope}`}
                          label={t(`network.scope.${scope}`)}
                          checked={person.scopes.includes(scope)}
                          onToggle={() =>
                            report(
                              store.run(
                                mutations.toggleSupportScope({
                                  id: person.id,
                                  scope,
                                }),
                              ),
                              "common.done",
                            )
                          }
                        />
                      ))}
                      {confirming === person.id ? (
                        <Alert
                          tone="warning"
                          title={t("network.revoke.confirm", {
                            name: person.name,
                          })}
                        >
                          <View style={styles.actions}>
                            <Button
                              label={t("common.cancel")}
                              variant="secondary"
                              size="sm"
                              style={styles.action}
                              onPress={() => setConfirming(null)}
                            />
                            <Button
                              label={t("network.revoke")}
                              variant="danger"
                              size="sm"
                              style={styles.action}
                              testID={`revoke-confirm-${person.id}`}
                              onPress={() => {
                                report(
                                  store.run(mutations.revokeSupport(person.id)),
                                  "common.done",
                                );
                                setConfirming(null);
                              }}
                            />
                          </View>
                        </Alert>
                      ) : (
                        <Button
                          label={t("network.revoke")}
                          variant="ghost"
                          size="sm"
                          testID={`revoke-${person.id}`}
                          onPress={() => setConfirming(person.id)}
                        />
                      )}
                    </>
                  ) : null}
                </Card>
              ))}
            </>
          )
        }
      </WithData>
    </Screen>
  );
}

// ── Conteúdo ────────────────────────────────────────────────────────────────

const kindIcon: Record<ContentKind, IconName> = {
  article: "file",
  video: "play",
  audio: "headphones",
  exercise: "activity",
};

export function LearnScreen() {
  const { t } = useI18n();
  const nav = useNav();
  return (
    <Screen testID="screen-learn">
      <Alert tone="info">{t("learn.notice")}</Alert>
      <WithData>
        {(snapshot) => {
          const recommended = snapshot.content.filter(
            (item) => item.recommendedByName,
          );
          const library = snapshot.content.filter(
            (item) => !item.recommendedByName,
          );
          if (snapshot.content.length === 0)
            return <EmptyState icon="book" text={t("learn.none")} />;
          const row = (
            item: (typeof snapshot.content)[number],
            index: number,
          ) => (
            <View key={item.id}>
              {index > 0 ? <Divider /> : null}
              <ListRow
                testID={`content-${item.id}`}
                icon={kindIcon[item.kind]}
                iconTone={item.read ? "success" : "primary"}
                title={item.title}
                subtitle={`${t(`learn.kind.${item.kind}`)} • ${t("learn.minutes", { count: item.estimatedMinutes })}${
                  item.recommendedByName
                    ? `\n${t("learn.recommendedBy", { name: item.recommendedByName })}`
                    : ""
                }`}
                trailing={
                  item.read ? (
                    <Badge label={t("learn.read")} tone="success" />
                  ) : undefined
                }
                onPress={() => nav.navigate("ContentDetail", { id: item.id })}
              />
            </View>
          );
          return (
            <>
              {recommended.length > 0 ? (
                <Section title={t("learn.recommended")}>
                  <Card>{recommended.map(row)}</Card>
                </Section>
              ) : null}
              {library.length > 0 ? (
                <Section title={t("learn.all")}>
                  <Card>{library.map(row)}</Card>
                </Section>
              ) : null}
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

export function ContentDetailScreen({
  route,
}: RootScreenProps<"ContentDetail">) {
  const { t } = useI18n();
  const { colors } = useTheme();
  const { feedback, report } = useActionFeedback();
  return (
    <Screen testID="screen-content-detail">
      <WithData>
        {(snapshot, store) => {
          const item = snapshot.content.find(
            (entry) => entry.id === route.params.id,
          );
          if (!item) return <EmptyState icon="book" text={t("learn.none")} />;
          return (
            <>
              <Card>
                <View style={styles.between}>
                  <Badge label={t(`learn.kind.${item.kind}`)} tone="info" />
                  <Text variant="bodySm" tone="muted">
                    {t("learn.minutes", { count: item.estimatedMinutes })}
                  </Text>
                </View>
                <Text variant="title1" header>
                  {item.title}
                </Text>
                {item.recommendedByName ? (
                  <Text variant="bodySm" tone="muted">
                    {t("learn.recommendedBy", { name: item.recommendedByName })}
                    {item.recommendationObjective
                      ? ` — ${t("learn.objective", { objective: item.recommendationObjective })}`
                      : ""}
                  </Text>
                ) : null}
                <Text variant="body">{item.body}</Text>
                {item.contraindications ? (
                  <Alert tone="warning" title={t("learn.care")}>
                    {item.contraindications}
                  </Alert>
                ) : null}
                <View style={styles.source}>
                  <Icon name="info" size={14} color={colors.inkMuted} />
                  <Text variant="bodySm" tone="muted" style={styles.flex}>
                    {t("learn.source", { source: item.sourceReference || "—" })}
                  </Text>
                </View>
              </Card>
              <FeedbackAlert feedback={feedback} />
              <View style={styles.actions}>
                <Button
                  label={
                    item.favorite ? t("learn.unfavorite") : t("learn.favorite")
                  }
                  icon="star"
                  variant="secondary"
                  size="sm"
                  style={styles.action}
                  testID="content-favorite"
                  onPress={() =>
                    report(
                      store.run(
                        mutations.toggleContent({
                          id: item.id,
                          flag: "favorite",
                        }),
                      ),
                      "common.done",
                    )
                  }
                />
                <Button
                  label={item.read ? t("learn.read") : t("learn.markRead")}
                  icon="check"
                  size="sm"
                  style={styles.action}
                  testID="content-read"
                  onPress={() =>
                    report(
                      store.run(
                        mutations.toggleContent({ id: item.id, flag: "read" }),
                      ),
                      "common.done",
                    )
                  }
                />
              </View>
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

const styles = StyleSheet.create({
  between: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 8,
  },
  flex: { flex: 1 },
  actions: { flexDirection: "row", gap: 8 },
  action: { flex: 1 },
  update: { gap: 2, paddingLeft: 8 },
  thread: { gap: 8 },
  bubble: {
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    gap: 4,
    maxWidth: "90%",
  },
  mine: { alignSelf: "flex-end" },
  theirs: { alignSelf: "flex-start" },
  source: { flexDirection: "row", gap: 6, alignItems: "flex-start" },
});
