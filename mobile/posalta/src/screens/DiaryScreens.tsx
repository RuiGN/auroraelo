import React, { useState } from "react";
import { Linking, StyleSheet, View } from "react-native";
import { Button } from "../components/Button";
import { Card, Divider, ListRow } from "../components/Card";
import { VisibilityPicker } from "../components/domain";
import {
  Alert,
  Badge,
  FeedbackAlert,
  useRunAction,
} from "../components/Feedback";
import {
  ChipGroup,
  Field,
  MultiChipGroup,
  Option,
  ScaleInput,
} from "../components/Form";
import { Icon } from "../components/Icon";
import { EmptyState, Screen, Section, WithData } from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import { Store } from "../data/store";
import {
  checkInDoneOn,
  recoveryDays,
  suggestsExtraSupport,
  toISODate,
} from "../domain/logic";
import {
  CHECKIN_QUESTION_KEYS,
  CheckInQuestionKey,
  CheckInScaleAnswers,
  EMOTIONS,
  Emotion,
  Scale5,
  Snapshot,
  Visibility,
} from "../domain/types";
import { useI18n } from "../i18n";
import { RootScreenProps } from "../navigation/types";
import { useNav } from "../navigation/useNav";
import { useTheme } from "../theme/ThemeProvider";
import { dialable } from "./UrgentHelpScreen";

// ── Hub do diário ───────────────────────────────────────────────────────────

export function DiaryHubScreen() {
  const { t, formatDate, formatDateTime } = useI18n();
  const nav = useNav();
  const { colors } = useTheme();
  const { feedback, run } = useRunAction();
  const [confirmRestart, setConfirmRestart] = useState(false);

  return (
    <Screen testID="screen-diary">
      <WithData>
        {(snapshot, store) => {
          const today = toISODate(store.now);
          const done = checkInDoneOn(snapshot, today);
          const sobriety = snapshot.sobriety;
          return (
            <>
              <Card>
                <ListRow
                  testID="diary-checkin"
                  icon="smile"
                  iconTone={done ? "success" : "primary"}
                  title={t("diary.checkIn")}
                  subtitle={t("diary.checkIn.subtitle")}
                  trailing={
                    done ? (
                      <Badge label={t("common.done")} tone="success" />
                    ) : undefined
                  }
                  onPress={() => nav.navigate("CheckIn")}
                />
                <Divider />
                <ListRow
                  testID="diary-write"
                  icon="pen"
                  title={t("diary.write")}
                  subtitle={t("diary.write.subtitle")}
                  onPress={() => nav.navigate("JournalEntryNew")}
                />
                <Divider />
                <ListRow
                  testID="diary-craving"
                  icon="wind"
                  title={t("diary.craving")}
                  subtitle={t("diary.craving.subtitle")}
                  onPress={() => nav.navigate("Craving")}
                />
              </Card>

              <FeedbackAlert feedback={feedback} />

              {snapshot.accessRequests.length > 0 ? (
                <Section title={t("access.title")}>
                  {snapshot.accessRequests.map((request) => (
                    <Card
                      key={request.id}
                      testID={`access-request-${request.id}`}
                    >
                      <Text variant="title3">
                        {t("access.from", { name: request.therapistName })}
                      </Text>
                      <Text variant="bodySm" tone="muted">
                        {t("access.entry", {
                          date: formatDateTime(request.entryCreatedAt),
                        })}
                      </Text>
                      <Text variant="body">{request.purpose}</Text>
                      <Alert tone="info">{t("access.note")}</Alert>
                      <View style={styles.actions}>
                        <Button
                          label={t("access.deny")}
                          variant="secondary"
                          size="sm"
                          style={styles.action}
                          testID={`access-deny-${request.id}`}
                          onPress={() =>
                            run(
                              mutations.respondAccessRequest({
                                id: request.id,
                                approve: false,
                              }),
                              "access.denied",
                            )
                          }
                        />
                        <Button
                          label={t("access.approve")}
                          size="sm"
                          style={styles.action}
                          testID={`access-approve-${request.id}`}
                          onPress={() =>
                            run(
                              mutations.respondAccessRequest({
                                id: request.id,
                                approve: true,
                              }),
                              "access.approved",
                            )
                          }
                        />
                      </View>
                    </Card>
                  ))}
                </Section>
              ) : null}

              {sobriety ? (
                <Section title={t("diary.recovery")}>
                  <Card testID="recovery-card">
                    <View style={styles.between}>
                      <Text variant="title3">{t("recovery.title")}</Text>
                      <Icon name="leaf" size={20} color={colors.success} />
                    </View>
                    {sobriety.hideCounter ? (
                      <Text
                        variant="body"
                        tone="muted"
                        testID="recovery-hidden"
                      >
                        {t("recovery.hidden")}
                      </Text>
                    ) : (
                      <>
                        <Text
                          variant="display"
                          tone="success"
                          testID="recovery-count"
                        >
                          {t("recovery.days", {
                            count: recoveryDays(
                              sobriety.referenceDate,
                              store.now,
                            ),
                          })}
                        </Text>
                        <Text variant="bodySm" tone="muted">
                          {t("recovery.since", {
                            date: formatDate(sobriety.referenceDate),
                          })}
                          {sobriety.restartCount > 0
                            ? ` • ${t("recovery.restart.count", { count: sobriety.restartCount })}`
                            : ""}
                        </Text>
                      </>
                    )}
                    <Text variant="bodySm" tone="muted">
                      {t("recovery.focus", { focus: sobriety.focus })}
                    </Text>
                    {sobriety.motivations ? (
                      <>
                        <Text variant="label">{t("recovery.motivations")}</Text>
                        <Text variant="body">{sobriety.motivations}</Text>
                      </>
                    ) : null}
                    <View style={styles.actions}>
                      <Button
                        label={
                          sobriety.hideCounter
                            ? t("recovery.show")
                            : t("recovery.hide")
                        }
                        variant="secondary"
                        size="sm"
                        style={styles.action}
                        testID="recovery-toggle"
                        onPress={() =>
                          run(
                            mutations.setCounterHidden(!sobriety.hideCounter),
                            "common.done",
                          )
                        }
                      />
                      <Button
                        label={t("recovery.restart")}
                        variant="ghost"
                        size="sm"
                        style={styles.action}
                        testID="recovery-restart"
                        onPress={() => setConfirmRestart(true)}
                      />
                    </View>
                    {confirmRestart ? (
                      <Alert tone="info" title={t("recovery.restart.confirm")}>
                        <Text variant="bodySm">
                          {t("recovery.restart.body")}
                        </Text>
                        <View style={styles.actions}>
                          <Button
                            label={t("common.cancel")}
                            variant="secondary"
                            size="sm"
                            style={styles.action}
                            onPress={() => setConfirmRestart(false)}
                          />
                          <Button
                            label={t("common.confirm")}
                            size="sm"
                            style={styles.action}
                            testID="recovery-restart-confirm"
                            onPress={() => {
                              run(mutations.restartCounter(), "common.done");
                              setConfirmRestart(false);
                            }}
                          />
                        </View>
                      </Alert>
                    ) : null}
                  </Card>
                </Section>
              ) : (
                <Section title={t("diary.recovery")}>
                  <Card testID="recovery-empty">
                    <Text variant="body" tone="muted">
                      {t("recovery.goal.intro")}
                    </Text>
                    <Button
                      label={t("recovery.goal.define")}
                      icon="leaf"
                      variant="secondary"
                      testID="recovery-define"
                      onPress={() => nav.navigate("RecoveryGoal")}
                    />
                  </Card>
                </Section>
              )}

              <Section title={t("diary.entries")}>
                {snapshot.journal.length === 0 ? (
                  <EmptyState icon="pen" text={t("diary.entries.none")} />
                ) : (
                  <Card>
                    {snapshot.journal.slice(0, 6).map((entry, index) => (
                      <View key={entry.id}>
                        {index > 0 ? <Divider /> : null}
                        <ListRow
                          testID={`entry-${entry.id}`}
                          icon="book"
                          title={`${t(`entry.mood.${entry.mood}`)} • ${formatDateTime(entry.createdAt)}`}
                          subtitle={entry.context}
                          onPress={() =>
                            nav.navigate("JournalEntryDetail", { id: entry.id })
                          }
                        />
                      </View>
                    ))}
                  </Card>
                )}
                <View style={styles.privacyNote}>
                  <Icon name="lock" size={16} color={colors.inkMuted} />
                  <Text variant="bodySm" tone="muted" style={styles.flex}>
                    {t("diary.privacy")}
                  </Text>
                </View>
              </Section>
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Check-in diário ─────────────────────────────────────────────────────────

type AnswerDraft = Partial<Record<CheckInQuestionKey, Scale5>>;

export function CheckInScreen() {
  return (
    <Screen testID="screen-checkin">
      <WithData>
        {(snapshot, store) => <CheckInForm snapshot={snapshot} store={store} />}
      </WithData>
    </Screen>
  );
}

interface CheckInFormProps {
  snapshot: Snapshot;
  store: Store;
}

function CheckInForm({ snapshot, store }: CheckInFormProps) {
  const { t } = useI18n();
  const nav = useNav();
  const { feedback, run, pending } = useRunAction();
  const existing = snapshot.checkIns.find(
    (item) => item.date === toISODate(store.now),
  );
  // Pré-preenche com o registro de hoje, se houver (um novo envio o substitui).
  const [answers, setAnswers] = useState<AnswerDraft>(existing?.answers ?? {});
  const [notes, setNotes] = useState(existing?.notes ?? "");
  const [visibility, setVisibility] = useState<Visibility>(
    existing?.visibility ?? "private",
  );
  const [submittedAnswers, setSubmittedAnswers] =
    useState<CheckInScaleAnswers | null>(null);
  const complete = CHECKIN_QUESTION_KEYS.every(
    (key) => answers[key] !== undefined,
  );

  return (
    <>
      <Text variant="body" tone="muted">
        {t("checkin.intro")}
      </Text>
      {existing ? (
        <Alert tone="info">{t("diary.checkIn.doneToday")}</Alert>
      ) : null}
      <Card>
        {CHECKIN_QUESTION_KEYS.map((key) => (
          <ScaleInput
            key={key}
            testID={`q-${key}`}
            label={t(`checkin.q.${key}`)}
            value={answers[key] ?? null}
            onChange={(value) =>
              setAnswers((current) => ({ ...current, [key]: value as Scale5 }))
            }
            lowLabel={t("checkin.scale.low")}
            highLabel={t("checkin.scale.high")}
          />
        ))}
      </Card>
      <Card>
        <Field
          label={t("checkin.notes")}
          optionalLabel={t("common.optional")}
          placeholder={t("checkin.notes.placeholder")}
          value={notes}
          onChangeText={setNotes}
          multiline
          maxLength={2000}
          testID="checkin-notes"
        />
        <VisibilityPicker
          label={t("checkin.visibility")}
          value={visibility}
          onChange={setVisibility}
          testID="checkin-visibility"
        />
      </Card>
      {!complete ? (
        <Text variant="bodySm" tone="muted">
          {t("checkin.missing")}
        </Text>
      ) : null}
      <FeedbackAlert feedback={feedback} />
      {submittedAnswers && suggestsExtraSupport(submittedAnswers) ? (
        <Alert tone="warning" title={t("checkin.support.title")}>
          <Text variant="bodySm">{t("checkin.support.body")}</Text>
          <Button
            label={t("checkin.support.cta")}
            icon="lifebuoy"
            variant="danger"
            size="sm"
            testID="checkin-support-cta"
            onPress={() => nav.navigate("UrgentHelp")}
          />
        </Alert>
      ) : null}
      <Button
        label={t("checkin.submit")}
        disabled={!complete}
        loading={pending}
        testID="checkin-submit"
        onPress={() => {
          if (!complete) return;
          const finalAnswers = answers as CheckInScaleAnswers;
          void run(
            mutations.submitCheckIn({
              answers: finalAnswers,
              notes,
              visibility,
            }),
            "checkin.saved",
          ).then((ok) => setSubmittedAnswers(ok ? finalAnswers : null));
        }}
      />
    </>
  );
}

// ── Novo registro no diário ─────────────────────────────────────────────────

const MOODS: Scale5[] = [1, 2, 3, 4, 5];

export function JournalEntryNewScreen() {
  const { t } = useI18n();
  const { feedback, run, pending } = useRunAction();
  const [mood, setMood] = useState<Scale5 | null>(null);
  const [emotions, setEmotions] = useState<Emotion[]>([]);
  const [intensity, setIntensity] = useState<Scale5 | null>(null);
  const [context, setContext] = useState("");
  const [triggers, setTriggers] = useState("");
  const [reactions, setReactions] = useState("");
  const [strategies, setStrategies] = useState("");
  const [visibility, setVisibility] = useState<Visibility>("private");
  const [showError, setShowError] = useState(false);

  const moodOptions: Option<string>[] = MOODS.map((value) => ({
    value: String(value),
    label: t(`entry.mood.${value}`),
  }));
  const emotionOptions: Option<Emotion>[] = EMOTIONS.map((value) => ({
    value,
    label: t(`entry.emotion.${value}`),
  }));

  return (
    <Screen testID="screen-journal-new">
      <WithData>
        {(_snapshot, store) => (
          <>
            <Card>
              <ChipGroup
                testID="entry-mood"
                label={t("entry.mood")}
                options={moodOptions}
                value={mood === null ? null : String(mood)}
                onChange={(value) => setMood(Number(value) as Scale5)}
              />
              <MultiChipGroup
                testID="entry-emotions"
                label={t("entry.emotions")}
                options={emotionOptions}
                value={emotions}
                onChange={setEmotions}
              />
              <ScaleInput
                testID="entry-intensity"
                label={t("entry.intensity")}
                value={intensity}
                onChange={(value) => setIntensity(value as Scale5)}
                lowLabel={t("checkin.scale.low")}
                highLabel={t("checkin.scale.high")}
              />
            </Card>
            <Card>
              <Field
                testID="entry-context"
                label={t("entry.context")}
                placeholder={t("entry.context.placeholder")}
                value={context}
                onChangeText={setContext}
                required
                multiline
                maxLength={4000}
                error={
                  showError && context.trim().length === 0
                    ? t("entry.context.required")
                    : undefined
                }
              />
              <Field
                testID="entry-triggers"
                label={t("entry.triggers")}
                optionalLabel={t("common.optional")}
                value={triggers}
                onChangeText={setTriggers}
                multiline
                maxLength={2000}
              />
              <Field
                testID="entry-reactions"
                label={t("entry.reactions")}
                optionalLabel={t("common.optional")}
                value={reactions}
                onChangeText={setReactions}
                multiline
                maxLength={2000}
              />
              <Field
                testID="entry-strategies"
                label={t("entry.strategies")}
                optionalLabel={t("common.optional")}
                value={strategies}
                onChangeText={setStrategies}
                multiline
                maxLength={2000}
              />
              <VisibilityPicker
                label={t("entry.visibility")}
                value={visibility}
                onChange={setVisibility}
                testID="entry-visibility"
              />
            </Card>
            <FeedbackAlert feedback={feedback} />
            <Button
              label={t("entry.submit")}
              disabled={mood === null || intensity === null}
              loading={pending}
              testID="entry-submit"
              onPress={() => {
                if (mood === null || intensity === null) return;
                if (context.trim().length === 0) {
                  setShowError(true);
                  return;
                }
                void run(
                  mutations.addJournalEntry({
                    mood,
                    emotions,
                    intensity,
                    context,
                    triggers,
                    reactions,
                    strategies,
                    visibility,
                  }),
                  "entry.saved",
                ).then((ok) => {
                  if (!ok) return;
                  setMood(null);
                  setEmotions([]);
                  setIntensity(null);
                  setContext("");
                  setTriggers("");
                  setReactions("");
                  setStrategies("");
                  setVisibility("private");
                  setShowError(false);
                });
              }}
            />
          </>
        )}
      </WithData>
    </Screen>
  );
}

export function JournalEntryDetailScreen({
  route,
}: RootScreenProps<"JournalEntryDetail">) {
  const { t, formatDateTime } = useI18n();
  return (
    <Screen testID="screen-journal-detail">
      <WithData>
        {(snapshot) => {
          const entry = snapshot.journal.find(
            (item) => item.id === route.params.id,
          );
          if (!entry)
            return <EmptyState icon="pen" text={t("diary.entries.none")} />;
          return (
            <Card>
              <Text variant="title2" header>
                {t(`entry.mood.${entry.mood}`)}
              </Text>
              <Text variant="bodySm" tone="muted">
                {formatDateTime(entry.createdAt)} •{" "}
                {t(`visibility.${entry.visibility}`)}
              </Text>
              {entry.emotions.length > 0 ? (
                <Text variant="label">
                  {entry.emotions
                    .map((emotion) => t(`entry.emotion.${emotion}`))
                    .join(", ")}{" "}
                  — {t("entry.intensity")}: {entry.intensity}
                </Text>
              ) : null}
              <Text variant="label">{t("entry.context")}</Text>
              <Text variant="body">{entry.context}</Text>
              {entry.triggers ? (
                <>
                  <Text variant="label">{t("entry.triggers")}</Text>
                  <Text variant="body">{entry.triggers}</Text>
                </>
              ) : null}
              {entry.reactions ? (
                <>
                  <Text variant="label">{t("entry.reactions")}</Text>
                  <Text variant="body">{entry.reactions}</Text>
                </>
              ) : null}
              {entry.strategies ? (
                <>
                  <Text variant="label">{t("entry.strategies")}</Text>
                  <Text variant="body">{entry.strategies}</Text>
                </>
              ) : null}
            </Card>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Vontade de usar (fissura) ───────────────────────────────────────────────

export function CravingScreen() {
  const { t, formatDateTime } = useI18n();
  const nav = useNav();
  const { feedback, run, pending } = useRunAction();
  const [intensity, setIntensity] = useState<number | null>(null);
  const [context, setContext] = useState("");
  const [strategy, setStrategy] = useState("");

  return (
    <Screen testID="screen-craving">
      <Text variant="body" tone="muted">
        {t("craving.intro")}
      </Text>
      <WithData>
        {(snapshot, store) => {
          const coping = snapshot.relapsePlan?.sections.find(
            (item) => item.type === "coping_strategies",
          );
          const firstContact = snapshot.urgentPlan?.contacts[0];
          return (
            <>
              <Card tone="primary">
                <Text variant="title3" header>
                  {t("craving.suggestions")}
                </Text>
                <Text variant="body">
                  {coping ? coping.content : t("craving.suggestions.none")}
                </Text>
                <View style={styles.actions}>
                  <Button
                    label={t("craving.breathe")}
                    icon="wind"
                    variant="secondary"
                    size="sm"
                    style={styles.action}
                    testID="craving-breathe"
                    onPress={() => nav.navigate("UrgentHelp")}
                  />
                  <Button
                    label={t("craving.callSomeone")}
                    icon="phone"
                    variant="secondary"
                    size="sm"
                    style={styles.action}
                    testID="craving-call"
                    onPress={() => {
                      if (firstContact) {
                        Linking.openURL(
                          `tel:${dialable(firstContact.phone)}`,
                        ).catch(() => nav.navigate("UrgentHelp"));
                      } else {
                        nav.navigate("UrgentHelp");
                      }
                    }}
                  />
                </View>
              </Card>
              <Card>
                <ScaleInput
                  testID="craving-intensity"
                  label={t("craving.intensity")}
                  value={intensity}
                  min={1}
                  max={10}
                  onChange={setIntensity}
                />
                <Field
                  testID="craving-context"
                  label={t("craving.context")}
                  optionalLabel={t("common.optional")}
                  value={context}
                  onChangeText={setContext}
                  multiline
                  maxLength={2000}
                />
                <Field
                  testID="craving-strategy"
                  label={t("craving.strategy")}
                  optionalLabel={t("common.optional")}
                  value={strategy}
                  onChangeText={setStrategy}
                  multiline
                  maxLength={2000}
                />
              </Card>
              <FeedbackAlert feedback={feedback} />
              <Button
                label={t("craving.submit")}
                disabled={intensity === null}
                loading={pending}
                testID="craving-submit"
                onPress={() => {
                  if (intensity === null) return;
                  void run(
                    mutations.addCraving({
                      intensity,
                      triggersContext: context,
                      copingStrategyUsed: strategy,
                    }),
                    "craving.saved",
                  ).then((ok) => {
                    if (!ok) return;
                    setIntensity(null);
                    setContext("");
                    setStrategy("");
                  });
                }}
              />
              {snapshot.cravings.length > 0 ? (
                <Section title={t("craving.history")}>
                  <Card>
                    {snapshot.cravings.slice(0, 5).map((item, index) => (
                      <View key={item.id}>
                        {index > 0 ? <Divider /> : null}
                        <ListRow
                          icon="wind"
                          title={t("craving.level", { value: item.intensity })}
                          subtitle={`${formatDateTime(item.recordedAt)}${item.triggersContext ? `\n${item.triggersContext}` : ""}`}
                        />
                      </View>
                    ))}
                  </Card>
                </Section>
              ) : null}
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
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  actions: { flexDirection: "row", gap: 8 },
  action: { flex: 1 },
  flex: { flex: 1 },
  privacyNote: { flexDirection: "row", gap: 8, alignItems: "flex-start" },
});
