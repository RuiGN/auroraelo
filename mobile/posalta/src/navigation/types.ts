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
  Tabs: NavigatorScreenParams<TabParamList> | undefined;
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
  Goals: undefined;
  GoalDetail: { id: string };
  // Diário
  CheckIn: undefined;
  JournalEntryNew: undefined;
  JournalEntryDetail: { id: string };
  Craving: undefined;
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
