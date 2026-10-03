/**
 * Agenda no modo live: consultas, horários livres e metas de agendamento
 * (api/mobile_agenda_api.py).
 *
 * Uma opção de agendamento do servidor é uma combinação serviço × profissional ×
 * unidade; no app ela vira um `BookableService` cujo `id` é essas três partes unidas
 * por "_" (UUIDs só têm "-"), para a ação saber o que pedir sem estado escondido.
 */
import { id, instant, int, list, oneOf, record, text } from "../../api/parse";
import {
  Appointment,
  AppointmentStatus,
  BookableService,
} from "../../domain/types";
import type { LiveActionRegistry } from "./actions";
import type { LoaderEntry } from "./registry";

const STATUSES: readonly AppointmentStatus[] = [
  "requested",
  "confirmed",
  "reschedule_requested",
  "canceled",
  "completed",
  "no_show",
];

/** Gera a chave do app (e a desfaz): `serviço_profissional_unidade`. */
export function optionId(
  serviceId: string,
  professionalId: string,
  unitId: string,
): string {
  return `${serviceId}_${professionalId}_${unitId}`;
}

export function splitOptionId(
  value: string,
): { serviceId: string; professionalId: string; unitId: string } | null {
  const parts = value.split("_");
  if (parts.length !== 3 || parts.some((part) => part.length === 0)) {
    return null;
  }
  return { serviceId: parts[0], professionalId: parts[1], unitId: parts[2] };
}

function parseAppointment(value: unknown): Appointment {
  const source = record(value);
  return {
    id: id(source.id),
    serviceName: text(source.service_name, 300),
    professionalName: text(source.professional_name, 300),
    unitName: text(source.unit_name, 300),
    startAt: instant(source.start_at),
    endAt: instant(source.end_at),
    status: oneOf(source.status, STATUSES, "requested"),
    cancelReason: text(source.cancel_reason, 1000),
  };
}

function parseOption(value: unknown): BookableService {
  const source = record(value);
  return {
    id: optionId(
      id(source.service_id),
      id(source.professional_id),
      id(source.unit_id),
    ),
    name: text(source.service_name, 300),
    durationMinutes: int(source.duration_minutes),
    professionalName: text(source.professional_name, 300),
    unitName: text(source.unit_name, 300),
    freeSlots: list(source.free_slots, instant, 500),
  };
}

export const appointmentsLoader: LoaderEntry = {
  slices: ["appointments"],
  load: async (api) => ({
    appointments: await api.get("/mobile/appointments/", {
      parse: (raw) => list(raw, parseAppointment, 500),
    }),
  }),
};

export const bookingLoader: LoaderEntry = {
  slices: ["services"],
  load: async (api) => ({
    services: await api.get("/mobile/booking/options/", {
      parse: (raw) => list(raw, parseOption, 100),
    }),
  }),
};

export const agendaLoaders: readonly LoaderEntry[] = [
  appointmentsLoader,
  bookingLoader,
];

/**
 * Chave de idempotência de UMA tentativa. O toque duplo já é barrado pelo motor (a
 * mesma ação com a mesma entrada em voo vira uma só); a chave não pode depender só do
 * horário, senão pedir de novo um horário que a pessoa cancelou devolveria a consulta
 * cancelada.
 */
function requestKey(): string {
  const random = Math.random().toString(36).slice(2, 12);
  return `app-${Date.now().toString(36)}-${random}`.slice(0, 64);
}

export const agendaActions: LiveActionRegistry = {
  requestAppointment: {
    run: (input) => async (api) => {
      const option = splitOptionId(input.serviceId);
      if (!option) return { ok: false, reason: "invalid" };
      await api.post("/mobile/appointments/", {
        service_id: option.serviceId,
        professional_id: option.professionalId,
        unit_id: option.unitId,
        start_at: input.slot,
        idempotency_key: requestKey(),
      });
      return { ok: true };
    },
    refresh: ["appointments", "services"],
  },
  cancelAppointment: {
    run: (input) => async (api) => {
      await api.post(`/mobile/appointments/${input.id}/cancel/`, {
        reason: input.reason.trim(),
      });
      return { ok: true };
    },
    refresh: ["appointments", "services"],
  },
  requestReschedule: {
    run: (input) => async (api) => {
      // O servidor só remarca para um horário livre: sem ele não há o que pedir.
      if (!input.slot) return { ok: false, reason: "invalid" };
      await api.post(`/mobile/appointments/${input.id}/reschedule/`, {
        start_at: input.slot,
      });
      return { ok: true };
    },
    refresh: ["appointments", "services"],
  },
};
