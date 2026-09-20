export const pt = {
  brand: "Aurora Elo",
  b2c: "Recuperação e apoio no seu tempo",
  connected: "Recuperação e vínculo com o cuidado",
  local: "Modo local • serviços online indisponíveis",
  intro:
    "Apoio à recuperação, sem julgamentos. Este app não faz diagnósticos e não substitui atendimento profissional.",
  areas: "Caminhos de recuperação",
  substances: "Álcool e outras substâncias",
  gambling: "Apostas e jogos de azar",
  gaming: "Jogos digitais",
  areasNote:
    "Informações gerais, não uma avaliação clínica. Nenhuma escolha ou dado de saúde é enviado.",
  aiTitle: "Apoio digital com IA",
  avatar: "Avatar de inteligência artificial, não é uma pessoa",
  aiBadge: "IA",
  aiOff:
    "IA desativada — indisponível também offline. Aguarda API própria e revisão clínica. Não há conversa ou monitoramento por IA.",
  consent: "Consentimento para IA: não concedido",
  consentNote:
    "Não coletamos consentimento enquanto o serviço estiver desativado. Uma futura ativação exigirá sua escolha explícita, termos versionados e possibilidade de revogação.",
  aiStart: "Conversa indisponível",
  records: "Seu cuidado",
  recordsOff:
    "Prontuário, teleconsulta e registro de medicação indisponíveis. Nenhuma dose foi marcada ou sincronizada.",
  help: "Ajuda em situação urgente",
  nobody:
    "Ninguém foi notificado. O app não envia SOS nem sua localização e não oferece plantão.",
  helpDetail:
    "Em risco imediato, procure o serviço de emergência da sua região ou uma pessoa de confiança. Não espere uma resposta deste app.",
  language: "Idioma da interface",
  privacy:
    "Só o idioma da interface é salvo neste aparelho. Relatos pessoais e prontuários não são traduzidos automaticamente.",
  loading: "Carregando idioma…",
  storageError:
    "Não foi possível salvar ou recuperar o idioma neste aparelho. A escolha vale apenas nesta sessão.",
} as const;

export type Locale = "pt-br" | "en" | "es";
type Messages = { [Key in keyof typeof pt]: string };
export const catalogs: Record<Locale, Messages> = {
  "pt-br": pt,
  en: {
    brand: "Aurora Elo",
    b2c: "Recovery at your own pace",
    connected: "Recovery and connection to care",
    local: "Local mode • online services unavailable",
    intro:
      "Recovery support without judgment. This app does not diagnose conditions or replace professional care.",
    areas: "Paths to recovery",
    substances: "Alcohol and other substances",
    gambling: "Betting and gambling",
    gaming: "Digital gaming",
    areasNote:
      "General information, not a clinical assessment. No choices or health data are sent.",
    aiTitle: "Digital support with AI",
    avatar: "Artificial intelligence avatar, not a person",
    aiBadge: "AI",
    aiOff:
      "AI disabled — also unavailable offline. Awaiting our own API and clinical review. No AI conversation or monitoring is running.",
    consent: "AI consent: not given",
    consentNote:
      "We do not collect consent while the service is disabled. Future activation will require your explicit choice, versioned terms and the option to revoke consent.",
    aiStart: "Conversation unavailable",
    records: "Your care",
    recordsOff:
      "Health records, teleconsultations and medication logging are unavailable. No dose has been marked or synced.",
    help: "Help in an urgent situation",
    nobody:
      "No one has been notified. This app does not send SOS alerts or your location and has no on-call service.",
    helpDetail:
      "In immediate danger, contact your local emergency service or someone you trust. Do not wait for a response from this app.",
    language: "Interface language",
    privacy:
      "Only the interface language is saved on this device. Personal accounts and health records are not automatically translated.",
    loading: "Loading language…",
    storageError:
      "Could not save or restore the language on this device. Your choice applies only to this session.",
  },
  es: {
    brand: "Aurora Elo",
    b2c: "Recuperación a tu ritmo",
    connected: "Recuperación y vínculo con el cuidado",
    local: "Modo local • servicios en línea no disponibles",
    intro:
      "Apoyo a la recuperación, sin juicios. Esta app no hace diagnósticos ni sustituye la atención profesional.",
    areas: "Caminos de recuperación",
    substances: "Alcohol y otras sustancias",
    gambling: "Apuestas y juegos de azar",
    gaming: "Videojuegos",
    areasNote:
      "Información general, no una evaluación clínica. No se envían elecciones ni datos de salud.",
    aiTitle: "Apoyo digital con IA",
    avatar: "Avatar de inteligencia artificial, no es una persona",
    aiBadge: "IA",
    aiOff:
      "IA desactivada — tampoco está disponible sin conexión. Pendiente de API propia y revisión clínica. No hay conversación ni monitoreo por IA.",
    consent: "Consentimiento para IA: no otorgado",
    consentNote:
      "No recogemos consentimiento mientras el servicio esté desactivado. Una futura activación requerirá tu elección explícita, términos versionados y la posibilidad de revocación.",
    aiStart: "Conversación no disponible",
    records: "Tu cuidado",
    recordsOff:
      "Historia clínica, teleconsulta y registro de medicación no disponibles. No se ha marcado ni sincronizado ninguna dosis.",
    help: "Ayuda en una situación urgente",
    nobody:
      "Nadie ha sido notificado. La app no envía alertas SOS ni tu ubicación y no ofrece servicio de guardia.",
    helpDetail:
      "En peligro inmediato, contacta con el servicio de emergencia de tu región o con alguien de confianza. No esperes una respuesta de esta app.",
    language: "Idioma de la interfaz",
    privacy:
      "Solo se guarda el idioma de la interfaz en este dispositivo. Los relatos personales y las historias clínicas no se traducen automáticamente.",
    loading: "Cargando idioma…",
    storageError:
      "No se pudo guardar o recuperar el idioma en este dispositivo. Tu elección solo se aplica a esta sesión.",
  },
};
export const localeLabels: Record<Locale, string> = {
  "pt-br": "Português (Brasil)",
  en: "English",
  es: "Español",
};
export const LANGUAGE_KEY = "aurora-elo.ui-language";
export function isLocale(value: unknown): value is Locale {
  return value === "pt-br" || value === "en" || value === "es";
}
