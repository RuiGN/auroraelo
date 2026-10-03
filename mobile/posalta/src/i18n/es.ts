import { Messages } from "./pt-br";

/** Español (es). Las claves deben coincidir exactamente con pt-br.ts (tipo Messages). */
export const es: Messages = {
  // ── Marca y general ───────────────────────────────────────────────────────
  "brand.tagline": "Tu cuidado después del alta",
  "common.cancel": "Cancelar",
  "common.close": "Cerrar",
  "common.send": "Enviar",
  "common.back": "Volver",
  "common.confirm": "Confirmar",
  "common.done": "Listo",
  "common.optional": "opcional",
  "common.today": "Hoy",
  "common.tomorrow": "Mañana",
  "common.yesterday": "Ayer",
  "common.call": "Llamar",
  "common.loading": "Cargando…",
  "common.version": "Versión {version}",

  // ── Navegación ────────────────────────────────────────────────────────────
  "nav.home": "Hoy",
  "nav.care": "Cuidado",
  "nav.diary": "Diario",
  "nav.agenda": "Agenda",
  "nav.support": "Apoyo",
  "nav.help": "Ayuda",
  "nav.profile": "Perfil",

  // ── Modo y disponibilidad ─────────────────────────────────────────────────
  "mode.preview.banner":
    "Demostración con datos ficticios. Nada se guarda, se envía ni es real.",
  "mode.unavailable.title": "Aún no conectado a tu clínica",
  "mode.unavailable.body":
    "Esta área mostrará los datos de tu cuidado cuando la aplicación esté conectada de forma segura a tu clínica. Por ahora no se muestra, guarda ni envía nada.",
  "mode.unavailable.help":
    "El botón Ayuda y los ajustes de idioma y apariencia funcionan con normalidad.",
  "mode.action.unavailable":
    "Esta acción aún no está disponible en la aplicación. No se guardó ni se envió nada.",
  "mode.action.invalid":
    "Revisa los campos e inténtalo de nuevo. No se guardó nada.",
  "mode.preview.saved":
    "Registrado en la demostración. No se guardó ni se envió a nadie.",

  // ── Inicio ────────────────────────────────────────────────────────────────
  "home.greeting.morning": "Buenos días, {name}",
  "home.greeting.afternoon": "Buenas tardes, {name}",
  "home.greeting.evening": "Buenas noches, {name}",
  "home.sinceDischarge_one": "Ha pasado {count} día desde tu alta",
  "home.sinceDischarge_other": "Han pasado {count} días desde tu alta",
  "home.dischargeToday": "Hoy es el día de tu alta",
  "home.today": "Tu día",
  "home.checkIn.todo": "Registrar cómo estás",
  "home.checkIn.done": "El registro de hoy está hecho",
  "home.medications": "Medicaciones de hoy",
  "home.medications.count": "{done} de {total} registradas",
  "home.medications.none": "Ninguna medicación hoy",
  "home.habits": "Rutina de hoy",
  "home.habits.count": "{done} de {total} hechas",
  "home.exercise": "Ejercicio del equipo",
  "home.exercise.due": "Para el {date}",
  "home.exercise.none": "Ningún ejercicio pendiente",
  "home.nextAppointment": "Próxima consulta",
  "home.nextAppointment.none": "Ninguna consulta programada",
  "home.lowEnergy.title": "¿Un día con poca energía?",
  "home.lowEnergy.body":
    "Está bien. Quédate solo con lo esencial hoy. Lo demás puede esperar.",
  "home.lowEnergy.activate": "Activar modo ligero",
  "home.lowEnergy.deactivate": "Volver a lo normal",
  "home.lowEnergy.active": "Modo ligero activo",
  "home.lowEnergy.actions": "Lo esencial de hoy",
  "home.quick.craving": "Tengo ganas de consumir",
  "home.quick.diary": "Escribir en mi diario",
  "home.goalFocus": "Meta en curso",
  "home.recoveryDays_one": "{count} día en recuperación",
  "home.recoveryDays_other": "{count} días en recuperación",
  "home.recovery.hidden": "Contador oculto por ti",

  // ── Ayuda urgente ─────────────────────────────────────────────────────────
  "help.title": "Necesito ayuda ahora",
  "help.disclaimer":
    "Esta aplicación no es un servicio de emergencia y no te monitorea en tiempo real. Nadie recibe un aviso cuando abres esta pantalla. Ante un peligro inmediato, llama ahora al servicio de emergencia.",
  "help.emergency": "Emergencia y apoyo",
  "help.number.medical": "SAMU — emergencia médica",
  "help.number.fire": "Bomberos",
  "help.number.police": "Policía",
  "help.number.emotional": "CVV — apoyo emocional, 24 horas",
  "help.number.call": "Llamar a {label} al número {number}",
  "help.people": "Personas de confianza",
  "help.people.none": "Aún no registraste personas de confianza con tu equipo.",
  "help.people.sms": "Enviar mensaje",
  "help.plan": "Mi plan para momentos difíciles",
  "help.calm": "Antes de decidir cualquier cosa",
  "help.breathing.title": "Respirar con calma",
  "help.breathing.start": "Comenzar respiración",
  "help.breathing.stop": "Detener",
  "help.breathing.inhale": "Inspira despacio",
  "help.breathing.exhale": "Suelta el aire despacio",
  "help.breathing.note":
    "Detente si sientes mareo. Puedes salir en cualquier momento.",
  "help.grounding.title": "5-4-3-2-1: volver al aquí y ahora",
  "help.grounding.step5": "Mira a tu alrededor y nombra 5 cosas que ves",
  "help.grounding.step4": "Toca 4 cosas y percibe su textura",
  "help.grounding.step3": "Escucha 3 sonidos a tu alrededor",
  "help.grounding.step2": "Percibe 2 olores",
  "help.grounding.step1": "Percibe 1 sabor en la boca",
  "help.grounding.note":
    "Ejercicio general de apoyo. No sustituye la atención profesional.",
  "help.noOneNotified": "Esta aplicación no avisó a nadie.",
  "help.preview.note":
    "En el modo demostración, las personas de confianza de abajo son ficticias. Los números de emergencia son reales.",
  "help.openFailed":
    "No se pudo abrir el marcador en este dispositivo. Marca el número manualmente.",

  // ── Cuidado ───────────────────────────────────────────────────────────────
  "care.plan": "Plan de cuidado",
  "care.plan.subtitle": "Lo que el equipo acordó contigo",
  "care.medications": "Medicaciones",
  "care.medications.subtitle": "Horarios y registro",
  "care.routine": "Rutina",
  "care.routine.subtitle": "Hábitos que protegen tu día",
  "care.exercises": "Ejercicios del equipo",
  "care.exercises.subtitle": "Actividades para hacer en casa",
  "care.relapse": "Plan de prevención de recaídas",
  "care.relapse.subtitle": "Desencadenantes, señales y qué hacer",
  "care.goals": "Metas",
  "care.goals.subtitle": "Pasos pequeños, uno a la vez",

  "plan.status.draft": "Borrador",
  "plan.status.pending_signature": "Pendiente de firma",
  "plan.status.active": "Activo",
  "plan.status.paused": "En pausa",
  "plan.status.completed": "Concluido",
  "plan.status.revoked": "Revocado",
  "plan.objective": "Objetivo",
  "plan.actions": "Qué hacer",
  "plan.mandatory": "Esencial",
  "plan.contraindications": "Precauciones",
  "plan.version": "Versión {version} • válido desde {date}",
  "plan.by": "Prescrito por {name}",
  "plan.respond": "Tu respuesta al plan",
  "plan.respond.badge": "Responder",
  "plan.respond.hint":
    "Puedes aceptar, pausar, rechazar o pedir una revisión al equipo.",
  "plan.decision.accepted": "Aceptar",
  "plan.decision.paused": "Pausar",
  "plan.decision.refused": "Rechazar",
  "plan.decision.review_requested": "Pedir revisión",
  "plan.notes": "Observaciones para el equipo",
  "plan.responded": "Respondiste: {decision}",
  "plan.responded.at": "el {date}",
  "plan.responded.note":
    "El equipo solo ve esta respuesta cuando se envíe a la clínica. La aplicación no avisa a nadie en tiempo real.",

  "meds.title": "Medicaciones",
  "meds.today": "Hoy",
  "meds.none": "Ninguna medicación prescrita.",
  "meds.taken": "Tomada",
  "meds.late": "Tomada con retraso",
  "meds.omitted": "No tomada",
  "meds.undo": "Deshacer",
  "meds.status.taken": "Tomada",
  "meds.status.late": "Tomada con retraso",
  "meds.status.omitted": "No tomada",
  "meds.status.pending": "Pendiente",
  "meds.prescribedBy": "Prescrita por {name}",
  "meds.until": "hasta {date}",
  "meds.continuous": "uso continuo",
  "meds.safety":
    "Este registro es tuyo. Si tienes dudas sobre una dosis, un efecto molesto o un olvido, habla con el equipo de salud antes de cambiar algo.",
  "meds.route.oral": "vía oral",
  "meds.route.sublingual": "sublingual",
  "meds.route.topical": "uso tópico",
  "meds.route.inhalation": "inhalación",
  "meds.route.injectable": "inyectable",
  "meds.route.ophthalmic": "uso oftálmico",
  "meds.route.nasal": "vía nasal",
  "meds.route.other": "otra vía",
  "meds.schedule": "Horarios",

  "routine.title": "Rutina",
  "routine.hint": "Marca lo que lograste. Hacerlo en parte también cuenta.",
  "routine.status.completed": "Hecho",
  "routine.status.partial": "En parte",
  "routine.status.postponed": "Pospuse",
  "routine.status.skipped": "Omití",
  "routine.window.morning": "Mañana",
  "routine.window.afternoon": "Tarde",
  "routine.window.evening": "Atardecer",
  "routine.window.night": "Noche",
  "routine.window.any_time": "Cualquier hora",
  "routine.none": "Aún no hay hábitos acordados.",

  "exercise.title": "Ejercicios del equipo",
  "exercise.pending": "Por hacer",
  "exercise.completed": "Concluidos",
  "exercise.none": "Ningún ejercicio asignado.",
  "exercise.minutes": "{count} min",
  "exercise.frequency": "Frecuencia: {value}",
  "exercise.assignedBy": "Asignado por {name}",
  "exercise.response": "Tu respuesta",
  "exercise.response.scale": "Elige de 1 (muy poco) a 5 (mucho)",
  "exercise.response.text": "Escribe con tus palabras",
  "exercise.complete": "Concluir ejercicio",
  "exercise.visibility": "Quién puede ver tu respuesta",
  "exercise.doneAt": "Concluido el {date}",

  "relapse.title": "Plan de prevención de recaídas",
  "relapse.intro":
    "Un plan hecho por ti y el equipo para los momentos de riesgo. Leerlo con calma ahora ayuda a recordarlo en el momento difícil.",
  "relapse.reviewed": "Revisado el {date}",
  "relapse.never": "Aún sin revisar",
  "relapse.none": "Aún no ha creado su plan.",
  "relapse.section.triggers": "Desencadenantes",
  "relapse.section.early_warning_signs": "Señales de alerta",
  "relapse.section.protective_factors": "Lo que me protege",
  "relapse.section.coping_strategies": "Lo que puedo hacer en el momento",
  "relapse.section.safe_environments": "Lugares seguros",
  "relapse.section.support_contacts": "Personas de apoyo",
  "relapse.section.professional_resources": "Ayuda profesional",
  "relapse.restartNote":
    "Volver a empezar es parte del camino. Habla con el equipo cuando lo necesites.",

  "plans.private":
    "Solo usted ve lo que hay aquí. El equipo no recibe nada cuando usted guarda.",
  "plans.save": "Guardar",
  "plans.saved": "Guardado.",
  "recovery.goal.title": "Mi meta de recuperación",
  "recovery.goal.define": "Definir mi meta",
  "recovery.goal.intro":
    "Elija lo que tenga sentido para usted. Se puede ajustar después, sin culpa.",
  "recovery.goal.type": "Tipo de meta",
  "recovery.goal.type.abstinence": "Mantenerme sin",
  "recovery.goal.type.reduction": "Reducir",
  "recovery.goal.type.moderation": "Moderar",
  "recovery.goal.focus": "¿Sobre qué?",
  "recovery.goal.focus.help": "Por ejemplo: alcohol, juego u otra sustancia.",
  "recovery.goal.motivations": "¿Por qué es importante para usted?",
  "recovery.goal.since": "Contar desde",
  "recovery.goal.since.today": "Hoy",
  "recovery.goal.since.yesterday": "Ayer",
  "recovery.goal.since.week": "Hace 7 días",
  "recovery.goal.since.month": "Hace 30 días",
  "recovery.goal.hide": "Ocultar el contador de días",
  "recovery.goal.submit": "Guardar mi meta",
  "relapse.edit": "Editar mi plan",
  "relapse.create": "Crear mi plan",
  "relapse.edit.title": "Mi plan de prevención",
  "relapse.edit.intro":
    "Escríbalo con sus palabras. Deje en blanco lo que no quiera completar ahora.",
  "urgent.edit.title": "Mi plan de apoyo urgente",
  "urgent.edit.subtitle": "Personas de confianza y lo que ayuda a calmarse",
  "urgent.instructions": "Lo que quiero recordar en esos momentos",
  "urgent.strategies": "Lo que me ayuda a calmarme (una por línea)",
  "urgent.contacts": "Personas de confianza",
  "urgent.contact.add": "Añadir persona",
  "urgent.contact.edit": "Editar",
  "urgent.contact.remove": "Quitar",
  "urgent.contact.name": "Nombre",
  "urgent.contact.relationship": "Relación (p. ej., madre, amigo)",
  "urgent.contact.phone": "Teléfono",
  "urgent.contact.message": "Mensaje listo (opcional)",
  "urgent.contact.save": "Guardar persona",
  "urgent.contact.limit": "Ya tiene 5 personas. Quite una para añadir otra.",
  "urgent.note":
    "Guardar no avisa a nadie. La llamada solo ocurre cuando usted toca el número.",
  "lowenergy.edit.title": "Mis acciones de poca energía",
  "lowenergy.edit.intro":
    "Hasta tres cosas muy pequeñas para los días difíciles.",
  "lowenergy.edit.action": "Acción {n}",
  "lowenergy.edit.entry": "Elegir mis acciones",
  "goals.title": "Metas",
  "goals.active": "En curso",
  "goals.other": "En pausa y concluidas",
  "goals.none": "Aún no hay metas definidas.",
  "goals.steps": "{done} de {total} pasos",
  "goals.due": "Hasta el {date}",
  "goals.horizon.short": "Corto plazo",
  "goals.horizon.medium": "Mediano plazo",
  "goals.horizon.long": "Largo plazo",
  "goals.status.active": "En curso",
  "goals.status.paused": "En pausa",
  "goals.status.completed": "Concluida",
  "goals.status.archived": "Archivada",
  "goals.pause": "Pausar meta",
  "goals.resume": "Retomar meta",
  "goals.complete": "Concluir meta",

  // ── Diario ────────────────────────────────────────────────────────────────
  "diary.checkIn": "Cómo estoy hoy",
  "diary.checkIn.subtitle": "Un registro rápido, una vez al día",
  "diary.checkIn.doneToday":
    "Ya registraste hoy. Enviar de nuevo reemplaza el registro de hoy.",
  "diary.write": "Escribir en el diario",
  "diary.write.subtitle": "Ánimo, emociones y lo que pasó",
  "diary.craving": "Ganas de consumir",
  "diary.craving.subtitle": "Regístralas y usa tus estrategias",
  "diary.entries": "Últimos registros",
  "diary.entries.none": "Tus registros aparecerán aquí.",
  "diary.recovery": "Mi camino de recuperación",
  "access.title": "Solicitudes del equipo",
  "access.from": "{name} pide ver uno de sus registros",
  "access.entry": "Registro del {date}",
  "access.note": "Usted decide. Si no responde, no se comparte nada.",
  "access.approve": "Permitir",
  "access.deny": "No permitir",
  "access.approved": "Solicitud aprobada.",
  "access.denied": "Solicitud rechazada.",
  "diary.privacy":
    "Tu diario es privado por defecto. Tú eliges si cada registro puede compartirse con el equipo.",

  "checkin.title": "Cómo estoy hoy",
  "checkin.intro": "Responde de 1 a 5. No hay respuesta correcta.",
  "checkin.scale.low": "Muy bajo",
  "checkin.scale.high": "Muy alto",
  "checkin.q.general_state": "¿Cómo evalúas tu estado general hoy?",
  "checkin.q.anxiety": "Nivel de ansiedad hoy",
  "checkin.q.sadness": "Sentimiento de tristeza o desánimo",
  "checkin.q.irritability": "Nivel de irritabilidad o impaciencia",
  "checkin.q.energy": "Nivel de energía",
  "checkin.q.sleep_quality": "Calidad de tu sueño anoche",
  "checkin.q.motivation": "Motivación para tu día",
  "checkin.notes": "Observaciones",
  "checkin.notes.placeholder": "Algo que quieras anotar sobre el día",
  "checkin.visibility": "¿Compartir este registro con el equipo?",
  "checkin.submit": "Guardar registro de hoy",
  "checkin.missing": "Responde todas las preguntas de 1 a 5 para guardar.",
  "checkin.saved":
    "Registro de hoy guardado. Tu equipo no sigue esta aplicación en tiempo real.",
  "checkin.support.title": "Parece un día difícil",
  "checkin.support.body":
    "No tienes que pasar por esto sin apoyo. Busca a alguien de confianza o usa el botón Ayuda si necesitas ayuda ahora.",
  "checkin.support.cta": "Abrir ayuda",

  "entry.title": "Nuevo registro en el diario",
  "entry.mood": "¿Cómo está tu ánimo?",
  "entry.mood.1": "Muy mal",
  "entry.mood.2": "Mal",
  "entry.mood.3": "Más o menos",
  "entry.mood.4": "Bien",
  "entry.mood.5": "Muy bien",
  "entry.emotions": "¿Qué sentiste?",
  "entry.intensity": "Intensidad (1 a 5)",
  "entry.context": "¿Qué pasó?",
  "entry.context.placeholder": "Cuéntalo con tus palabras",
  "entry.triggers": "¿Qué pudo haberlo desencadenado?",
  "entry.reactions": "¿Cómo reaccionaste?",
  "entry.strategies": "¿Qué ayudó?",
  "entry.visibility": "Quién puede ver este registro",
  "entry.submit": "Guardar en el diario",
  "entry.saved": "Registro guardado en el diario.",
  "entry.context.required": "Escribe al menos una línea sobre lo que pasó.",
  "entry.detail": "Registro",
  "entry.emotion.anxiety": "Ansiedad",
  "entry.emotion.sadness": "Tristeza",
  "entry.emotion.anger": "Enojo",
  "entry.emotion.joy": "Alegría",
  "entry.emotion.fear": "Miedo",
  "entry.emotion.calm": "Calma",
  "entry.emotion.frustration": "Frustración",
  "entry.emotion.hope": "Esperanza",

  "visibility.private": "Solo yo",
  "visibility.private.hint": "Se queda solo contigo.",
  "visibility.shareable": "Puedo compartir con el equipo",
  "visibility.shareable.hint": "El equipo podrá ver este registro.",
  "visibility.confirmation_required": "Preguntarme antes",
  "visibility.confirmation_required.hint":
    "El equipo solo lo ve después de que autorices la solicitud de acceso.",

  "craving.title": "Ganas de consumir",
  "craving.intro":
    "Sentir ganas de consumir es común y suele pasar. No tienes que enfrentarlo solo.",
  "craving.intensity": "¿Qué tan fuerte es ahora? (1 a 10)",
  "craving.context": "¿Qué está pasando?",
  "craving.strategy": "¿Qué hiciste o harás?",
  "craving.suggestions": "De tu plan",
  "craving.suggestions.none":
    "Cuando tu plan de prevención esté listo, las estrategias aparecerán aquí.",
  "craving.breathe": "Respirar ahora",
  "craving.callSomeone": "Llamar a alguien de confianza",
  "craving.submit": "Registrar",
  "craving.saved":
    "Registro guardado. Si las ganas se vuelven demasiado fuertes, usa el botón Ayuda.",
  "craving.history": "Registros anteriores",
  "craving.level": "Intensidad {value} de 10",

  "recovery.title": "Mi contador",
  "recovery.days_one": "{count} día",
  "recovery.days_other": "{count} días",
  "recovery.since": "desde el {date}",
  "recovery.hide": "Ocultar contador",
  "recovery.show": "Mostrar contador",
  "recovery.hidden": "Contador oculto. Tú decides cuándo verlo.",
  "recovery.motivations": "Lo que me motiva",
  "recovery.restart": "Reiniciar la cuenta",
  "recovery.restart.confirm": "¿Reiniciar la cuenta hoy?",
  "recovery.restart.body":
    "Volver a empezar es parte del camino y no borra lo que aprendiste. Si quieres, habla con el equipo sobre lo que pasó.",
  "recovery.restart.count_one": "{count} reinicio",
  "recovery.restart.count_other": "{count} reinicios",
  "recovery.focus": "Enfoque: {focus}",

  // ── Agenda ────────────────────────────────────────────────────────────────
  "agenda.title": "Agenda",
  "agenda.upcoming": "Próximas",
  "agenda.past": "Anteriores",
  "agenda.none": "No hay consultas por aquí.",
  "agenda.request": "Solicitar consulta",
  "agenda.status.requested": "Esperando confirmación",
  "agenda.status.confirmed": "Confirmada",
  "agenda.status.reschedule_requested": "Reprogramación solicitada",
  "agenda.status.canceled": "Cancelada",
  "agenda.status.completed": "Realizada",
  "agenda.status.no_show": "No asistió",
  "agenda.with": "con {name}",
  "agenda.at": "{unit}",
  "agenda.reschedule": "Pedir reprogramación",
  "agenda.reschedule.pick": "Elija el nuevo horario",
  "agenda.reschedule.none":
    "No hay horarios libres para reprogramar ahora. Hable con la clínica.",
  "agenda.reschedule.submit": "Solicitar reprogramación",
  "agenda.cancel": "Cancelar consulta",
  "agenda.cancel.confirm": "¿Cancelar esta consulta?",
  "agenda.cancel.reason": "Motivo (opcional)",
  "agenda.rescheduleNote":
    "La solicitud de reprogramación solo vale cuando la clínica responda. Hasta entonces, la consulta original sigue reservada.",
  "agenda.request.title": "Solicitar consulta",
  "agenda.request.service": "Tipo de atención",
  "agenda.request.slot": "Horarios libres",
  "agenda.request.noSlots":
    "No hay horarios libres ahora. Habla con la clínica.",
  "agenda.request.submit": "Solicitar este horario",
  "agenda.request.note":
    "La solicitud queda a la espera de confirmación de la clínica. Solo se confirma cuando recibas la respuesta.",
  "agenda.request.sent":
    "Solicitud registrada. Espera la confirmación de la clínica.",

  // ── Apoyo ─────────────────────────────────────────────────────────────────
  "support.network": "Mi red de apoyo",
  "support.network.subtitle": "Quién te acompaña y qué puede ver",
  "support.learn": "Para aprender",
  "support.learn.subtitle": "Textos y prácticas recomendados",

  "network.title": "Mi red de apoyo",
  "network.intro":
    "Personas que autorizaste para acompañar parte de tu camino. Tú decides qué puede ver cada una.",
  "network.none": "Aún no invitaste a nadie.",
  "network.revoke": "Terminar acompañamiento",
  "network.revoked": "Acompañamiento terminado",
  "network.revoke.confirm": "¿Terminar el acompañamiento de {name}?",
  "network.diary": "Tu diario nunca se comparte con la red de apoyo.",

  "privacy.request.status.approved": "Aprobada",
  "privacy.request.status.rejected": "Rechazada",
  "privacy.request.status.processing": "En curso",
  "privacy.consent.pending": "A la espera de su decisión",
  "network.scope.view_wellness_summary": "Ver un resumen de mi bienestar",
  "network.scope.receive_urgent_alerts":
    "Recibir avisos urgentes que yo elija enviar",
  "network.scope.view_relapse_plan_safe":
    "Ver las partes seguras de mi plan de prevención",
  "network.scope.receive_checkin_summary":
    "Recibir un resumen de mis check-ins",
  "network.password": "Su contraseña",
  "network.password.note":
    "Para cambiar lo que alguien ve, confirme con su contraseña.",
  "gate.consent.title": "Antes de empezar",
  "gate.consent.intro":
    "Lea y acepte el documento de abajo para usar la aplicación.",
  "gate.consent.progress": "Documento {current} de {total}",
  "gate.consent.version": "Versión {version}",
  "gate.consent.refusal": "Si no acepta: {text}",
  "gate.consent.accept": "Lo leí y acepto",
  "gate.consent.signout": "Salir sin aceptar",
  "learn.title": "Para aprender",
  "learn.recommended": "Recomendados por el equipo",
  "learn.all": "Biblioteca",
  "learn.none": "Ningún contenido disponible.",
  "learn.kind.article": "Texto",
  "learn.kind.video": "Video",
  "learn.kind.audio": "Audio",
  "learn.kind.exercise": "Práctica",
  "learn.minutes": "{count} min",
  "learn.recommendedBy": "Recomendado por {name}",
  "learn.objective": "Para qué: {objective}",
  "learn.source": "Fuente: {source}",
  "learn.care": "Precauciones",
  "learn.favorite": "Añadir a favoritos",
  "learn.unfavorite": "Quitar de favoritos",
  "learn.markRead": "Marcar como leído",
  "learn.read": "Leído",
  "learn.notice":
    "Contenido informativo. No sustituye la orientación de tu equipo de salud.",

  // ── Perfil, privacidad y ajustes ──────────────────────────────────────────
  "profile.title": "Perfil",
  "profile.discharge": "Alta el {date}",
  "profile.team": "Mi equipo",
  "profile.role.psychiatrist": "Psiquiatría",
  "profile.role.psychologist": "Psicología",
  "profile.role.nurse": "Enfermería",
  "profile.role.pharmacist": "Farmacia",
  "profile.role.other": "Equipo",
  "profile.psychotherapyNote":
    "Las anotaciones de psicoterapia están restringidas a tu psicólogo y a ti. Ninguna otra área de la clínica las ve.",

  "settings.title": "Ajustes",
  "settings.language": "Idioma",
  "settings.language.note":
    "Cambia solo el idioma de la interfaz. Tus relatos, historia clínica y textos del equipo no se traducen.",
  "settings.appearance": "Apariencia",
  "settings.theme.system": "Automático",
  "settings.theme.light": "Claro",
  "settings.theme.dark": "Oscuro",
  "settings.reminders": "Recordatorios",
  "settings.reminders.off":
    "Los recordatorios por notificación aún no están activos en esta aplicación. No pide permiso de notificaciones.",
  "settings.storage":
    "En este dispositivo se guardan el idioma, la apariencia y, si iniciaste sesión, tu sesión en el almacén seguro del dispositivo. Aquí no se almacena ningún dato de salud.",
  "settings.storageError":
    "No se pudo guardar la preferencia en este dispositivo. Vale solo para esta sesión.",
  "settings.about": "Acerca de esta aplicación",
  "settings.about.body":
    "Aurora Elo Post-Alta apoya tu cuidado después de la internación. No hace diagnósticos, no sustituye la atención profesional y no es un servicio de emergencia.",
  "settings.mode.preview": "Modo demostración (datos ficticios)",
  "settings.mode.live": "Modo clínica",

  "privacy.title": "Privacidad y consentimientos",
  "privacy.intro":
    "Tú controlas cómo se usan tus datos. Cada autorización tiene una versión y una fecha, y puede revisarse.",
  "privacy.consents": "Autorizaciones",
  "privacy.consent.terms_of_use": "Términos de uso",
  "privacy.consent.clinical_limits": "Límites de la atención digital",
  "privacy.consent.clinical_follow_up": "Seguimiento clínico",
  "privacy.consent.communication": "Comunicación con el equipo",
  "privacy.consent.granted": "Autorizado",
  "privacy.consent.revoked": "Revocado",
  "privacy.consent.mandatory": "Necesario para usar la aplicación",
  "privacy.consent.version": "Versión {version} • {date}",
  "privacy.consent.revoke": "Revocar",
  "privacy.consent.grant": "Autorizar de nuevo",
  "privacy.rights": "Tus derechos (LGPD)",
  "privacy.rights.intro":
    "Pide una copia, corrección o eliminación de tus datos. La clínica confirma tu identidad antes de responder.",
  "privacy.request.confirmation": "Confirmar que tratan mis datos",
  "privacy.request.access": "Acceder a mis datos",
  "privacy.request.correction": "Corregir mis datos",
  "privacy.request.portability": "Llevarme mis datos",
  "privacy.request.revocation": "Revocar autorizaciones",
  "privacy.request.erasure": "Pedir eliminación",
  "privacy.request.open": "Solicitar",
  "privacy.request.status.identity_pending":
    "Esperando confirmación de identidad",
  "privacy.request.status.in_review": "En análisis",
  "privacy.request.status.completed": "Concluida",
  "privacy.request.sent":
    "Pedido registrado en la demostración. En producción, la clínica confirma tu identidad antes de cualquier respuesta.",
  "privacy.request.duplicate": "Ya hay un pedido de este tipo en curso.",
  "privacy.requests": "Mis pedidos",
  "privacy.requests.none": "Ningún pedido hecho.",
  "privacy.mandatoryNote":
    "Las autorizaciones necesarias no pueden revocarse aquí. Para dejar de usar el servicio, haz un pedido de revocación.",
  // ── Gravaciones y carga (modo live) ─────────────────────────────────────
  "mode.action.offline":
    "Sin conexión con la clínica ahora. No se guardó nada. Inténtalo de nuevo cuando vuelva internet.",
  "mode.action.rejected":
    "No se pudo guardar. Revisa la información e inténtalo de nuevo. No se cambió nada.",
  "mode.action.session":
    "Tu sesión terminó. Inicia sesión de nuevo para continuar. No se guardó nada.",
  "mode.action.blocked":
    "El acceso a tu cuidado está suspendido temporalmente por la clínica. Habla con la clínica. La ayuda urgente sigue disponible.",
  "mode.action.server":
    "El servidor no pudo completar esto ahora. Inténtalo en un momento. Comprueba si el registro aparece antes de repetirlo.",
  "data.loading": "Cargando tus datos…",
  "data.error.title": "No se pudo cargar",
  "data.error.stale":
    "No se pudo actualizar ahora. Estás viendo lo que ya se había cargado.",
  "data.retry": "Intentar de nuevo",

  // ── Mensajes por código de error del servidor ───────────────────────────
  "error.code.network":
    "Sin conexión con el servidor ahora. Revisa tu internet e inténtalo de nuevo.",
  "error.code.invalid_credentials":
    "El correo o la contraseña no coinciden. Revísalos e inténtalo de nuevo.",
  "error.code.rate_limited":
    "Demasiados intentos en poco tiempo. Espera unos minutos e inténtalo de nuevo.",
  "error.code.clinic_choice_required": "Elige la clínica para continuar.",
  "error.code.invalid_token":
    "Tu sesión terminó. Inicia sesión de nuevo para continuar.",
  "error.code.not_found":
    "No encontramos este elemento. Actualiza la pantalla e inténtalo de nuevo.",
  "error.code.invalid_dose_time":
    "Esta hora no corresponde a una dosis prevista de este medicamento.",
  "error.code.timezone_required":
    "Falta la zona horaria en tu registro. Pide a la clínica que lo corrija.",
  "error.code.plan_closed":
    "Este plan ya está cerrado y no acepta una nueva respuesta.",
  "error.code.invalid_date":
    "Esta fecha no se puede usar aquí. Elige una fecha dentro del período permitido.",
  "error.code.not_scheduled": "Este hábito no está previsto para este día.",
  "error.code.already_completed":
    "Esto ya se completó y no se puede enviar de nuevo.",
  "error.code.invalid_response":
    "La respuesta no está en un formato aceptado. Revísala e inténtalo de nuevo.",
  "error.code.unsupported":
    "Este tipo de actividad aún no se puede hacer en la aplicación.",
  "error.code.no_actions_configured":
    "El equipo aún no definió las acciones del modo de poca energía.",
  "error.code.invalid_intensity": "La intensidad debe estar entre 1 y 10.",
  "error.code.invalid_scope": "Este permiso no está disponible.",
  "error.code.reauthentication_failed":
    "La contraseña no coincidió. No se cambió nada.",
  "error.code.consent_rejected":
    "No se pudo registrar tu decisión. No se cambió nada.",
  "error.code.revocation_rejected":
    "Esta autorización no se puede revocar aquí.",
  "error.code.already_open": "Ya hay un pedido de este tipo en curso.",
  "error.code.rejected": "La clínica no aceptó esta solicitud.",
  "error.code.slot_unavailable": "Este horario ya no está libre. Elige otro.",
  "error.code.weak_password":
    "Esta contraseña no fue aceptada. Mira qué falta e inténtalo de nuevo.",
  "error.code.invalid_code":
    "Este código no es válido o ya venció. Pide una nueva invitación a la clínica o, en la recuperación de contraseña, solicita un nuevo código.",
  "error.code.invalid_contact":
    "Revise el nombre, la relación y el mensaje de la persona.",
  "error.code.invalid_focus": "Indique sobre qué es la meta.",
  "error.code.invalid_phone":
    "Revise el teléfono: use solo números, +, espacios, paréntesis y guion.",
  "error.code.invalid_section_type": "Esta parte del plan no existe.",
  "error.code.already_exists": "Ya tiene una meta de recuperación activa.",
  "error.code.limit_reached":
    "Ha llegado al límite. Quite uno para añadir otro.",
  "error.code.clinic_blocked":
    "El acceso a tu cuidado está suspendido temporalmente por la clínica. Habla con la clínica.",
  "error.code.unknown":
    "No se pudo completar. Inténtalo de nuevo en un momento.",

  // ── Configuración del servidor ──────────────────────────────────────────
  "config.missing.title": "Aplicación sin configurar",
  "config.missing.body":
    "Esta versión de la aplicación no sabe con qué servidor hablar, así que no puede iniciar sesión ni mostrar tus datos. No se muestra, guarda ni envía nada. Avisa a quien te dio esta aplicación.",
  "config.missing.help":
    "La ayuda urgente funciona con normalidad, sin conexión.",
  "config.missing.dev":
    "Para quien desarrolla: define EXPO_PUBLIC_API_BASE_URL con la dirección https del servidor y reinicia la aplicación.",

  // ── Acceso: entrar, activar cuenta y recuperar contraseña ───────────────
  "auth.restoring": "Abriendo tu cuenta…",
  "auth.signin.title": "Entrar",
  "auth.signin.intro":
    "Entra con el correo y la contraseña de tu cuenta para ver tu cuidado.",
  "auth.email": "Correo electrónico",
  "auth.password": "Contraseña",
  "auth.password.show": "Mostrar contraseña",
  "auth.password.hide": "Ocultar contraseña",
  "auth.signin.submit": "Entrar",
  "auth.forgot": "Olvidé mi contraseña",
  "auth.haveCode": "Recibí un código de invitación",
  "auth.clinic.title": "¿En qué clínica quieres entrar?",
  "auth.clinic.hint":
    "Tu cuenta está vinculada a más de una clínica. Elige una para continuar.",
  "auth.clinic.label": "Clínica",
  "auth.help.note":
    "La ayuda urgente funciona sin iniciar sesión y sin internet.",
  "auth.notice.expired":
    "Tu sesión terminó. Inicia sesión de nuevo para continuar.",
  "auth.notice.reset": "Contraseña cambiada. Entra con la nueva contraseña.",
  "auth.activate.title": "Activar cuenta",
  "auth.activate.intro":
    "Usa el código de la invitación que envió la clínica. Si abriste el enlace del correo, el código ya viene completado.",
  "auth.activate.code": "Código de invitación",
  "auth.activate.firstName": "Nombre",
  "auth.activate.lastName": "Apellido",
  "auth.activate.password": "Contraseña",
  "auth.activate.existing":
    "Si ya tienes una cuenta de Aurora Elo, escribe tu contraseña actual y deja el nombre y el apellido en blanco. Si la cuenta es nueva, elige una contraseña que solo tú conozcas.",
  "auth.activate.submit": "Activar y entrar",
  "auth.recover.title": "Recuperar contraseña",
  "auth.recover.intro":
    "Escribe el correo de tu cuenta. Si está registrado, enviaremos un código y un enlace para crear una nueva contraseña.",
  "auth.recover.submit": "Enviar instrucciones",
  "auth.recover.sent":
    "Listo. Si este correo está registrado, recibirás las instrucciones en unos instantes. Revisa también la carpeta de spam.",
  "auth.recover.haveCode": "Ya recibí el código",
  "auth.reset.title": "Crear una nueva contraseña",
  "auth.reset.intro":
    "Pega el código que llegó por correo y elige una nueva contraseña. Si abriste el enlace del correo, el código ya viene completado.",
  "auth.reset.code": "Código recibido por correo",
  "auth.reset.newPassword": "Nueva contraseña",
  "auth.reset.submit": "Guardar nueva contraseña",
  "auth.reset.note":
    "Al cambiar la contraseña, se cierra la sesión en todos los demás dispositivos.",
  "auth.backToSignin": "Volver a entrar",
  "auth.codeFilled":
    "Completamos el código a partir del enlace. Puedes corregirlo si lo necesitas.",

  // ── Perfil: salir de este dispositivo ───────────────────────────────────
  "profile.session": "Cuenta en este dispositivo",
  "profile.logout": "Salir",
  "profile.logout.subtitle": "Cierra la sesión en este dispositivo",
  "profile.logout.confirm": "¿Salir de este dispositivo?",
  "profile.logout.body":
    "Tendrás que entrar de nuevo para ver tu cuidado. La ayuda urgente sigue disponible sin iniciar sesión.",
  "profile.logout.working": "Saliendo…",
  "profile.logoutOthers": "Salir de los otros dispositivos",
  "profile.logoutOthers.subtitle":
    "Cierra la sesión en todos los demás dispositivos",
  "profile.logoutOthers.confirm": "¿Salir de los otros dispositivos?",
  "profile.logoutOthers.body":
    "Quien esté usando tu cuenta en otro dispositivo tendrá que entrar de nuevo. Este dispositivo sigue conectado.",
  "profile.logoutOthers.done_one":
    "Se cerró la sesión en {count} otro dispositivo.",
  "profile.logoutOthers.done_other":
    "Se cerró la sesión en {count} otros dispositivos.",
  "profile.logoutOthers.none": "No había otros dispositivos conectados.",
};
