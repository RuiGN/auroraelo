import { addDays, combineDateTime, toISODate } from "../domain/logic";
import { Snapshot } from "../domain/types";

/**
 * Dados 100% SINTÉTICOS para o modo demonstração (EXPO_PUBLIC_APP_MODE=preview).
 * Nenhum nome, telefone, prescrição ou registro aqui pertence a uma pessoa real.
 * Os textos clínicos ficam em português: conteúdo de paciente/prontuário não é
 * traduzido pelo seletor de idioma (decisão do PRD).
 */
export function buildPreviewSnapshot(now: Date): Snapshot {
  const today = toISODate(now);
  const day = (offset: number) => addDays(today, offset);
  const at = (offset: number, time: string) =>
    combineDateTime(day(offset), time);

  const dischargeDate = day(-9);
  const team = {
    psychiatrist: {
      id: "t-psy",
      name: "Dra. Helena Duarte",
      role: "psychiatrist" as const,
    },
    psychologist: {
      id: "t-psi",
      name: "Rafael Moura",
      role: "psychologist" as const,
    },
    nurse: { id: "t-enf", name: "Camila Freitas", role: "nurse" as const },
    pharmacist: {
      id: "t-far",
      name: "Bruno Tavares",
      role: "pharmacist" as const,
    },
  };

  return {
    patient: {
      id: "p-demo",
      displayName: "Alex Exemplo",
      clinicName: "Clínica Aurora (demonstração)",
      dischargeDate,
      careTeam: Object.values(team),
    },
    checkIns: [
      {
        id: "ci-1",
        date: day(-1),
        answers: {
          general_state: 3,
          anxiety: 3,
          sadness: 2,
          irritability: 2,
          energy: 3,
          sleep_quality: 2,
          motivation: 4,
        },
        notes: "Dormi mal, mas consegui caminhar à tarde.",
        visibility: "shareable",
        submittedAt: at(-1, "20:40"),
      },
    ],
    journal: [
      {
        id: "j-1",
        createdAt: at(-2, "21:10"),
        mood: 3,
        emotions: ["anxiety", "hope"],
        intensity: 3,
        context:
          "Primeiro jantar em família depois da alta. Fiquei tenso no começo.",
        triggers: "Brinde com bebida na mesa.",
        reactions: "Fiquei calado e saí para a varanda.",
        strategies:
          "Respirei fundo e voltei quando passou. Liguei para meu irmão depois.",
        visibility: "private",
      },
    ],
    sobriety: {
      id: "sg-1",
      goalType: "abstinence",
      focus: "Álcool",
      referenceDate: dischargeDate,
      restartCount: 0,
      motivations:
        "Estar presente para minha família e recuperar a confiança no trabalho.",
      hideCounter: false,
    },
    cravings: [
      {
        id: "cr-1",
        recordedAt: at(-3, "18:30"),
        intensity: 6,
        triggersContext:
          "Voltando do trabalho, passei na frente do bar de sempre.",
        copingStrategyUsed:
          "Mudei de caminho e liguei para uma pessoa de confiança.",
      },
    ],
    medications: [
      {
        id: "m-1",
        name: "Sertralina",
        presentation: "Comprimido 50 mg",
        dose: "1 comprimido",
        route: "oral",
        scheduleTimes: ["08:00"],
        startDate: day(-60),
        endDate: null,
        isContinuous: true,
        prescriberName: team.psychiatrist.name,
        instructions: "Tomar pela manhã, com água, após o café da manhã.",
      },
      {
        id: "m-2",
        name: "Naltrexona",
        presentation: "Comprimido 50 mg",
        dose: "1 comprimido",
        route: "oral",
        scheduleTimes: ["08:00"],
        startDate: day(-30),
        endDate: day(60),
        isContinuous: false,
        prescriberName: team.psychiatrist.name,
        instructions: "Tomar junto com a primeira medicação da manhã.",
      },
      {
        id: "m-3",
        name: "Tiamina (vitamina B1)",
        presentation: "Comprimido 300 mg",
        dose: "1 comprimido",
        route: "oral",
        scheduleTimes: ["20:00"],
        startDate: day(-30),
        endDate: null,
        isContinuous: true,
        prescriberName: team.psychiatrist.name,
        instructions: "Tomar à noite, após o jantar.",
      },
    ],
    doseLogs: [
      {
        id: "d-1",
        medicationId: "m-1",
        scheduledFor: at(-1, "08:00"),
        status: "taken",
        recordedAt: at(-1, "08:12"),
      },
      {
        id: "d-2",
        medicationId: "m-2",
        scheduledFor: at(-1, "08:00"),
        status: "taken",
        recordedAt: at(-1, "08:12"),
      },
      {
        id: "d-3",
        medicationId: "m-3",
        scheduledFor: at(-1, "20:00"),
        status: "late",
        recordedAt: at(-1, "21:30"),
      },
    ],
    carePlan: {
      id: "cp-1",
      title: "Plano de cuidado pós-alta",
      objective:
        "Sustentar a recuperação nos primeiros meses em casa, com acompanhamento regular, rotina protegida e apoio da família.",
      contraindications:
        "Interrompa a atividade física e fale com a equipe se sentir dor no peito, falta de ar ou tontura.",
      status: "active",
      version: 2,
      validFrom: dischargeDate,
      validUntil: day(81),
      prescriberName: team.psychiatrist.name,
      actions: [
        {
          id: "ca-1",
          description: "Comparecer às consultas e ligações de acompanhamento",
          targetFrequency: "Conforme agenda",
          guidance:
            "Se não puder comparecer, avise a clínica com antecedência.",
          isMandatory: true,
        },
        {
          id: "ca-2",
          description: "Tomar a medicação prescrita nos horários combinados",
          targetFrequency: "Diária",
          guidance:
            "Em caso de dúvida ou efeito incômodo, fale com a equipe antes de mudar qualquer dose.",
          isMandatory: true,
        },
        {
          id: "ca-3",
          description: "Participar de um grupo de apoio",
          targetFrequency: "Semanal",
          guidance:
            "Escolha um grupo perto de casa ou on-line com a ajuda da equipe.",
          isMandatory: false,
        },
        {
          id: "ca-4",
          description: "Caminhada leve",
          targetFrequency: "3 vezes por semana",
          guidance: "Comece com 20 minutos, em ritmo confortável.",
          isMandatory: false,
        },
      ],
      response: null,
    },
    habits: [
      {
        id: "h-1",
        title: "Café da manhã e água",
        description: "Começar o dia com uma refeição antes da medicação.",
        timeWindow: "morning",
        targetTime: "07:30",
      },
      {
        id: "h-2",
        title: "Caminhada de 20 minutos",
        description: "Ritmo leve, de preferência perto de casa.",
        timeWindow: "afternoon",
        targetTime: null,
      },
      {
        id: "h-3",
        title: "Ligar para uma pessoa de confiança",
        description: "Uma conversa curta já conta.",
        timeWindow: "any_time",
        targetTime: null,
      },
      {
        id: "h-4",
        title: "Desligar telas 30 minutos antes de dormir",
        description: "Ajuda o sono a ficar mais regular.",
        timeWindow: "night",
        targetTime: "22:00",
      },
    ],
    habitChecks: [
      { habitId: "h-1", date: day(-1), status: "completed" },
      { habitId: "h-2", date: day(-1), status: "completed" },
      { habitId: "h-3", date: day(-1), status: "partial" },
      { habitId: "h-4", date: day(-1), status: "skipped" },
    ],
    exercises: [
      {
        id: "ex-1",
        title: "Mapa de gatilhos da semana",
        instructions:
          "Anote situações, lugares ou sentimentos que aumentaram a vontade de usar nesta semana e o que você fez em cada uma.",
        approach: "Prevenção de recaída",
        estimatedMinutes: 15,
        responseFormat: "text",
        frequency: "Semanal",
        dueDate: day(2),
        assignedByName: team.psychologist.name,
        status: "assigned",
        response: "",
        completedAt: null,
        visibility: "confirmation_required",
      },
      {
        id: "ex-2",
        title: "Termômetro da vontade de usar",
        instructions:
          "De 1 a 5, como esteve sua vontade de usar hoje? Anote o que ajudou.",
        approach: "Automonitoramento",
        estimatedMinutes: 5,
        responseFormat: "scale_1_5",
        frequency: "Diária",
        dueDate: null,
        assignedByName: team.psychologist.name,
        status: "completed",
        response: "2",
        completedAt: at(-1, "19:00"),
        visibility: "private",
      },
    ],
    relapsePlan: {
      id: "rp-1",
      title: "Meu plano de prevenção de recaída",
      version: 1,
      lastReviewedAt: at(-6, "15:00"),
      sections: [
        {
          id: "rs-1",
          type: "triggers",
          title: "Gatilhos",
          content:
            "Bar perto do trabalho, brindes em festas, discussões em família, noites sozinho.",
        },
        {
          id: "rs-2",
          type: "early_warning_signs",
          title: "Sinais de alerta",
          content:
            "Dormir mal por vários dias, isolamento, irritação fácil, pensar que “um gole não faz mal”.",
        },
        {
          id: "rs-3",
          type: "protective_factors",
          title: "O que me protege",
          content:
            "Rotina de sono, caminhada, minha mãe e meu irmão, grupo de apoio às quartas.",
        },
        {
          id: "rs-4",
          type: "coping_strategies",
          title: "O que posso fazer na hora",
          content:
            "Respirar por 2 minutos, sair do ambiente, beber água, ligar para meu irmão.",
        },
        {
          id: "rs-5",
          type: "safe_environments",
          title: "Lugares seguros",
          content: "Casa da minha mãe, academia do bairro, grupo de apoio.",
        },
        {
          id: "rs-6",
          type: "support_contacts",
          title: "Pessoas de apoio",
          content: "Pedro (irmão), Marta (mãe), Rafael (psicólogo).",
        },
        {
          id: "rs-7",
          type: "professional_resources",
          title: "Ajuda profissional",
          content:
            "Clínica Aurora: equipe de acompanhamento em horário comercial. Emergência: 192. Apoio emocional: 188.",
        },
      ],
    },
    goals: [
      {
        id: "g-1",
        title: "Retomar a rotina de trabalho",
        description:
          "Voltar ao trabalho de forma gradual, combinando ajustes com a empresa.",
        horizon: "medium",
        dueDate: day(45),
        status: "active",
        steps: [
          {
            id: "gs-1",
            description: "Conversar com o RH sobre o retorno",
            order: 1,
            isDone: true,
          },
          {
            id: "gs-2",
            description:
              "Definir carga horária reduzida nas 2 primeiras semanas",
            order: 2,
            isDone: false,
          },
          {
            id: "gs-3",
            description: "Escolher um caminho de volta sem passar pelo bar",
            order: 3,
            isDone: false,
          },
        ],
      },
      {
        id: "g-2",
        title: "Reaproximar da família",
        description: "Reconstruir a confiança com pequenos passos concretos.",
        horizon: "short",
        dueDate: day(14),
        status: "active",
        steps: [
          {
            id: "gs-4",
            description: "Almoço de domingo com minha mãe",
            order: 1,
            isDone: true,
          },
          {
            id: "gs-5",
            description: "Passeio com meu irmão",
            order: 2,
            isDone: false,
          },
        ],
      },
    ],
    lowEnergy: {
      actions: [
        "Beber um copo de água",
        "Tomar a medicação do horário",
        "Mandar uma mensagem para alguém de confiança",
      ],
      active: false,
      startedAt: null,
    },
    appointments: [
      {
        id: "a-1",
        serviceName: "Consulta de retorno",
        professionalName: team.psychiatrist.name,
        unitName: "Unidade Centro",
        startAt: at(-3, "10:00"),
        endAt: at(-3, "10:40"),
        status: "completed",
        cancelReason: "",
      },
      {
        id: "a-2",
        serviceName: "Psicoterapia individual",
        professionalName: team.psychologist.name,
        unitName: "Unidade Centro",
        startAt: at(2, "16:00"),
        endAt: at(2, "16:50"),
        status: "confirmed",
        cancelReason: "",
      },
      {
        id: "a-3",
        serviceName: "Revisão de medicação",
        professionalName: team.psychiatrist.name,
        unitName: "Unidade Centro",
        startAt: at(12, "09:30"),
        endAt: at(12, "10:10"),
        status: "requested",
        cancelReason: "",
      },
    ],
    services: [
      {
        id: "s-1",
        name: "Psicoterapia individual",
        durationMinutes: 50,
        professionalName: team.psychologist.name,
        unitName: "Unidade Centro",
        freeSlots: [
          at(4, "14:00"),
          at(4, "15:00"),
          at(5, "10:00"),
          at(7, "16:00"),
        ],
      },
      {
        id: "s-2",
        name: "Consulta de acompanhamento (enfermagem)",
        durationMinutes: 30,
        professionalName: team.nurse.name,
        unitName: "Unidade Centro",
        freeSlots: [at(3, "11:00"), at(6, "09:00")],
      },
    ],
    supportNetwork: [
      {
        id: "sn-1",
        name: "Marta Exemplo",
        relationship: "Mãe",
        scopes: ["view_goals", "view_appointments"],
        active: true,
      },
      {
        id: "sn-2",
        name: "Pedro Exemplo",
        relationship: "Irmão",
        scopes: ["view_goals", "receive_alerts"],
        active: true,
      },
    ],
    urgentPlan: {
      personalInstructions:
        "Se eu sentir muita vontade de usar: sair do lugar, beber água, respirar fundo e ligar para alguém da lista antes de decidir qualquer coisa.",
      calmingStrategies: [
        "Respirar devagar por 2 minutos",
        "Caminhar até a esquina e voltar",
        "Ouvir minha playlist calma",
      ],
      contacts: [
        {
          id: "uc-1",
          name: "Pedro Exemplo",
          relationship: "Irmão",
          phone: "+55 81 0000-0002",
          messageTemplate:
            "Oi, estou em um momento difícil e queria conversar. Pode falar agora?",
        },
        {
          id: "uc-2",
          name: "Marta Exemplo",
          relationship: "Mãe",
          phone: "+55 81 0000-0001",
          messageTemplate:
            "Mãe, preciso de você por perto hoje. Pode me ligar quando puder?",
        },
      ],
      lastReviewedAt: at(-6, "15:00"),
    },
    content: [
      {
        id: "c-1",
        title: "Entendendo a vontade de usar (fissura)",
        kind: "article",
        category: "Recuperação",
        body: "A vontade de usar costuma subir, chegar a um pico e diminuir, mesmo sem ceder a ela. Observar o que aconteceu antes, respirar e mudar de ambiente podem ajudar a atravessar esse momento. Conversar com alguém de confiança também ajuda.",
        contraindications:
          "Este texto é informativo e não substitui a orientação da sua equipe de saúde.",
        sourceReference: "Conteúdo sintético de demonstração",
        recommendedByName: team.psychologist.name,
        recommendationObjective:
          "Preparar você para os momentos de maior vontade de usar.",
        estimatedMinutes: 4,
        favorite: false,
        read: false,
      },
      {
        id: "c-2",
        title: "Sono e recuperação",
        kind: "article",
        category: "Rotina",
        body: "Horários regulares para dormir e acordar costumam tornar os dias mais previsíveis. Evite telas na última meia hora antes de deitar e combine com a equipe se o sono continuar difícil por muitos dias.",
        contraindications:
          "Não use este texto para ajustar medicação por conta própria.",
        sourceReference: "Conteúdo sintético de demonstração",
        recommendedByName: null,
        recommendationObjective: null,
        estimatedMinutes: 3,
        favorite: true,
        read: true,
      },
      {
        id: "c-3",
        title: "Respiração guiada de 2 minutos",
        kind: "audio",
        category: "Bem-estar",
        body: "Sente-se com a coluna apoiada. Inspire contando até 4 e solte o ar contando até 6. Repita por cerca de dois minutos, no seu ritmo. Pare se sentir tontura.",
        contraindications: "Pare se sentir tontura ou desconforto.",
        sourceReference: "Conteúdo sintético de demonstração",
        recommendedByName: null,
        recommendationObjective: null,
        estimatedMinutes: 2,
        favorite: false,
        read: false,
      },
      {
        id: "c-4",
        title: "Conversando com a família sobre os próximos passos",
        kind: "article",
        category: "Família",
        body: "Combine com sua família o que ajuda e o que não ajuda neste momento. Dizer com clareza do que você precisa evita mal-entendidos.",
        contraindications: "",
        sourceReference: "Conteúdo sintético de demonstração",
        recommendedByName: team.psychologist.name,
        recommendationObjective: "Facilitar a reaproximação com a família.",
        estimatedMinutes: 5,
        favorite: false,
        read: false,
      },
    ],
    consents: [
      {
        id: "co-1",
        purpose: "terms_of_use",
        documentVersion: "2025.1",
        status: "granted",
        decidedAt: at(-9, "09:00"),
        mandatory: true,
      },
      {
        id: "co-2",
        purpose: "clinical_limits",
        documentVersion: "2025.1",
        status: "granted",
        decidedAt: at(-9, "09:00"),
        mandatory: true,
      },
      {
        id: "co-3",
        purpose: "clinical_follow_up",
        documentVersion: "2025.1",
        status: "granted",
        decidedAt: at(-9, "09:02"),
        mandatory: false,
      },
      {
        id: "co-4",
        purpose: "communication",
        documentVersion: "2025.1",
        status: "granted",
        decidedAt: at(-9, "09:02"),
        mandatory: false,
      },
    ],
    privacyRequests: [],
  };
}
