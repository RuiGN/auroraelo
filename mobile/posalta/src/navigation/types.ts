import { NavigatorScreenParams } from "@react-navigation/native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

export type TabParamList = {
  Home: undefined;
  Care: undefined;
  Diary: undefined;
  Agenda: undefined;
  Support: undefined;
};

export type RootStackParamList = {
  // Entrada (modo live sem sessão ativa). Nenhuma leva parâmetros: senhas e códigos
  // de convite nunca viram parâmetro de rota (na web virariam endereço e histórico).
  SignIn: undefined;
  Activate: undefined;
  Recover: undefined;
  Reset: undefined;
  ConfigMissing: undefined;
  /** Aceite obrigatório dos documentos vigentes (live, antes dos dados). */
  ConsentGate: undefined;
  Restoring: undefined;
  // App com dados (preview ou sessão ativa)
  Tabs: NavigatorScreenParams<TabParamList> | undefined;
  /** Disponível também sem sessão: os números de emergência não dependem de login. */
  UrgentHelp: undefined;
  Profile: undefined;
  Settings: undefined;
  Privacy: undefined;
  // Cuidado
  CarePlan: undefined;
  Medications: undefined;
  Routine: undefined;
  Exercises: undefined;
  ExerciseDetail: { id: string };
  RelapsePlan: undefined;
  RelapsePlanEdit: undefined;
  UrgentPlanEdit: undefined;
  LowEnergyEdit: undefined;
  Goals: undefined;
  GoalDetail: { id: string };
  // Diário
  CheckIn: undefined;
  JournalEntryNew: undefined;
  JournalEntryDetail: { id: string };
  Craving: undefined;
  RecoveryGoal: undefined;
  // Agenda
  AppointmentDetail: { id: string };
  RequestAppointment: undefined;
  // Apoio
  Network: undefined;
  Learn: undefined;
  ContentDetail: { id: string };
};

export type RootScreenProps<Name extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, Name>;
