import React, { useState } from "react";
import { StyleSheet, View } from "react-native";
import { Button } from "../components/Button";
import { Card, Divider, ListRow } from "../components/Card";
import { VisibilityPicker } from "../components/domain";
import {
  Alert,
  Badge,
  FeedbackAlert,
  useActionFeedback,
} from "../components/Feedback";
import {
  CheckRow,
  ChipGroup,
  Field,
  Option,
  ScaleInput,
} from "../components/Form";
import {
  EmptyState,
  ProgressBar,
  Screen,
  Section,
  WithData,
} from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import {
  doseSlotsForDay,
  goalProgress,
  habitStatusOn,
  toISODate,
} from "../domain/logic";
import {
  CarePlanDecision,
  DoseStatus,
  GoalStatus,
  HabitStatus,
  TimeWindow,
  Visibility,
} from "../domain/types";
import { useI18n } from "../i18n";
import { RootScreenProps } from "../navigation/types";
import { useNav } from "../navigation/useNav";

// ── Hub ─────────────────────────────────────────────────────────────────────

export function CareHubScreen() {
  const { t } = useI18n();
  const nav = useNav();
  return (
    <Screen testID="screen-care">
      <WithData>
        {(snapshot) => {
          const pendingExercises = snapshot.exercises.filter(
            (item) => item.status === "assigned",
          ).length;
          const planPending =
            snapshot.carePlan !== null && snapshot.carePlan.response === null;
          return (
            <Card>
              <ListRow
                testID="care-plan"
                icon="file"
                title={t("care.plan")}
                subtitle={t("care.plan.subtitle")}
                trailing={
                  planPending ? (
                    <Badge label={t("plan.respond.badge")} tone="warning" />
                  ) : undefined
                }
                onPress={() => nav.navigate("CarePlan")}
              />
              <Divider />
              <ListRow
                testID="care-medications"
                icon="pill"
                title={t("care.medications")}
                subtitle={t("care.medications.subtitle")}
                onPress={() => nav.navigate("Medications")}
              />
              <Divider />
              <ListRow
                testID="care-routine"
                icon="checklist"
                title={t("care.routine")}
                subtitle={t("care.routine.subtitle")}
                onPress={() => nav.navigate("Routine")}
              />
              <Divider />
              <ListRow
                testID="care-exercises"
                icon="activity"
                title={t("care.exercises")}
                subtitle={t("care.exercises.subtitle")}
                trailing={
                  pendingExercises > 0 ? (
                    <Badge label={`${pendingExercises}`} tone="info" />
                  ) : undefined
                }
                onPress={() => nav.navigate("Exercises")}
              />
              <Divider />
              <ListRow
                testID="care-relapse"
                icon="shield"
                title={t("care.relapse")}
                subtitle={t("care.relapse.subtitle")}
                onPress={() => nav.navigate("RelapsePlan")}
              />
              <Divider />
              <ListRow
                testID="care-goals"
                icon="target"
                title={t("care.goals")}
                subtitle={t("care.goals.subtitle")}
                onPress={() => nav.navigate("Goals")}
              />
            </Card>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Plano de cuidado ────────────────────────────────────────────────────────

const DECISIONS: CarePlanDecision[] = [
  "accepted",
  "paused",
  "refused",
  "review_requested",
];

export function CarePlanScreen() {
  const { t, formatDate, formatDateTime } = useI18n();
  const [editing, setEditing] = useState(false);
  const [decision, setDecision] = useState<CarePlanDecision | null>(null);
  const [notes, setNotes] = useState("");
  const { feedback, report } = useActionFeedback();

  return (
    <Screen testID="screen-care-plan">
      <WithData>
        {(snapshot, store) => {
          const plan = snapshot.carePlan;
          if (!plan) return <EmptyState icon="file" text={t("meds.none")} />;
          const showForm = plan.response === null || editing;
          return (
            <>
              <Card>
                <View style={styles.between}>
                  <Text variant="title2" header style={styles.flex}>
                    {plan.title}
                  </Text>
                  <Badge
                    label={t(`plan.status.${plan.status}`)}
                    tone={plan.status === "active" ? "success" : "neutral"}
                  />
                </View>
                <Text variant="bodySm" tone="muted">
                  {t("plan.version", {
                    version: plan.version,
                    date: formatDate(plan.validFrom),
                  })}
                </Text>
                <Text variant="bodySm" tone="muted">
                  {t("plan.by", { name: plan.prescriberName })}
                </Text>
                <Text variant="label">{t("plan.objective")}</Text>
                <Text variant="body">{plan.objective}</Text>
              </Card>

              <Section title={t("plan.actions")}>
                {plan.actions.map((action) => (
                  <Card key={action.id} testID={`plan-action-${action.id}`}>
                    <View style={styles.between}>
                      <Text variant="title3" style={styles.flex}>
                        {action.description}
                      </Text>
                      {action.isMandatory ? (
                        <Badge label={t("plan.mandatory")} tone="info" />
                      ) : null}
                    </View>
                    <Text variant="bodySm" tone="muted">
                      {action.targetFrequency}
                    </Text>
                    {action.guidance ? (
                      <Text variant="bodySm">{action.guidance}</Text>
                    ) : null}
                  </Card>
                ))}
              </Section>

              {plan.contraindications ? (
                <Alert tone="warning" title={t("plan.contraindications")}>
                  {plan.contraindications}
                </Alert>
              ) : null}

              <Section title={t("plan.respond")}>
                <FeedbackAlert feedback={feedback} />
                {plan.response && !editing ? (
                  <Card testID="plan-response">
                    <Text variant="title3">
                      {t("plan.responded", {
                        decision: t(`plan.decision.${plan.response.decision}`),
                      })}
                    </Text>
                    <Text variant="bodySm" tone="muted">
                      {t("plan.responded.at", {
                        date: formatDateTime(plan.response.respondedAt),
                      })}
                    </Text>
                    {plan.response.notes ? (
                      <Text variant="body">{plan.response.notes}</Text>
                    ) : null}
                    <Text variant="bodySm" tone="muted">
                      {t("plan.responded.note")}
                    </Text>
                    <Button
                      label={t("plan.respond")}
                      variant="secondary"
                      size="sm"
                      onPress={() => {
                        setDecision(plan.response?.decision ?? null);
                        setNotes(plan.response?.notes ?? "");
                        setEditing(true);
                      }}
                    />
                  </Card>
                ) : null}
                {showForm ? (
                  <Card>
                    <Text variant="bodySm" tone="muted">
                      {t("plan.respond.hint")}
                    </Text>
                    <ChipGroup
                      testID="plan-decision"
                      value={decision}
                      onChange={setDecision}
                      options={DECISIONS.map((item) => ({
                        value: item,
                        label: t(`plan.decision.${item}`),
                      }))}
                    />
                    <Field
                      label={t("plan.notes")}
                      optionalLabel={t("common.optional")}
                      value={notes}
                      onChangeText={setNotes}
                      multiline
                      maxLength={2000}
                      testID="plan-notes"
                    />
                    <Button
                      label={t("common.send")}
                      disabled={decision === null}
                      testID="plan-submit"
                      onPress={() => {
                        if (decision === null) return;
                        const ok = report(
                          store.run(
                            mutations.respondCarePlan({ decision, notes }),
                          ),
                          "common.done",
                        );
                        if (ok) setEditing(false);
                      }}
                    />
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

// ── Medicações ──────────────────────────────────────────────────────────────

const DOSE_ACTIONS: {
  status: DoseStatus;
  label: "meds.taken" | "meds.late" | "meds.omitted";
}[] = [
  { status: "taken", label: "meds.taken" },
  { status: "late", label: "meds.late" },
  { status: "omitted", label: "meds.omitted" },
];

export function MedicationsScreen() {
  const { t, formatTime, formatDate } = useI18n();
  const { feedback, report } = useActionFeedback();
  return (
    <Screen testID="screen-medications">
      <Alert tone="info">{t("meds.safety")}</Alert>
      <FeedbackAlert feedback={feedback} />
      <WithData>
        {(snapshot, store) => {
          const today = toISODate(store.now);
          const slots = doseSlotsForDay(snapshot, today);
          return (
            <>
              <Section title={t("meds.today")}>
                {slots.length === 0 ? (
                  <EmptyState icon="pill" text={t("meds.none")} />
                ) : null}
                {slots.map((slot) => (
                  <Card key={slot.key} testID={`dose-${slot.key}`}>
                    <View style={styles.between}>
                      <View style={styles.flex}>
                        <Text variant="title3">{slot.medication.name}</Text>
                        <Text variant="bodySm" tone="muted">
                          {slot.medication.presentation} •{" "}
                          {slot.medication.dose}
                        </Text>
                      </View>
                      <Badge
                        label={
                          slot.log
                            ? t(`meds.status.${slot.log.status}`)
                            : `${t("meds.status.pending")} • ${formatTime(slot.scheduledFor)}`
                        }
                        tone={
                          slot.log
                            ? slot.log.status === "taken"
                              ? "success"
                              : slot.log.status === "late"
                                ? "warning"
                                : "danger"
                            : "neutral"
                        }
                      />
                    </View>
                    {slot.log ? (
                      <Button
                        label={t("meds.undo")}
                        variant="ghost"
                        size="sm"
                        testID={`undo-${slot.key}`}
                        onPress={() =>
                          report(
                            store.run(
                              mutations.undoDose({
                                medicationId: slot.medication.id,
                                scheduledFor: slot.scheduledFor,
                              }),
                            ),
                            "common.done",
                          )
                        }
                      />
                    ) : (
                      <View style={styles.actions}>
                        {DOSE_ACTIONS.map((action) => (
                          <Button
                            key={action.status}
                            label={t(action.label)}
                            size="sm"
                            variant={
                              action.status === "taken"
                                ? "primary"
                                : "secondary"
                            }
                            testID={`dose-${action.status}-${slot.key}`}
                            style={styles.action}
                            onPress={() =>
                              report(
                                store.run(
                                  mutations.logDose({
                                    medicationId: slot.medication.id,
                                    scheduledFor: slot.scheduledFor,
                                    status: action.status,
                                  }),
                                ),
                                "common.done",
                              )
                            }
                          />
                        ))}
                      </View>
                    )}
                  </Card>
                ))}
              </Section>

              <Section title={t("care.medications")}>
                {snapshot.medications.map((medication) => (
                  <Card key={medication.id}>
                    <Text variant="title3">{medication.name}</Text>
                    <Text variant="bodySm" tone="muted">
                      {medication.presentation} • {medication.dose} •{" "}
                      {t(`meds.route.${medication.route}`)}
                    </Text>
                    <Text variant="bodySm">
                      {t("meds.schedule")}:{" "}
                      {medication.scheduleTimes.join(", ")} •{" "}
                      {medication.isContinuous || !medication.endDate
                        ? t("meds.continuous")
                        : t("meds.until", {
                            date: formatDate(medication.endDate),
                          })}
                    </Text>
                    {medication.instructions ? (
                      <Text variant="body">{medication.instructions}</Text>
                    ) : null}
                    <Text variant="bodySm" tone="muted">
                      {t("meds.prescribedBy", {
                        name: medication.prescriberName,
                      })}
                    </Text>
                  </Card>
                ))}
              </Section>
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Rotina ──────────────────────────────────────────────────────────────────

const WINDOW_ORDER: TimeWindow[] = [
  "morning",
  "afternoon",
  "evening",
  "night",
  "any_time",
];
const HABIT_STATUSES: HabitStatus[] = [
  "completed",
  "partial",
  "postponed",
  "skipped",
];

export function RoutineScreen() {
  const { t } = useI18n();
  const { feedback, report } = useActionFeedback();
  return (
    <Screen testID="screen-routine">
      <Text variant="bodySm" tone="muted">
        {t("routine.hint")}
      </Text>
      <FeedbackAlert feedback={feedback} />
      <WithData>
        {(snapshot, store) => {
          const today = toISODate(store.now);
          const habits = [...snapshot.habits].sort(
            (a, b) =>
              WINDOW_ORDER.indexOf(a.timeWindow) -
              WINDOW_ORDER.indexOf(b.timeWindow),
          );
          if (habits.length === 0)
            return <EmptyState icon="checklist" text={t("routine.none")} />;
          return (
            <>
              {habits.map((habit) => {
                const current = habitStatusOn(
                  snapshot.habitChecks,
                  habit.id,
                  today,
                );
                const options: Option<HabitStatus>[] = HABIT_STATUSES.map(
                  (status) => ({
                    value: status,
                    label: t(`routine.status.${status}`),
                  }),
                );
                return (
                  <Card key={habit.id} testID={`habit-${habit.id}`}>
                    <Text variant="caption" tone="muted">
                      {t(`routine.window.${habit.timeWindow}`).toUpperCase()}
                      {habit.targetTime ? ` • ${habit.targetTime}` : ""}
                    </Text>
                    <Text variant="title3">{habit.title}</Text>
                    {habit.description ? (
                      <Text variant="bodySm" tone="muted">
                        {habit.description}
                      </Text>
                    ) : null}
                    <ChipGroup
                      testID={`habit-status-${habit.id}`}
                      options={options}
                      value={current}
                      onChange={(status) =>
                        report(
                          store.run(
                            mutations.setHabitStatus({
                              habitId: habit.id,
                              date: today,
                              status: status === current ? null : status,
                            }),
                          ),
                          "common.done",
                        )
                      }
                    />
                  </Card>
                );
              })}
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Exercícios ──────────────────────────────────────────────────────────────

export function ExercisesScreen() {
  const { t, formatDate } = useI18n();
  const nav = useNav();
  return (
    <Screen testID="screen-exercises">
      <WithData>
        {(snapshot) => {
          const pending = snapshot.exercises.filter(
            (item) => item.status === "assigned",
          );
          const done = snapshot.exercises.filter(
            (item) => item.status === "completed",
          );
          if (snapshot.exercises.length === 0) {
            return <EmptyState icon="activity" text={t("exercise.none")} />;
          }
          return (
            <>
              <Section title={t("exercise.pending")}>
                {pending.length === 0 ? (
                  <EmptyState icon="check" text={t("home.exercise.none")} />
                ) : null}
                <Card>
                  {pending.map((item, index) => (
                    <View key={item.id}>
                      {index > 0 ? <Divider /> : null}
                      <ListRow
                        testID={`exercise-${item.id}`}
                        icon="activity"
                        title={item.title}
                        subtitle={`${t("exercise.minutes", { count: item.estimatedMinutes })}${
                          item.dueDate
                            ? ` • ${t("home.exercise.due", { date: formatDate(item.dueDate, "weekday") })}`
                            : ""
                        }`}
                        onPress={() =>
                          nav.navigate("ExerciseDetail", { id: item.id })
                        }
                      />
                    </View>
                  ))}
                </Card>
              </Section>
              {done.length > 0 ? (
                <Section title={t("exercise.completed")}>
                  <Card>
                    {done.map((item, index) => (
                      <View key={item.id}>
                        {index > 0 ? <Divider /> : null}
                        <ListRow
                          testID={`exercise-${item.id}`}
                          icon="check"
                          iconTone="success"
                          title={item.title}
                          subtitle={
                            item.completedAt
                              ? t("exercise.doneAt", {
                                  date: formatDate(item.completedAt),
                                })
                              : undefined
                          }
                          onPress={() =>
                            nav.navigate("ExerciseDetail", { id: item.id })
                          }
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

export function ExerciseDetailScreen({
  route,
}: RootScreenProps<"ExerciseDetail">) {
  const { t, formatDate } = useI18n();
  const { feedback, report } = useActionFeedback();
  const [response, setResponse] = useState("");
  const [visibility, setVisibility] = useState<Visibility | null>(null);
  return (
    <Screen testID="screen-exercise-detail">
      <WithData>
        {(snapshot, store) => {
          const exercise = snapshot.exercises.find(
            (item) => item.id === route.params.id,
          );
          if (!exercise) return <EmptyState text={t("exercise.none")} />;
          const completed = exercise.status === "completed";
          const chosenVisibility = visibility ?? exercise.visibility;
          return (
            <>
              <Card>
                <Text variant="title2" header>
                  {exercise.title}
                </Text>
                <Text variant="bodySm" tone="muted">
                  {exercise.approach} •{" "}
                  {t("exercise.minutes", { count: exercise.estimatedMinutes })}
                </Text>
                <Text variant="bodySm" tone="muted">
                  {t("exercise.frequency", { value: exercise.frequency })} •{" "}
                  {t("exercise.assignedBy", { name: exercise.assignedByName })}
                </Text>
                <Text variant="body">{exercise.instructions}</Text>
              </Card>
              <FeedbackAlert feedback={feedback} />
              <Card>
                <Text variant="title3">{t("exercise.response")}</Text>
                {completed ? (
                  <>
                    <Text variant="body" testID="exercise-response">
                      {exercise.response}
                    </Text>
                    {exercise.completedAt ? (
                      <Text variant="bodySm" tone="muted">
                        {t("exercise.doneAt", {
                          date: formatDate(exercise.completedAt),
                        })}
                      </Text>
                    ) : null}
                  </>
                ) : (
                  <>
                    {exercise.responseFormat === "scale_1_5" ? (
                      <ScaleInput
                        label={t("exercise.response.scale")}
                        value={response ? Number(response) : null}
                        onChange={(value) => setResponse(String(value))}
                        lowLabel={t("checkin.scale.low")}
                        highLabel={t("checkin.scale.high")}
                        testID="exercise-scale"
                      />
                    ) : (
                      <Field
                        label={t("exercise.response.text")}
                        value={response}
                        onChangeText={setResponse}
                        multiline
                        maxLength={4000}
                        testID="exercise-text"
                      />
                    )}
                    <VisibilityPicker
                      label={t("exercise.visibility")}
                      value={chosenVisibility}
                      onChange={setVisibility}
                      testID="exercise-visibility"
                    />
                    <Button
                      label={t("exercise.complete")}
                      disabled={response.trim().length === 0}
                      testID="exercise-submit"
                      onPress={() =>
                        report(
                          store.run(
                            mutations.completeExercise({
                              id: exercise.id,
                              response,
                              visibility: chosenVisibility,
                            }),
                          ),
                          "common.done",
                        )
                      }
                    />
                  </>
                )}
              </Card>
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Plano de prevenção de recaída ───────────────────────────────────────────

export function RelapsePlanScreen() {
  const { t, formatDate } = useI18n();
  return (
    <Screen testID="screen-relapse-plan">
      <WithData>
        {(snapshot) => {
          const plan = snapshot.relapsePlan;
          if (!plan)
            return <EmptyState icon="shield" text={t("relapse.none")} />;
          return (
            <>
              <Card tone="primary">
                <Text variant="title2" header>
                  {plan.title}
                </Text>
                <Text variant="body">{t("relapse.intro")}</Text>
                <Text variant="bodySm" tone="muted">
                  {plan.lastReviewedAt
                    ? t("relapse.reviewed", {
                        date: formatDate(plan.lastReviewedAt),
                      })
                    : t("relapse.never")}
                </Text>
              </Card>
              {plan.sections.map((section) => (
                <Card key={section.id} testID={`relapse-${section.type}`}>
                  <Text variant="title3" header>
                    {t(`relapse.section.${section.type}`)}
                  </Text>
                  <Text variant="body">{section.content}</Text>
                </Card>
              ))}
              <Alert tone="info">{t("relapse.restartNote")}</Alert>
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

// ── Metas ───────────────────────────────────────────────────────────────────

export function GoalsScreen() {
  const { t, formatDate } = useI18n();
  const nav = useNav();
  return (
    <Screen testID="screen-goals">
      <WithData>
        {(snapshot) => {
          const active = snapshot.goals.filter(
            (goal) => goal.status === "active",
          );
          const others = snapshot.goals.filter(
            (goal) => goal.status !== "active",
          );
          if (snapshot.goals.length === 0)
            return <EmptyState icon="target" text={t("goals.none")} />;
          const renderGoal = (goal: (typeof snapshot.goals)[number]) => {
            const progress = goalProgress(goal);
            return (
              <Card
                key={goal.id}
                testID={`goal-${goal.id}`}
                onPress={() => nav.navigate("GoalDetail", { id: goal.id })}
              >
                <View style={styles.between}>
                  <Text variant="title3" style={styles.flex}>
                    {goal.title}
                  </Text>
                  <Badge
                    label={t(`goals.status.${goal.status}`)}
                    tone={
                      goal.status === "completed"
                        ? "success"
                        : goal.status === "active"
                          ? "info"
                          : "neutral"
                    }
                  />
                </View>
                <ProgressBar
                  percent={progress.percent}
                  label={t("goals.steps", {
                    done: progress.done,
                    total: progress.total,
                  })}
                />
                <Text variant="bodySm" tone="muted">
                  {t("goals.steps", {
                    done: progress.done,
                    total: progress.total,
                  })}
                  {goal.dueDate
                    ? ` • ${t("goals.due", { date: formatDate(goal.dueDate) })}`
                    : ""}
                </Text>
              </Card>
            );
          };
          return (
            <>
              <Section title={t("goals.active")}>
                {active.map(renderGoal)}
              </Section>
              {others.length > 0 ? (
                <Section title={t("goals.other")}>
                  {others.map(renderGoal)}
                </Section>
              ) : null}
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

export function GoalDetailScreen({ route }: RootScreenProps<"GoalDetail">) {
  const { t, formatDate } = useI18n();
  const { feedback, report } = useActionFeedback();
  return (
    <Screen testID="screen-goal-detail">
      <WithData>
        {(snapshot, store) => {
          const goal = snapshot.goals.find(
            (item) => item.id === route.params.id,
          );
          if (!goal) return <EmptyState icon="target" text={t("goals.none")} />;
          const progress = goalProgress(goal);
          const setStatus = (status: GoalStatus) =>
            report(
              store.run(mutations.setGoalStatus({ goalId: goal.id, status })),
              "common.done",
            );
          return (
            <>
              <Card>
                <View style={styles.between}>
                  <Text variant="title2" header style={styles.flex}>
                    {goal.title}
                  </Text>
                  <Badge
                    label={t(`goals.status.${goal.status}`)}
                    tone={goal.status === "completed" ? "success" : "info"}
                  />
                </View>
                <Text variant="bodySm" tone="muted">
                  {t(`goals.horizon.${goal.horizon}`)}
                  {goal.dueDate
                    ? ` • ${t("goals.due", { date: formatDate(goal.dueDate) })}`
                    : ""}
                </Text>
                {goal.description ? (
                  <Text variant="body">{goal.description}</Text>
                ) : null}
                <ProgressBar
                  percent={progress.percent}
                  label={t("goals.steps", {
                    done: progress.done,
                    total: progress.total,
                  })}
                />
                <Text variant="bodySm" tone="muted" testID="goal-progress">
                  {t("goals.steps", {
                    done: progress.done,
                    total: progress.total,
                  })}
                </Text>
              </Card>
              <FeedbackAlert feedback={feedback} />
              <Card>
                {[...goal.steps]
                  .sort((a, b) => a.order - b.order)
                  .map((step) => (
                    <CheckRow
                      key={step.id}
                      testID={`step-${step.id}`}
                      label={step.description}
                      checked={step.isDone}
                      onToggle={() =>
                        report(
                          store.run(
                            mutations.toggleGoalStep({
                              goalId: goal.id,
                              stepId: step.id,
                            }),
                          ),
                          "common.done",
                        )
                      }
                    />
                  ))}
              </Card>
              <View style={styles.actions}>
                {goal.status === "active" ? (
                  <>
                    <Button
                      label={t("goals.pause")}
                      variant="secondary"
                      style={styles.action}
                      onPress={() => setStatus("paused")}
                      testID="goal-pause"
                    />
                    <Button
                      label={t("goals.complete")}
                      style={styles.action}
                      onPress={() => setStatus("completed")}
                      testID="goal-complete"
                    />
                  </>
                ) : (
                  <Button
                    label={t("goals.resume")}
                    style={styles.action}
                    onPress={() => setStatus("active")}
                    testID="goal-resume"
                  />
                )}
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
});
