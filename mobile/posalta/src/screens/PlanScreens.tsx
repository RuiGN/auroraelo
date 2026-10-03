import React, { useState } from "react";
import { StyleSheet, View } from "react-native";
import { Button } from "../components/Button";
import { Card, Divider } from "../components/Card";
import { Alert, FeedbackAlert, useRunAction } from "../components/Feedback";
import { CheckRow, ChipGroup, Field } from "../components/Form";
import { Screen, Section, WithData } from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import { addDays, toISODate } from "../domain/logic";
import { RelapseSectionType, Snapshot } from "../domain/types";
import { TranslationKey, useI18n } from "../i18n";
import { useNav } from "../navigation/useNav";

/*
 * Conteúdo pessoal que o paciente edita no app (privado: a equipe não recebe nada ao
 * salvar). Cada tela só monta a mutação; no live ela vira uma chamada à API do
 * paciente (src/data/live/authoring.ts).
 */

const SECTION_TYPES: RelapseSectionType[] = [
  "triggers",
  "early_warning_signs",
  "protective_factors",
  "coping_strategies",
  "safe_environments",
  "support_contacts",
  "professional_resources",
];

// ── Meta de recuperação ─────────────────────────────────────────────────────

type GoalType = "abstinence" | "reduction" | "moderation";
type Since = "today" | "yesterday" | "week" | "month";
const SINCE_DAYS: Record<Since, number> = {
  today: 0,
  yesterday: 1,
  week: 7,
  month: 30,
};

export function RecoveryGoalScreen() {
  const { t } = useI18n();
  const nav = useNav();
  const { feedback, run, pending } = useRunAction();
  const [goalType, setGoalType] = useState<GoalType>("abstinence");
  const [focus, setFocus] = useState("");
  const [motivations, setMotivations] = useState("");
  const [since, setSince] = useState<Since>("today");
  const [hide, setHide] = useState(false);
  return (
    <Screen testID="screen-recovery-goal">
      <WithData>
        {(_snapshot, store) => (
          <>
            <Text variant="body" tone="muted">
              {t("recovery.goal.intro")}
            </Text>
            <Alert tone="info">{t("plans.private")}</Alert>
            <Card>
              <ChipGroup
                testID="goal-type"
                label={t("recovery.goal.type")}
                value={goalType}
                onChange={setGoalType}
                options={(
                  ["abstinence", "reduction", "moderation"] as const
                ).map((value) => ({
                  value,
                  label: t(`recovery.goal.type.${value}`),
                }))}
              />
              <Field
                testID="goal-focus"
                label={t("recovery.goal.focus")}
                help={t("recovery.goal.focus.help")}
                value={focus}
                onChangeText={setFocus}
                maxLength={128}
                required
              />
              <Field
                testID="goal-motivations"
                label={t("recovery.goal.motivations")}
                optionalLabel={t("common.optional")}
                value={motivations}
                onChangeText={setMotivations}
                multiline
                maxLength={2000}
              />
              <ChipGroup
                testID="goal-since"
                label={t("recovery.goal.since")}
                value={since}
                onChange={setSince}
                options={(["today", "yesterday", "week", "month"] as const).map(
                  (value) => ({
                    value,
                    label: t(`recovery.goal.since.${value}`),
                  }),
                )}
              />
              <CheckRow
                testID="goal-hide"
                label={t("recovery.goal.hide")}
                checked={hide}
                onToggle={() => setHide((value) => !value)}
              />
            </Card>
            <FeedbackAlert feedback={feedback} />
            <Button
              label={t("recovery.goal.submit")}
              testID="goal-submit"
              disabled={focus.trim().length === 0}
              loading={pending}
              onPress={() => {
                const referenceDate = addDays(
                  toISODate(store.now),
                  -SINCE_DAYS[since],
                );
                void run(
                  mutations.setupSobriety({
                    goalType,
                    focus,
                    referenceDate,
                    motivations,
                    hideCounter: hide,
                  }),
                  "plans.saved",
                ).then((ok) => {
                  if (ok) nav.goBack();
                });
              }}
            />
          </>
        )}
      </WithData>
    </Screen>
  );
}

// ── Plano de prevenção de recaída ───────────────────────────────────────────

function initialSections(
  snapshot: Snapshot,
): Record<RelapseSectionType, string> {
  const values = Object.fromEntries(
    SECTION_TYPES.map((type) => [type, ""]),
  ) as Record<RelapseSectionType, string>;
  for (const section of snapshot.relapsePlan?.sections ?? []) {
    values[section.type] = section.content;
  }
  return values;
}

export function RelapsePlanEditScreen() {
  const { t } = useI18n();
  const nav = useNav();
  const { feedback, run, pending } = useRunAction();
  const [values, setValues] = useState<Record<
    RelapseSectionType,
    string
  > | null>(null);
  return (
    <Screen testID="screen-relapse-edit">
      <WithData>
        {(snapshot) => {
          const current = values ?? initialSections(snapshot);
          return (
            <>
              <Text variant="body" tone="muted">
                {t("relapse.edit.intro")}
              </Text>
              <Alert tone="info">{t("plans.private")}</Alert>
              {SECTION_TYPES.map((type) => (
                <Card key={type}>
                  <Field
                    testID={`relapse-field-${type}`}
                    label={t(`relapse.section.${type}`)}
                    value={current[type]}
                    onChangeText={(text) =>
                      setValues({ ...current, [type]: text })
                    }
                    multiline
                    maxLength={4000}
                  />
                </Card>
              ))}
              <FeedbackAlert feedback={feedback} />
              <Button
                label={t("plans.save")}
                testID="relapse-save"
                loading={pending}
                onPress={() => {
                  void run(
                    mutations.saveRelapsePlan({
                      title: snapshot.relapsePlan?.title || t("relapse.title"),
                      sections: SECTION_TYPES.map((type) => ({
                        type,
                        title: t(`relapse.section.${type}`),
                        content: current[type],
                      })),
                    }),
                    "plans.saved",
                  ).then((ok) => {
                    if (ok) nav.goBack();
                  });
                }}
              />
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Plano de apoio urgente ──────────────────────────────────────────────────

interface ContactDraft {
  id?: string;
  name: string;
  relationship: string;
  phone: string;
  messageTemplate: string;
}

const EMPTY_CONTACT: ContactDraft = {
  name: "",
  relationship: "",
  phone: "",
  messageTemplate: "",
};

export function UrgentPlanEditScreen() {
  const { t } = useI18n();
  const { feedback, run, pending } = useRunAction();
  const [instructions, setInstructions] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<string | null>(null);
  const [draft, setDraft] = useState<ContactDraft | null>(null);
  return (
    <Screen testID="screen-urgent-edit">
      <WithData>
        {(snapshot) => {
          const plan = snapshot.urgentPlan;
          const instructionsValue =
            instructions ?? plan?.personalInstructions ?? "";
          const strategiesValue =
            strategies ?? (plan?.calmingStrategies ?? []).join("\n");
          const contacts = plan?.contacts ?? [];
          return (
            <>
              <Alert tone="info">{t("urgent.note")}</Alert>
              <FeedbackAlert feedback={feedback} />
              <Card>
                <Field
                  testID="urgent-instructions"
                  label={t("urgent.instructions")}
                  value={instructionsValue}
                  onChangeText={setInstructions}
                  multiline
                  maxLength={2000}
                />
                <Field
                  testID="urgent-strategies"
                  label={t("urgent.strategies")}
                  value={strategiesValue}
                  onChangeText={setStrategies}
                  multiline
                  maxLength={2200}
                />
                <Button
                  label={t("plans.save")}
                  testID="urgent-save"
                  loading={pending}
                  onPress={() => {
                    void run(
                      mutations.saveUrgentPlan({
                        personalInstructions: instructionsValue,
                        calmingStrategies: strategiesValue.split("\n"),
                      }),
                      "plans.saved",
                    );
                  }}
                />
              </Card>

              <Section title={t("urgent.contacts")}>
                <Card>
                  {contacts.map((contact, index) => (
                    <View
                      key={contact.id}
                      testID={`urgent-contact-${contact.id}`}
                    >
                      {index > 0 ? <Divider /> : null}
                      <Text variant="title3">{contact.name}</Text>
                      <Text variant="bodySm" tone="muted">
                        {contact.relationship} • {contact.phone}
                      </Text>
                      <View style={styles.actions}>
                        <Button
                          label={t("urgent.contact.edit")}
                          variant="secondary"
                          size="sm"
                          style={styles.action}
                          testID={`urgent-edit-${contact.id}`}
                          onPress={() =>
                            setDraft({
                              id: contact.id,
                              name: contact.name,
                              relationship: contact.relationship,
                              phone: contact.phone,
                              messageTemplate: contact.messageTemplate,
                            })
                          }
                        />
                        <Button
                          label={t("urgent.contact.remove")}
                          variant="ghost"
                          size="sm"
                          style={styles.action}
                          testID={`urgent-remove-${contact.id}`}
                          onPress={() => {
                            void run(
                              mutations.removeUrgentContact(contact.id),
                              "plans.saved",
                            );
                          }}
                        />
                      </View>
                    </View>
                  ))}
                  {draft === null ? (
                    contacts.length >= 5 ? (
                      <Text variant="bodySm" tone="muted">
                        {t("urgent.contact.limit")}
                      </Text>
                    ) : (
                      <Button
                        label={t("urgent.contact.add")}
                        icon="plus"
                        variant="secondary"
                        testID="urgent-add"
                        onPress={() => setDraft(EMPTY_CONTACT)}
                      />
                    )
                  ) : null}
                </Card>
                {draft ? (
                  <Card testID="urgent-contact-form">
                    <Field
                      testID="contact-name"
                      label={t("urgent.contact.name")}
                      value={draft.name}
                      onChangeText={(name) => setDraft({ ...draft, name })}
                      maxLength={120}
                      required
                    />
                    <Field
                      testID="contact-relationship"
                      label={t("urgent.contact.relationship")}
                      value={draft.relationship}
                      onChangeText={(relationship) =>
                        setDraft({ ...draft, relationship })
                      }
                      maxLength={80}
                      required
                    />
                    <Field
                      testID="contact-phone"
                      label={t("urgent.contact.phone")}
                      value={draft.phone}
                      onChangeText={(phone) => setDraft({ ...draft, phone })}
                      keyboardType="numeric"
                      maxLength={40}
                      required
                    />
                    <Field
                      testID="contact-message"
                      label={t("urgent.contact.message")}
                      value={draft.messageTemplate}
                      onChangeText={(messageTemplate) =>
                        setDraft({ ...draft, messageTemplate })
                      }
                      multiline
                      maxLength={500}
                    />
                    <View style={styles.actions}>
                      <Button
                        label={t("common.cancel")}
                        variant="secondary"
                        size="sm"
                        style={styles.action}
                        onPress={() => setDraft(null)}
                      />
                      <Button
                        label={t("urgent.contact.save")}
                        size="sm"
                        style={styles.action}
                        testID="contact-save"
                        onPress={() => {
                          void run(
                            mutations.saveUrgentContact(draft),
                            "plans.saved",
                          ).then((ok) => {
                            if (ok) setDraft(null);
                          });
                        }}
                      />
                    </View>
                  </Card>
                ) : null}
              </Section>
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Ações de pouca energia ──────────────────────────────────────────────────

export function LowEnergyEditScreen() {
  const { t } = useI18n();
  const nav = useNav();
  const { feedback, run, pending } = useRunAction();
  const [values, setValues] = useState<string[] | null>(null);
  return (
    <Screen testID="screen-lowenergy-edit">
      <WithData>
        {(snapshot) => {
          const current =
            values ??
            [0, 1, 2].map((index) => snapshot.lowEnergy.actions[index] ?? "");
          return (
            <>
              <Text variant="body" tone="muted">
                {t("lowenergy.edit.intro")}
              </Text>
              <Card>
                {current.map((value, index) => (
                  <Field
                    key={index}
                    testID={`lowenergy-action-${index}`}
                    label={t("lowenergy.edit.action" as TranslationKey, {
                      n: index + 1,
                    })}
                    value={value}
                    onChangeText={(text) =>
                      setValues(
                        current.map((item, at) => (at === index ? text : item)),
                      )
                    }
                    maxLength={120}
                  />
                ))}
              </Card>
              <FeedbackAlert feedback={feedback} />
              <Button
                label={t("plans.save")}
                testID="lowenergy-save"
                loading={pending}
                onPress={() => {
                  void run(
                    mutations.setLowEnergyActions(current),
                    "plans.saved",
                  ).then((ok) => {
                    if (ok) nav.goBack();
                  });
                }}
              />
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: "row", gap: 8, marginTop: 8 },
  action: { flex: 1 },
});
