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
import { ChipGroup, Field } from "../components/Form";
import { EmptyState, Screen, Section, WithData } from "../components/Layout";
import { Text } from "../components/Text";
import { mutations } from "../data/mutations";
import { Appointment, AppointmentStatus } from "../domain/types";
import { useI18n } from "../i18n";
import { RootScreenProps } from "../navigation/types";
import { useNav } from "../navigation/useNav";

const statusTone: Record<
  AppointmentStatus,
  "success" | "info" | "warning" | "neutral" | "danger"
> = {
  requested: "info",
  confirmed: "success",
  reschedule_requested: "warning",
  canceled: "neutral",
  completed: "neutral",
  no_show: "danger",
};

function isUpcoming(item: Appointment, now: Date): boolean {
  const active =
    item.status === "confirmed" ||
    item.status === "requested" ||
    item.status === "reschedule_requested";
  return active && item.endAt >= now.toISOString();
}

export function AgendaScreen() {
  const { t, formatDateTime } = useI18n();
  const nav = useNav();
  return (
    <Screen testID="screen-agenda">
      <WithData>
        {(snapshot, store) => {
          const upcoming = snapshot.appointments
            .filter((item) => isUpcoming(item, store.now))
            .sort((a, b) => a.startAt.localeCompare(b.startAt));
          const past = snapshot.appointments
            .filter((item) => !isUpcoming(item, store.now))
            .sort((a, b) => b.startAt.localeCompare(a.startAt));
          const renderItem = (item: Appointment, index: number) => (
            <View key={item.id}>
              {index > 0 ? <Divider /> : null}
              <ListRow
                testID={`appointment-${item.id}`}
                icon="calendar"
                title={item.serviceName}
                subtitle={`${formatDateTime(item.startAt)}\n${t("agenda.with", { name: item.professionalName })}`}
                badge={
                  <Badge
                    label={t(`agenda.status.${item.status}`)}
                    tone={statusTone[item.status]}
                  />
                }
                onPress={() =>
                  nav.navigate("AppointmentDetail", { id: item.id })
                }
              />
            </View>
          );
          return (
            <>
              <Button
                label={t("agenda.request")}
                icon="plus"
                onPress={() => nav.navigate("RequestAppointment")}
                testID="agenda-request"
                fullWidth
              />
              <Section title={t("agenda.upcoming")}>
                {upcoming.length === 0 ? (
                  <EmptyState icon="calendar" text={t("agenda.none")} />
                ) : (
                  <Card>{upcoming.map(renderItem)}</Card>
                )}
              </Section>
              {past.length > 0 ? (
                <Section title={t("agenda.past")}>
                  <Card>{past.map(renderItem)}</Card>
                </Section>
              ) : null}
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

export function AppointmentDetailScreen({
  route,
}: RootScreenProps<"AppointmentDetail">) {
  const { t, formatDateTime, formatTime } = useI18n();
  const { feedback, report } = useActionFeedback();
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [reason, setReason] = useState("");
  return (
    <Screen testID="screen-appointment-detail">
      <WithData>
        {(snapshot, store) => {
          const item = snapshot.appointments.find(
            (entry) => entry.id === route.params.id,
          );
          if (!item)
            return <EmptyState icon="calendar" text={t("agenda.none")} />;
          const changeable =
            item.status === "confirmed" || item.status === "requested";
          return (
            <>
              <Card>
                <View style={styles.between}>
                  <Text variant="title2" header style={styles.flex}>
                    {item.serviceName}
                  </Text>
                  <Badge
                    label={t(`agenda.status.${item.status}`)}
                    tone={statusTone[item.status]}
                  />
                </View>
                <Text variant="body">{formatDateTime(item.startAt)}</Text>
                <Text variant="bodySm" tone="muted">
                  {formatTime(item.startAt)} – {formatTime(item.endAt)}
                </Text>
                <Text variant="bodySm" tone="muted">
                  {t("agenda.with", { name: item.professionalName })} •{" "}
                  {t("agenda.at", { unit: item.unitName })}
                </Text>
                {item.cancelReason ? (
                  <Text variant="bodySm">{item.cancelReason}</Text>
                ) : null}
              </Card>
              {item.status === "reschedule_requested" ? (
                <Alert tone="warning">{t("agenda.rescheduleNote")}</Alert>
              ) : null}
              <FeedbackAlert feedback={feedback} />
              {changeable ? (
                <View style={styles.stack}>
                  <Button
                    label={t("agenda.reschedule")}
                    variant="secondary"
                    icon="refresh"
                    testID="appointment-reschedule"
                    onPress={() =>
                      report(
                        store.run(mutations.requestReschedule({ id: item.id })),
                        "common.done",
                      )
                    }
                  />
                  {!confirmCancel ? (
                    <Button
                      label={t("agenda.cancel")}
                      variant="ghost"
                      testID="appointment-cancel"
                      onPress={() => setConfirmCancel(true)}
                    />
                  ) : (
                    <Card>
                      <Text variant="title3">{t("agenda.cancel.confirm")}</Text>
                      <Field
                        label={t("agenda.cancel.reason")}
                        value={reason}
                        onChangeText={setReason}
                        maxLength={255}
                        testID="appointment-cancel-reason"
                      />
                      <View style={styles.actions}>
                        <Button
                          label={t("common.cancel")}
                          variant="secondary"
                          size="sm"
                          style={styles.action}
                          onPress={() => setConfirmCancel(false)}
                        />
                        <Button
                          label={t("agenda.cancel")}
                          variant="danger"
                          size="sm"
                          style={styles.action}
                          testID="appointment-cancel-confirm"
                          onPress={() => {
                            report(
                              store.run(
                                mutations.cancelAppointment({
                                  id: item.id,
                                  reason,
                                }),
                              ),
                              "common.done",
                            );
                            setConfirmCancel(false);
                          }}
                        />
                      </View>
                    </Card>
                  )}
                </View>
              ) : null}
            </>
          );
        }}
      </WithData>
    </Screen>
  );
}

export function RequestAppointmentScreen() {
  const { t, formatDateTime } = useI18n();
  const { feedback, report } = useActionFeedback();
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [slot, setSlot] = useState<string | null>(null);
  return (
    <Screen testID="screen-request-appointment">
      <WithData>
        {(snapshot, store) => {
          const service =
            snapshot.services.find((item) => item.id === serviceId) ?? null;
          return (
            <>
              <Card>
                <ChipGroup
                  testID="request-service"
                  label={t("agenda.request.service")}
                  value={serviceId}
                  onChange={(value) => {
                    setServiceId(value);
                    setSlot(null);
                  }}
                  options={snapshot.services.map((item) => ({
                    value: item.id,
                    label: item.name,
                  }))}
                />
                {service ? (
                  <Text variant="bodySm" tone="muted">
                    {t("agenda.with", { name: service.professionalName })} •{" "}
                    {t("agenda.at", { unit: service.unitName })}
                  </Text>
                ) : null}
              </Card>
              {service ? (
                <Card>
                  {service.freeSlots.length === 0 ? (
                    <Text variant="bodySm" tone="muted">
                      {t("agenda.request.noSlots")}
                    </Text>
                  ) : (
                    <ChipGroup
                      testID="request-slot"
                      label={t("agenda.request.slot")}
                      value={slot}
                      onChange={setSlot}
                      options={service.freeSlots.map((value) => ({
                        value,
                        label: formatDateTime(value),
                      }))}
                    />
                  )}
                </Card>
              ) : null}
              <Alert tone="info">{t("agenda.request.note")}</Alert>
              <FeedbackAlert feedback={feedback} />
              <Button
                label={t("agenda.request.submit")}
                disabled={!serviceId || !slot}
                testID="request-submit"
                onPress={() => {
                  if (!serviceId || !slot) return;
                  const ok = report(
                    store.run(
                      mutations.requestAppointment({ serviceId, slot }),
                    ),
                    "agenda.request.sent",
                  );
                  if (ok) setSlot(null);
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
  between: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 8,
  },
  flex: { flex: 1 },
  stack: { gap: 8 },
  actions: { flexDirection: "row", gap: 8 },
  action: { flex: 1 },
});
