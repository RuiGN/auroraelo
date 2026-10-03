import { Messages } from "./pt-br";

/** English (en). Keys must match pt-br.ts exactly (enforced by the Messages type). */
export const en: Messages = {
  // ── Brand and general ─────────────────────────────────────────────────────
  "brand.tagline": "Your care after discharge",
  "common.cancel": "Cancel",
  "common.close": "Close",
  "common.send": "Send",
  "common.back": "Back",
  "common.confirm": "Confirm",
  "common.done": "Done",
  "common.optional": "optional",
  "common.today": "Today",
  "common.tomorrow": "Tomorrow",
  "common.yesterday": "Yesterday",
  "common.call": "Call",
  "common.loading": "Loading…",
  "common.version": "Version {version}",

  // ── Navigation ────────────────────────────────────────────────────────────
  "nav.home": "Today",
  "nav.care": "Care",
  "nav.diary": "Diary",
  "nav.agenda": "Agenda",
  "nav.support": "Support",
  "nav.help": "Help",
  "nav.profile": "Profile",

  // ── Mode and availability ─────────────────────────────────────────────────
  "mode.preview.banner":
    "Demo with made-up data. Nothing is saved, sent or real.",
  "mode.unavailable.title": "Not connected to your clinic yet",
  "mode.unavailable.body":
    "This area will show your care data once the app is securely connected to your clinic. For now nothing is shown, saved or sent.",
  "mode.unavailable.help":
    "The Help button and the language and appearance settings work normally.",
  "mode.action.unavailable":
    "This action is not available in the app yet. Nothing was saved or sent.",
  "mode.action.invalid": "Check the fields and try again. Nothing was saved.",
  "mode.preview.saved":
    "Recorded in the demo. It was not saved or sent to anyone.",

  // ── Home ──────────────────────────────────────────────────────────────────
  "home.greeting.morning": "Good morning, {name}",
  "home.greeting.afternoon": "Good afternoon, {name}",
  "home.greeting.evening": "Good evening, {name}",
  "home.sinceDischarge_one": "It has been {count} day since your discharge",
  "home.sinceDischarge_other": "It has been {count} days since your discharge",
  "home.dischargeToday": "Today is your discharge day",
  "home.today": "Your day",
  "home.checkIn.todo": "Log how you are feeling",
  "home.checkIn.done": "Today's check-in is done",
  "home.medications": "Today's medications",
  "home.medications.count": "{done} of {total} logged",
  "home.medications.none": "No medications today",
  "home.habits": "Today's routine",
  "home.habits.count": "{done} of {total} done",
  "home.exercise": "Exercise from your team",
  "home.exercise.due": "Due {date}",
  "home.exercise.none": "No pending exercises",
  "home.nextAppointment": "Next appointment",
  "home.nextAppointment.none": "No appointment scheduled",
  "home.lowEnergy.title": "Low-energy day?",
  "home.lowEnergy.body":
    "That is okay. Keep to the essentials today. The rest can wait.",
  "home.lowEnergy.activate": "Turn on light mode",
  "home.lowEnergy.deactivate": "Back to normal",
  "home.lowEnergy.active": "Light mode on",
  "home.lowEnergy.actions": "Today's essentials",
  "home.quick.craving": "I feel like using",
  "home.quick.diary": "Write in my diary",
  "home.goalFocus": "Goal in progress",
  "home.recoveryDays_one": "{count} day in recovery",
  "home.recoveryDays_other": "{count} days in recovery",
  "home.recovery.hidden": "Counter hidden by you",

  // ── Urgent help ───────────────────────────────────────────────────────────
  "help.title": "I need help now",
  "help.disclaimer":
    "This app is not an emergency service and does not monitor you in real time. Nobody is alerted when you open this screen. In immediate danger, call your emergency service now.",
  "help.emergency": "Emergency and support",
  "help.number.medical": "SAMU — medical emergency",
  "help.number.fire": "Fire department",
  "help.number.police": "Police",
  "help.number.emotional": "CVV — emotional support, 24 hours",
  "help.number.call": "Call {label} at {number}",
  "help.people": "People you trust",
  "help.people.none": "You have not added trusted people with your team yet.",
  "help.people.sms": "Send a message",
  "help.plan": "My plan for hard moments",
  "help.calm": "Before deciding anything",
  "help.breathing.title": "Breathe calmly",
  "help.breathing.start": "Start breathing",
  "help.breathing.stop": "Stop",
  "help.breathing.inhale": "Breathe in slowly",
  "help.breathing.exhale": "Breathe out slowly",
  "help.breathing.note": "Stop if you feel dizzy. You can leave at any time.",
  "help.grounding.title": "5-4-3-2-1: come back to the here and now",
  "help.grounding.step5": "Look around and name 5 things you can see",
  "help.grounding.step4": "Touch 4 things and notice their texture",
  "help.grounding.step3": "Listen for 3 sounds around you",
  "help.grounding.step2": "Notice 2 smells",
  "help.grounding.step1": "Notice 1 taste in your mouth",
  "help.grounding.note":
    "A general support exercise. It does not replace professional care.",
  "help.noOneNotified": "Nobody was notified by this app.",
  "help.preview.note":
    "In demo mode, the trusted people below are made up. The emergency numbers are real.",
  "help.openFailed":
    "Could not open the dialer on this device. Dial the number manually.",

  // ── Care ──────────────────────────────────────────────────────────────────
  "care.plan": "Care plan",
  "care.plan.subtitle": "What your team agreed with you",
  "care.medications": "Medications",
  "care.medications.subtitle": "Times and logging",
  "care.routine": "Routine",
  "care.routine.subtitle": "Habits that protect your day",
  "care.exercises": "Team exercises",
  "care.exercises.subtitle": "Activities to do at home",
  "care.relapse": "Relapse prevention plan",
  "care.relapse.subtitle": "Triggers, signs and what to do",
  "care.goals": "Goals",
  "care.goals.subtitle": "Small steps, one at a time",

  "plan.status.draft": "Draft",
  "plan.status.pending_signature": "Awaiting signature",
  "plan.status.active": "Active",
  "plan.status.paused": "Paused",
  "plan.status.completed": "Completed",
  "plan.status.revoked": "Revoked",
  "plan.objective": "Objective",
  "plan.actions": "What to do",
  "plan.mandatory": "Essential",
  "plan.contraindications": "Precautions",
  "plan.version": "Version {version} • valid from {date}",
  "plan.by": "Prescribed by {name}",
  "plan.respond": "Your response to the plan",
  "plan.respond.badge": "Respond",
  "plan.respond.hint":
    "You can accept, pause, decline or ask your team for a review.",
  "plan.decision.accepted": "Accept",
  "plan.decision.paused": "Pause",
  "plan.decision.refused": "Decline",
  "plan.decision.review_requested": "Ask for review",
  "plan.notes": "Notes for your team",
  "plan.responded": "You responded: {decision}",
  "plan.responded.at": "on {date}",
  "plan.responded.note":
    "Your team only sees this response once it is sent to the clinic. The app does not alert anyone in real time.",

  "meds.title": "Medications",
  "meds.today": "Today",
  "meds.none": "No medications prescribed.",
  "meds.taken": "Taken",
  "meds.late": "Taken late",
  "meds.omitted": "Not taken",
  "meds.undo": "Undo",
  "meds.status.taken": "Taken",
  "meds.status.late": "Taken late",
  "meds.status.omitted": "Not taken",
  "meds.status.pending": "Pending",
  "meds.prescribedBy": "Prescribed by {name}",
  "meds.until": "until {date}",
  "meds.continuous": "ongoing use",
  "meds.safety":
    "This log is yours. If you have a question about a dose, an uncomfortable effect or a missed dose, talk to your health team before changing anything.",
  "meds.route.oral": "by mouth",
  "meds.route.sublingual": "under the tongue",
  "meds.route.topical": "topical",
  "meds.route.inhalation": "inhaled",
  "meds.route.injectable": "injection",
  "meds.route.ophthalmic": "eye use",
  "meds.route.nasal": "nasal",
  "meds.route.other": "other route",
  "meds.schedule": "Times",

  "routine.title": "Routine",
  "routine.hint": "Mark what you managed. Doing part of it counts too.",
  "routine.status.completed": "Done",
  "routine.status.partial": "Partly",
  "routine.status.postponed": "Postponed",
  "routine.status.skipped": "Skipped",
  "routine.window.morning": "Morning",
  "routine.window.afternoon": "Afternoon",
  "routine.window.evening": "Early evening",
  "routine.window.night": "Night",
  "routine.window.any_time": "Any time",
  "routine.none": "No habits agreed yet.",

  "exercise.title": "Team exercises",
  "exercise.pending": "To do",
  "exercise.completed": "Completed",
  "exercise.none": "No exercises assigned.",
  "exercise.minutes": "{count} min",
  "exercise.frequency": "Frequency: {value}",
  "exercise.assignedBy": "Assigned by {name}",
  "exercise.response": "Your response",
  "exercise.response.scale": "Choose from 1 (very little) to 5 (a lot)",
  "exercise.response.text": "Write in your own words",
  "exercise.complete": "Complete exercise",
  "exercise.visibility": "Who can see your response",
  "exercise.doneAt": "Completed on {date}",

  "relapse.title": "Relapse prevention plan",
  "relapse.intro":
    "A plan made by you and your team for risky moments. Reading it calmly now helps you remember it in a hard moment.",
  "relapse.reviewed": "Reviewed on {date}",
  "relapse.never": "Not reviewed yet",
  "relapse.none": "You haven't created your plan yet.",
  "relapse.section.triggers": "Triggers",
  "relapse.section.early_warning_signs": "Warning signs",
  "relapse.section.protective_factors": "What protects me",
  "relapse.section.coping_strategies": "What I can do in the moment",
  "relapse.section.safe_environments": "Safe places",
  "relapse.section.support_contacts": "People who support me",
  "relapse.section.professional_resources": "Professional help",
  "relapse.restartNote":
    "Starting again is part of the journey. Talk to your team when you need to.",

  "plans.private":
    "Only you see what is here. The team receives nothing when you save.",
  "plans.save": "Save",
  "plans.saved": "Saved.",
  "recovery.goal.title": "My recovery goal",
  "recovery.goal.define": "Set my goal",
  "recovery.goal.intro":
    "Choose what makes sense for you. You can adjust it later, with no guilt.",
  "recovery.goal.type": "Type of goal",
  "recovery.goal.type.abstinence": "Stay without",
  "recovery.goal.type.reduction": "Cut down",
  "recovery.goal.type.moderation": "Moderate",
  "recovery.goal.focus": "About what?",
  "recovery.goal.focus.help":
    "For example: alcohol, gambling or another substance.",
  "recovery.goal.motivations": "Why does this matter to you?",
  "recovery.goal.since": "Count from",
  "recovery.goal.since.today": "Today",
  "recovery.goal.since.yesterday": "Yesterday",
  "recovery.goal.since.week": "7 days ago",
  "recovery.goal.since.month": "30 days ago",
  "recovery.goal.hide": "Hide the day counter",
  "recovery.goal.submit": "Save my goal",
  "relapse.edit": "Edit my plan",
  "relapse.create": "Create my plan",
  "relapse.edit.title": "My prevention plan",
  "relapse.edit.intro":
    "Write it in your own words. Leave blank whatever you don't want to fill in right now.",
  "urgent.edit.title": "My urgent support plan",
  "urgent.edit.subtitle": "Trusted people and what helps you calm down",
  "urgent.instructions": "What I want to remember in these moments",
  "urgent.strategies": "What helps me calm down (one per line)",
  "urgent.contacts": "Trusted people",
  "urgent.contact.add": "Add person",
  "urgent.contact.edit": "Edit",
  "urgent.contact.remove": "Remove",
  "urgent.contact.name": "Name",
  "urgent.contact.relationship": "Relationship (e.g. mother, friend)",
  "urgent.contact.phone": "Phone",
  "urgent.contact.message": "Ready-made message (optional)",
  "urgent.contact.save": "Save person",
  "urgent.contact.limit":
    "You already have 5 people. Remove one to add another.",
  "urgent.note":
    "Saving does not notify anyone. A call only happens when you tap the number.",
  "lowenergy.edit.title": "My low-energy actions",
  "lowenergy.edit.intro": "Up to three very small things for hard days.",
  "lowenergy.edit.action": "Action {n}",
  "lowenergy.edit.entry": "Choose my actions",
  "goals.title": "Goals",
  "goals.active": "In progress",
  "goals.other": "Paused and completed",
  "goals.none": "No goals set yet.",
  "goals.steps": "{done} of {total} steps",
  "goals.due": "By {date}",
  "goals.horizon.short": "Short term",
  "goals.horizon.medium": "Medium term",
  "goals.horizon.long": "Long term",
  "goals.status.active": "In progress",
  "goals.status.paused": "Paused",
  "goals.status.completed": "Completed",
  "goals.status.archived": "Archived",
  "goals.pause": "Pause goal",
  "goals.resume": "Resume goal",
  "goals.complete": "Complete goal",

  // ── Diary ─────────────────────────────────────────────────────────────────
  "diary.checkIn": "How I am today",
  "diary.checkIn.subtitle": "A quick log, once a day",
  "diary.checkIn.doneToday":
    "You already logged today. Sending again replaces today's entry.",
  "diary.write": "Write in my diary",
  "diary.write.subtitle": "Mood, emotions and what happened",
  "diary.craving": "Urge to use",
  "diary.craving.subtitle": "Log it and use your strategies",
  "diary.entries": "Latest entries",
  "diary.entries.none": "Your entries will appear here.",
  "diary.recovery": "My recovery journey",
  "access.title": "Team requests",
  "access.from": "{name} asks to see one of your entries",
  "access.entry": "Entry from {date}",
  "access.note": "It's up to you. If you don't answer, nothing is shared.",
  "access.approve": "Allow",
  "access.deny": "Don't allow",
  "access.approved": "Request approved.",
  "access.denied": "Request declined.",
  "diary.privacy":
    "Your diary is private by default. You choose whether each entry can be shared with your team.",

  "checkin.title": "How I am today",
  "checkin.intro": "Answer from 1 to 5. There is no right answer.",
  "checkin.scale.low": "Very low",
  "checkin.scale.high": "Very high",
  "checkin.q.general_state": "How would you rate your general state today?",
  "checkin.q.anxiety": "Anxiety level today",
  "checkin.q.sadness": "Feeling of sadness or low mood",
  "checkin.q.irritability": "Level of irritability or impatience",
  "checkin.q.energy": "Energy level",
  "checkin.q.sleep_quality": "Quality of your sleep last night",
  "checkin.q.motivation": "Motivation for your day",
  "checkin.notes": "Notes",
  "checkin.notes.placeholder": "Anything you want to note about the day",
  "checkin.visibility": "Share this entry with your team?",
  "checkin.submit": "Save today's entry",
  "checkin.missing": "Answer every question from 1 to 5 to save.",
  "checkin.saved":
    "Today's entry saved. Your team does not follow this app in real time.",
  "checkin.support.title": "This seems like a hard day",
  "checkin.support.body":
    "You do not have to go through this without support. Reach out to someone you trust or use the Help button if you need help now.",
  "checkin.support.cta": "Open help",

  "entry.title": "New diary entry",
  "entry.mood": "How is your mood?",
  "entry.mood.1": "Very bad",
  "entry.mood.2": "Bad",
  "entry.mood.3": "So-so",
  "entry.mood.4": "Good",
  "entry.mood.5": "Very good",
  "entry.emotions": "What did you feel?",
  "entry.intensity": "Intensity (1 to 5)",
  "entry.context": "What happened?",
  "entry.context.placeholder": "Tell it in your own words",
  "entry.triggers": "What may have set it off?",
  "entry.reactions": "How did you react?",
  "entry.strategies": "What helped?",
  "entry.visibility": "Who can see this entry",
  "entry.submit": "Save to diary",
  "entry.saved": "Entry saved to your diary.",
  "entry.context.required": "Write at least one line about what happened.",
  "entry.detail": "Entry",
  "entry.emotion.anxiety": "Anxiety",
  "entry.emotion.sadness": "Sadness",
  "entry.emotion.anger": "Anger",
  "entry.emotion.joy": "Joy",
  "entry.emotion.fear": "Fear",
  "entry.emotion.calm": "Calm",
  "entry.emotion.frustration": "Frustration",
  "entry.emotion.hope": "Hope",

  "visibility.private": "Only me",
  "visibility.private.hint": "It stays with you.",
  "visibility.shareable": "I can share with my team",
  "visibility.shareable.hint": "Your team will be able to see this entry.",
  "visibility.confirmation_required": "Ask me first",
  "visibility.confirmation_required.hint":
    "Your team only sees it after you approve an access request.",

  "craving.title": "Urge to use",
  "craving.intro":
    "Feeling an urge to use is common and usually passes. You do not have to handle it alone.",
  "craving.intensity": "How strong is it right now? (1 to 10)",
  "craving.context": "What is going on?",
  "craving.strategy": "What did you do or will you do?",
  "craving.suggestions": "From your plan",
  "craving.suggestions.none":
    "Once your prevention plan is ready, your strategies will appear here.",
  "craving.breathe": "Breathe now",
  "craving.callSomeone": "Call someone you trust",
  "craving.submit": "Log it",
  "craving.saved":
    "Entry saved. If the urge gets too strong, use the Help button.",
  "craving.history": "Earlier entries",
  "craving.level": "Intensity {value} of 10",

  "recovery.title": "My counter",
  "recovery.days_one": "{count} day",
  "recovery.days_other": "{count} days",
  "recovery.since": "since {date}",
  "recovery.hide": "Hide counter",
  "recovery.show": "Show counter",
  "recovery.hidden": "Counter hidden. You decide when to see it.",
  "recovery.motivations": "What motivates me",
  "recovery.restart": "Restart the count",
  "recovery.restart.confirm": "Restart the count today?",
  "recovery.restart.body":
    "Starting again is part of the journey and does not erase what you learned. If you like, talk to your team about what happened.",
  "recovery.restart.count_one": "{count} restart",
  "recovery.restart.count_other": "{count} restarts",
  "recovery.focus": "Focus: {focus}",

  // ── Agenda ────────────────────────────────────────────────────────────────
  "agenda.title": "Agenda",
  "agenda.upcoming": "Upcoming",
  "agenda.past": "Past",
  "agenda.none": "No appointments here.",
  "agenda.request": "Request appointment",
  "agenda.status.requested": "Awaiting confirmation",
  "agenda.status.confirmed": "Confirmed",
  "agenda.status.reschedule_requested": "Reschedule requested",
  "agenda.status.canceled": "Canceled",
  "agenda.status.completed": "Completed",
  "agenda.status.no_show": "Did not attend",
  "agenda.with": "with {name}",
  "agenda.at": "{unit}",
  "agenda.reschedule": "Ask to reschedule",
  "agenda.reschedule.pick": "Choose the new time",
  "agenda.reschedule.none":
    "There are no free times to reschedule right now. Please contact the clinic.",
  "agenda.reschedule.submit": "Request reschedule",
  "agenda.cancel": "Cancel appointment",
  "agenda.cancel.confirm": "Cancel this appointment?",
  "agenda.cancel.reason": "Reason (optional)",
  "agenda.rescheduleNote":
    "A reschedule request only counts once the clinic replies. Until then the original appointment stays booked.",
  "agenda.request.title": "Request appointment",
  "agenda.request.service": "Type of care",
  "agenda.request.slot": "Free times",
  "agenda.request.noSlots": "No free times right now. Contact the clinic.",
  "agenda.request.submit": "Request this time",
  "agenda.request.note":
    "The request waits for the clinic to confirm. It is only confirmed once you receive the reply.",
  "agenda.request.sent":
    "Request recorded. Wait for the clinic's confirmation.",

  // ── Support ───────────────────────────────────────────────────────────────
  "support.network": "My support network",
  "support.network.subtitle": "Who follows along and what they can see",
  "support.learn": "To learn",
  "support.learn.subtitle": "Recommended reading and practices",

  "network.title": "My support network",
  "network.intro":
    "People you authorized to follow part of your journey. You decide what each one can see.",
  "network.none": "You have not invited anyone yet.",
  "network.revoke": "End access",
  "network.revoked": "Access ended",
  "network.revoke.confirm": "End access for {name}?",
  "network.diary": "Your diary is never shared with your support network.",

  "privacy.request.status.approved": "Approved",
  "privacy.request.status.rejected": "Declined",
  "privacy.request.status.processing": "In progress",
  "privacy.consent.pending": "Waiting for your decision",
  "network.scope.view_wellness_summary": "See a summary of my well-being",
  "network.scope.receive_urgent_alerts":
    "Receive urgent alerts that I choose to send",
  "network.scope.view_relapse_plan_safe":
    "See the safe parts of my prevention plan",
  "network.scope.receive_checkin_summary": "Receive a summary of my check-ins",
  "network.password": "Your password",
  "network.password.note":
    "To change what someone can see, confirm with your password.",
  "gate.consent.title": "Before you start",
  "gate.consent.intro": "Read and accept the document below to use the app.",
  "gate.consent.progress": "Document {current} of {total}",
  "gate.consent.version": "Version {version}",
  "gate.consent.refusal": "If you do not accept: {text}",
  "gate.consent.accept": "I have read and accept",
  "gate.consent.signout": "Sign out without accepting",
  "learn.title": "To learn",
  "learn.recommended": "Recommended by your team",
  "learn.all": "Library",
  "learn.none": "No content available.",
  "learn.kind.article": "Article",
  "learn.kind.video": "Video",
  "learn.kind.audio": "Audio",
  "learn.kind.exercise": "Practice",
  "learn.minutes": "{count} min",
  "learn.recommendedBy": "Recommended by {name}",
  "learn.objective": "Why: {objective}",
  "learn.source": "Source: {source}",
  "learn.care": "Precautions",
  "learn.favorite": "Add to favorites",
  "learn.unfavorite": "Remove from favorites",
  "learn.markRead": "Mark as read",
  "learn.read": "Read",
  "learn.notice":
    "Informational content. It does not replace your health team's guidance.",

  // ── Profile, privacy and settings ─────────────────────────────────────────
  "profile.title": "Profile",
  "profile.discharge": "Discharged on {date}",
  "profile.team": "My team",
  "profile.role.psychiatrist": "Psychiatry",
  "profile.role.psychologist": "Psychology",
  "profile.role.nurse": "Nursing",
  "profile.role.pharmacist": "Pharmacy",
  "profile.role.other": "Team",
  "profile.psychotherapyNote":
    "Psychotherapy notes are restricted to your psychologist and you. No other area of the clinic sees them.",

  "settings.title": "Settings",
  "settings.language": "Language",
  "settings.language.note":
    "Changes only the interface language. Your own entries, medical record and team texts are not translated.",
  "settings.appearance": "Appearance",
  "settings.theme.system": "Automatic",
  "settings.theme.light": "Light",
  "settings.theme.dark": "Dark",
  "settings.reminders": "Reminders",
  "settings.reminders.off":
    "Notification reminders are not active in this app yet. It does not ask for notification permission.",
  "settings.storage":
    "This device keeps the language, the appearance and, if you signed in, your session in the device's secure vault. No health data is stored here.",
  "settings.storageError":
    "Could not save the preference on this device. It only applies to this session.",
  "settings.about": "About this app",
  "settings.about.body":
    "Aurora Elo Post-Discharge supports your care after inpatient treatment. It does not diagnose, does not replace professional care and is not an emergency service.",
  "settings.mode.preview": "Demo mode (made-up data)",
  "settings.mode.live": "Clinic mode",

  "privacy.title": "Privacy and consents",
  "privacy.intro":
    "You control how your data is used. Each authorization has a version and a date, and can be reviewed.",
  "privacy.consents": "Authorizations",
  "privacy.consent.terms_of_use": "Terms of use",
  "privacy.consent.clinical_limits": "Limits of digital care",
  "privacy.consent.clinical_follow_up": "Clinical follow-up",
  "privacy.consent.communication": "Communication with your team",
  "privacy.consent.granted": "Authorized",
  "privacy.consent.revoked": "Revoked",
  "privacy.consent.mandatory": "Required to use the app",
  "privacy.consent.version": "Version {version} • {date}",
  "privacy.consent.revoke": "Revoke",
  "privacy.consent.grant": "Authorize again",
  "privacy.rights": "Your rights (LGPD)",
  "privacy.rights.intro":
    "Ask for a copy, correction or deletion of your data. The clinic confirms your identity before replying.",
  "privacy.request.confirmation": "Confirm you process my data",
  "privacy.request.access": "Access my data",
  "privacy.request.correction": "Correct my data",
  "privacy.request.portability": "Take my data with me",
  "privacy.request.revocation": "Revoke authorizations",
  "privacy.request.erasure": "Request deletion",
  "privacy.request.open": "Request",
  "privacy.request.status.identity_pending": "Awaiting identity confirmation",
  "privacy.request.status.in_review": "Under review",
  "privacy.request.status.completed": "Completed",
  "privacy.request.sent":
    "Request recorded in the demo. In production the clinic confirms your identity before any reply.",
  "privacy.request.duplicate": "A request of this type is already in progress.",
  "privacy.requests": "My requests",
  "privacy.requests.none": "No requests made.",
  "privacy.mandatoryNote":
    "Required authorizations cannot be revoked here. To stop using the service, make a revocation request.",
  // ── Writes and loading (live mode) ──────────────────────────────────────
  "mode.action.offline":
    "No connection to the clinic right now. Nothing was saved. Try again when the internet is back.",
  "mode.action.rejected":
    "This could not be saved. Check the information and try again. Nothing was changed.",
  "mode.action.session":
    "Your session has ended. Sign in again to continue. Nothing was saved.",
  "mode.action.blocked":
    "Access to your care is temporarily suspended by the clinic. Please contact the clinic. Urgent help is still available.",
  "mode.action.server":
    "The server could not finish this right now. Try again in a moment. Check whether the entry appears before repeating it.",
  "data.loading": "Loading your data…",
  "data.error.title": "Could not load",
  "data.error.stale":
    "Could not refresh right now. You are seeing what was already loaded.",
  "data.retry": "Try again",

  // ── Messages by server error code ───────────────────────────────────────
  "error.code.network":
    "No connection to the server right now. Check your internet and try again.",
  "error.code.invalid_credentials":
    "The email or password does not match. Check them and try again.",
  "error.code.rate_limited":
    "Too many attempts in a short time. Wait a few minutes and try again.",
  "error.code.clinic_choice_required": "Choose the clinic to continue.",
  "error.code.invalid_token":
    "Your session has ended. Sign in again to continue.",
  "error.code.not_found":
    "We could not find this item. Refresh the screen and try again.",
  "error.code.invalid_dose_time":
    "This time does not match a scheduled dose of this medication.",
  "error.code.timezone_required":
    "Your record is missing a time zone. Please ask the clinic to fix it.",
  "error.code.plan_closed":
    "This plan is already closed and does not accept a new response.",
  "error.code.invalid_date":
    "This date cannot be used here. Choose a date within the allowed period.",
  "error.code.not_scheduled": "This habit is not planned for this day.",
  "error.code.already_completed":
    "This was already completed and cannot be sent again.",
  "error.code.invalid_response":
    "The response is not in an accepted format. Check it and try again.",
  "error.code.unsupported":
    "This type of activity cannot be done in the app yet.",
  "error.code.no_actions_configured":
    "The team has not set the low energy mode actions yet.",
  "error.code.invalid_intensity": "The intensity must be between 1 and 10.",
  "error.code.invalid_scope": "This permission is not available.",
  "error.code.reauthentication_failed":
    "The password did not match. Nothing was changed.",
  "error.code.consent_rejected":
    "Your decision could not be recorded. Nothing was changed.",
  "error.code.revocation_rejected":
    "This authorization cannot be revoked here.",
  "error.code.already_open": "A request of this type is already in progress.",
  "error.code.rejected": "The clinic did not accept this request.",
  "error.code.slot_unavailable":
    "This time slot is no longer free. Choose another one.",
  "error.code.weak_password":
    "This password was not accepted. See what is missing and try again.",
  "error.code.invalid_code":
    "This code is not valid or has expired. Ask the clinic for a new invitation or, for a password reset, request a new code.",
  "error.code.invalid_contact":
    "Check the person's name, relationship and message.",
  "error.code.invalid_focus": "Say what the goal is about.",
  "error.code.invalid_phone":
    "Check the phone number: use only digits, +, spaces, parentheses and hyphens.",
  "error.code.invalid_section_type": "This part of the plan does not exist.",
  "error.code.already_exists": "You already have an active recovery goal.",
  "error.code.limit_reached":
    "You have reached the limit. Remove one to add another.",
  "error.code.clinic_blocked":
    "Access to your care is temporarily suspended by the clinic. Please contact the clinic.",
  "error.code.unknown":
    "This could not be completed. Please try again in a moment.",

  // ── Server configuration ────────────────────────────────────────────────
  "config.missing.title": "App not configured",
  "config.missing.body":
    "This version of the app does not know which server to talk to, so it cannot sign in or show your data. Nothing is shown, saved or sent. Let whoever gave you this app know.",
  "config.missing.help":
    "Urgent help works normally, even without a connection.",
  "config.missing.dev":
    "For developers: set EXPO_PUBLIC_API_BASE_URL to the server's https address and restart the app.",

  // ── Sign-in: sign in, activate account and reset password ───────────────
  "auth.restoring": "Opening your account…",
  "auth.signin.title": "Sign in",
  "auth.signin.intro":
    "Sign in with your account email and password to see your care.",
  "auth.email": "Email",
  "auth.password": "Password",
  "auth.password.show": "Show password",
  "auth.password.hide": "Hide password",
  "auth.signin.submit": "Sign in",
  "auth.forgot": "I forgot my password",
  "auth.haveCode": "I received an invitation code",
  "auth.clinic.title": "Which clinic do you want to sign in to?",
  "auth.clinic.hint":
    "Your account is linked to more than one clinic. Choose one to continue.",
  "auth.clinic.label": "Clinic",
  "auth.help.note":
    "Urgent help works without signing in and without internet.",
  "auth.notice.expired": "Your session has ended. Sign in again to continue.",
  "auth.notice.reset": "Password changed. Sign in with your new password.",
  "auth.activate.title": "Activate account",
  "auth.activate.intro":
    "Use the invitation code the clinic sent you. If you opened the link in the email, the code is already filled in.",
  "auth.activate.code": "Invitation code",
  "auth.activate.firstName": "First name",
  "auth.activate.lastName": "Last name",
  "auth.activate.password": "Password",
  "auth.activate.existing":
    "If you already have an Aurora Elo account, enter your current password and leave the names blank. If the account is new, choose a password only you know.",
  "auth.activate.submit": "Activate and sign in",
  "auth.recover.title": "Reset password",
  "auth.recover.intro":
    "Enter your account email. If it is registered, we will send a code and a link to create a new password.",
  "auth.recover.submit": "Send instructions",
  "auth.recover.sent":
    "Done. If this email is registered, you will receive the instructions shortly. Check your spam folder too.",
  "auth.recover.haveCode": "I already have the code",
  "auth.reset.title": "Create a new password",
  "auth.reset.intro":
    "Paste the code that arrived by email and choose a new password. If you opened the link in the email, the code is already filled in.",
  "auth.reset.code": "Code received by email",
  "auth.reset.newPassword": "New password",
  "auth.reset.submit": "Save new password",
  "auth.reset.note":
    "When you change your password, you are signed out of all other devices.",
  "auth.backToSignin": "Back to sign in",
  "auth.codeFilled":
    "We filled in the code from the link. You can edit it if needed.",

  // ── Profile: sign out of this device ────────────────────────────────────
  "profile.session": "Account on this device",
  "profile.logout": "Sign out",
  "profile.logout.subtitle": "Ends the session on this device",
  "profile.logout.confirm": "Sign out of this device?",
  "profile.logout.body":
    "You will need to sign in again to see your care. Urgent help stays available without signing in.",
  "profile.logout.working": "Signing out…",
  "profile.logoutOthers": "Sign out of other devices",
  "profile.logoutOthers.subtitle": "Ends the session on all other devices",
  "profile.logoutOthers.confirm": "Sign out of other devices?",
  "profile.logoutOthers.body":
    "Anyone using your account on another device will need to sign in again. This device stays signed in.",
  "profile.logoutOthers.done_one": "{count} other device was signed out.",
  "profile.logoutOthers.done_other": "{count} other devices were signed out.",
  "profile.logoutOthers.none": "There were no other devices signed in.",
};
