import React from "react";
import { StyleSheet, View } from "react-native";
import { Button } from "../components/Button";
import { Card, Divider, ListRow } from "../components/Card";
import { Badge, FeedbackAlert, useRunAction } from "../components/Feedback";
import { Icon } from "../components/Icon";
import {
  NoDataState,
  ProgressBar,
  Screen,
  Section,
  StaleNotice,
} from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import { useStore } from "../data/store";
import {
  checkInDoneOn,
  doseSlotsForDay,
  doseSummary,
  firstName,
  goalProgress,
  habitSummary,
  nextAppointment,
  partOfDay,
  recoveryDays,
  toISODate,
  daysSince,
} from "../domain/logic";
import { Snapshot } from "../domain/types";
import { useI18n } from "../i18n";
import { useNav } from "../navigation/useNav";
import { useTheme } from "../theme/ThemeProvider";

export function HomeScreen() {
  const store = useStore();
  const nav = useNav();
  const { t } = useI18n();
  return (
    <Screen testID="screen-home">
      {store.snapshot ? (
        <>
          <StaleNotice />
          <HomeContent snapshot={store.snapshot} now={store.now} />
        </>
      ) : (
        <>
          <NoDataState />
          <Button
            label={t("help.title")}
            icon="lifebuoy"
            variant="danger"
            onPress={() => nav.navigate("UrgentHelp")}
            fullWidth
          />
        </>
      )}
    </Screen>
  );
}

interface HomeContentProps {
  snapshot: Snapshot;
  now: Date;
}

function HomeContent({ snapshot, now }: HomeContentProps) {
  const { t, formatDate, relativeDay, formatTime } = useI18n();
  const { colors } = useTheme();
  const nav = useNav();
  const store = useStore();
  const { feedback, run } = useRunAction();
  const today = toISODate(now);

  const slots = doseSlotsForDay(snapshot, today);
  const doses = doseSummary(slots);
  const habits = habitSummary(snapshot.habits, snapshot.habitChecks, today);
  const checkInDone = checkInDoneOn(snapshot, today);
  const pendingExercise = snapshot.exercises
    .filter((item) => item.status === "assigned")
    .sort((a, b) =>
      (a.dueDate ?? "9999").localeCompare(b.dueDate ?? "9999"),
    )[0];
  const appointment = nextAppointment(snapshot, now);
  const focusGoal = snapshot.goals.find((goal) => goal.status === "active");
  const dischargeDate = snapshot.patient.dischargeDate;
  const sinceDischarge = dischargeDate ? daysSince(dischargeDate, now) : null;
  const sobriety = snapshot.sobriety;
  const lowEnergy = snapshot.lowEnergy;

  const greetingKey = `home.greeting.${partOfDay(now)}` as const;

  return (
    <>
      <Card tone="primary" testID="home-greeting">
        <Text variant="title1" header>
          {t(greetingKey, { name: firstName(snapshot.patient.displayName) })}
        </Text>
        {sinceDischarge !== null ? (
          <Text variant="body" tone="muted">
            {sinceDischarge <= 0
              ? t("home.dischargeToday")
              : t("home.sinceDischarge", { count: sinceDischarge })}
          </Text>
        ) : null}
        {sobriety ? (
          <View style={styles.recovery}>
            <Icon name="leaf" size={18} color={colors.success} />
            {sobriety.hideCounter ? (
              <Text variant="label" tone="muted">
                {t("home.recovery.hidden")}
              </Text>
            ) : (
              <Text variant="label" tone="success" testID="recovery-days">
                {t("home.recoveryDays", {
                  count: recoveryDays(sobriety.referenceDate, now),
                })}
              </Text>
            )}
          </View>
        ) : null}
      </Card>

      <FeedbackAlert feedback={feedback} />

      {lowEnergy.active ? (
        <Card tone="warning" testID="low-energy-active">
          <View style={styles.rowGap}>
            <Icon name="battery" size={20} color={colors.warning} />
            <Text variant="title3" header>
              {t("home.lowEnergy.active")}
            </Text>
          </View>
          <Text variant="bodySm">{t("home.lowEnergy.body")}</Text>
          <Text variant="label">{t("home.lowEnergy.actions")}</Text>
          {lowEnergy.actions.map((action) => (
            <View key={action} style={styles.rowGap}>
              <Icon name="check" size={16} color={colors.warning} />
              <Text variant="body" style={styles.flex}>
                {action}
              </Text>
            </View>
          ))}
          <Button
            label={t("home.lowEnergy.deactivate")}
            variant="secondary"
            onPress={() => run(mutations.setLowEnergy(false), "common.done")}
            testID="low-energy-off"
          />
        </Card>
      ) : (
        <Card testID="low-energy-prompt">
          <View style={styles.rowGap}>
            <Icon name="battery" size={20} color={colors.inkMuted} />
            <Text variant="title3" header>
              {t("home.lowEnergy.title")}
            </Text>
          </View>
          <Text variant="bodySm" tone="muted">
            {t("home.lowEnergy.body")}
          </Text>
          <Button
            label={t("home.lowEnergy.activate")}
            variant="secondary"
            size="sm"
            onPress={() => run(mutations.setLowEnergy(true), "common.done")}
            testID="low-energy-on"
          />
          <Button
            label={t("lowenergy.edit.entry")}
            variant="ghost"
            size="sm"
            onPress={() => nav.navigate("LowEnergyEdit")}
            testID="low-energy-edit"
          />
        </Card>
      )}

      <Section title={t("home.today")}>
        <Card>
          <ListRow
            testID="today-checkin"
            icon="pen"
            iconTone={checkInDone ? "success" : "primary"}
            title={
              checkInDone ? t("home.checkIn.done") : t("home.checkIn.todo")
            }
            trailing={
              <Badge
                label={checkInDone ? t("common.done") : t("diary.checkIn")}
                tone={checkInDone ? "success" : "info"}
              />
            }
            onPress={() => nav.navigate("CheckIn")}
          />
          <Divider />
          <ListRow
            testID="today-medications"
            icon="pill"
            title={t("home.medications")}
            subtitle={
              doses.total === 0
                ? t("home.medications.none")
                : t("home.medications.count", {
                    done: doses.done,
                    total: doses.total,
                  })
            }
            onPress={() => nav.navigate("Medications")}
          />
          {!lowEnergy.active ? (
            <>
              <Divider />
              <ListRow
                testID="today-habits"
                icon="checklist"
                title={t("home.habits")}
                subtitle={t("home.habits.count", {
                  done: habits.done,
                  total: habits.total,
                })}
                onPress={() => nav.navigate("Routine")}
              />
              <Divider />
              <ListRow
                testID="today-exercise"
                icon="activity"
                title={
                  pendingExercise ? pendingExercise.title : t("home.exercise")
                }
                subtitle={
                  pendingExercise
                    ? pendingExercise.dueDate
                      ? t("home.exercise.due", {
                          date: formatDate(pendingExercise.dueDate, "weekday"),
                        })
                      : t("home.exercise")
                    : t("home.exercise.none")
                }
                onPress={() => nav.navigate("Exercises")}
              />
              <Divider />
              <ListRow
                testID="today-appointment"
                icon="calendar"
                title={t("home.nextAppointment")}
                subtitle={
                  appointment
                    ? `${relativeDay(appointment.startAt, now)} • ${formatTime(appointment.startAt)} — ${appointment.serviceName}`
                    : t("home.nextAppointment.none")
                }
                onPress={() =>
                  appointment
                    ? nav.navigate("AppointmentDetail", { id: appointment.id })
                    : nav.navigate("Tabs", { screen: "Agenda" })
                }
              />
            </>
          ) : null}
        </Card>
      </Section>

      {!lowEnergy.active ? (
        <>
          <View style={styles.grid}>
            <Button
              label={t("home.quick.craving")}
              icon="wind"
              variant="secondary"
              onPress={() => nav.navigate("Craving")}
              style={styles.gridItem}
              testID="quick-craving"
            />
            <Button
              label={t("home.quick.diary")}
              icon="pen"
              variant="secondary"
              onPress={() => nav.navigate("JournalEntryNew")}
              style={styles.gridItem}
              testID="quick-diary"
            />
          </View>

          {focusGoal ? (
            <Section title={t("home.goalFocus")}>
              <Card
                onPress={() => nav.navigate("GoalDetail", { id: focusGoal.id })}
                testID="home-goal"
              >
                <Text variant="title3">{focusGoal.title}</Text>
                <ProgressBar
                  percent={goalProgress(focusGoal).percent}
                  label={t("goals.steps", {
                    done: goalProgress(focusGoal).done,
                    total: goalProgress(focusGoal).total,
                  })}
                />
                <Text variant="bodySm" tone="muted">
                  {t("goals.steps", {
                    done: goalProgress(focusGoal).done,
                    total: goalProgress(focusGoal).total,
                  })}
                </Text>
              </Card>
            </Section>
          ) : null}
        </>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  recovery: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
  },
  rowGap: { flexDirection: "row", alignItems: "center", gap: 8 },
  flex: { flex: 1 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  gridItem: { flexBasis: "47%", flexGrow: 1 },
});
