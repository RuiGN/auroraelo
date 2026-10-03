/**
 * Conteúdo pessoal que o PACIENTE edita no app (privado por padrão): meta de
 * recuperação, plano de prevenção de recaída, plano de apoio urgente (e seus contatos)
 * e as ações do modo de pouca energia (rotas de escrita de api/mobile_authoring_api.py).
 */
import type { LiveActionRegistry } from "./actions";

export const authoringActions: LiveActionRegistry = {
  setupSobriety: {
    run: (input) => async (api) => {
      await api.post("/mobile/recovery/goal/", {
        goal_type: input.goalType,
        focus: input.focus.trim(),
        reference_date: input.referenceDate,
        motivations: input.motivations.trim(),
        hide_counter: input.hideCounter,
      });
      return { ok: true };
    },
    refresh: ["sobriety"],
  },
  saveRelapsePlan: {
    run:
      (input, { snapshot }) =>
      async (api) => {
        const sections = input.sections
          .filter((item) => item.content.trim().length > 0)
          .map((item) => ({
            section_type: item.type,
            title: item.title.trim() || item.type,
            content: item.content.trim(),
          }));
        await api.put("/mobile/relapse-plan/", {
          title: input.title.trim(),
          sections,
        });
        // O PUT só grava o que veio: uma parte esvaziada precisa ser removida à parte.
        const kept = new Set(sections.map((item) => item.section_type));
        for (const section of snapshot?.relapsePlan?.sections ?? []) {
          if (!kept.has(section.type)) {
            await api.delete(`/mobile/relapse-plan/sections/${section.type}/`);
          }
        }
        return { ok: true };
      },
    refresh: ["relapsePlan"],
  },
  saveUrgentPlan: {
    run: (input) => async (api) => {
      await api.put("/mobile/urgent-plan/", {
        personal_instructions: input.personalInstructions.trim(),
        calming_strategies: input.calmingStrategies
          .map((item) => item.trim())
          .filter((item) => item.length > 0),
      });
      return { ok: true };
    },
    refresh: ["urgentPlan"],
  },
  saveUrgentContact: {
    run: (input) => async (api) => {
      const body = {
        name: input.name.trim(),
        relationship: input.relationship.trim(),
        phone_number: input.phone.trim(),
        message_template: input.messageTemplate.trim(),
      };
      if (input.id) {
        await api.put(`/mobile/urgent-plan/contacts/${input.id}/`, body);
      } else {
        await api.post("/mobile/urgent-plan/contacts/", body);
      }
      return { ok: true };
    },
    refresh: ["urgentPlan"],
  },
  removeUrgentContact: {
    run: (contactId) => async (api) => {
      await api.delete(`/mobile/urgent-plan/contacts/${contactId}/`);
      return { ok: true };
    },
    refresh: ["urgentPlan"],
  },
  setLowEnergyActions: {
    run: (actions) => async (api) => {
      await api.put("/mobile/low-energy/actions/", {
        actions: actions
          .map((item) => item.trim())
          .filter((item) => item.length > 0),
      });
      return { ok: true };
    },
    refresh: ["lowEnergy"],
  },
};
