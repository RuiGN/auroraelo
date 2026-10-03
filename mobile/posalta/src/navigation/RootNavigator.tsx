import React from "react";
import { Platform, View } from "react-native";
import {
  DefaultTheme,
  LinkingOptions,
  NavigationContainer,
  Theme as NavTheme,
} from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import {
  createNativeStackNavigator,
  NativeStackNavigationOptions,
} from "@react-navigation/native-stack";
import { useOptionalSession } from "../api/session";
import { Icon, IconName } from "../components/Icon";
import { BrandMark, Wordmark } from "../components/Layout";
import { useStore } from "../data/store";
import { TranslationKey, useI18n } from "../i18n";
import {
  AgendaScreen,
  AppointmentDetailScreen,
  RequestAppointmentScreen,
} from "../screens/AgendaScreens";
import {
  ActivateScreen,
  ConfigMissingScreen,
  RecoverScreen,
  ResetScreen,
  RestoringScreen,
  SignInScreen,
} from "../screens/AuthScreens";
import {
  CarePlanScreen,
  CareHubScreen,
  ExerciseDetailScreen,
  ExercisesScreen,
  GoalDetailScreen,
  GoalsScreen,
  MedicationsScreen,
  RelapsePlanScreen,
  RoutineScreen,
} from "../screens/CareScreens";
import {
  CheckInScreen,
  CravingScreen,
  DiaryHubScreen,
  JournalEntryDetailScreen,
  JournalEntryNewScreen,
} from "../screens/DiaryScreens";
import { HomeScreen } from "../screens/HomeScreen";
import {
  PrivacyScreen,
  ProfileScreen,
  SettingsScreen,
} from "../screens/ProfileScreens";
import {
  ContentDetailScreen,
  LearnScreen,
  NetworkScreen,
  SupportHubScreen,
} from "../screens/SupportScreens";
import { ConsentGateScreen } from "../screens/ConsentGateScreen";
import {
  LowEnergyEditScreen,
  RecoveryGoalScreen,
  RelapsePlanEditScreen,
  UrgentPlanEditScreen,
} from "../screens/PlanScreens";
import { UrgentHelpScreen } from "../screens/UrgentHelpScreen";
import { useTheme } from "../theme/ThemeProvider";
import { fontFamilyByWeight } from "../theme/tokens";
import { CloseButton, HeaderActions } from "./HeaderActions";
import { RootStackParamList, TabParamList } from "./types";

/**
 * Endereços legíveis para a versão web/PWA (e para conferir telas isoladas).
 * Habilitado só na web: nos apps nativos não há esquema de URL registrado.
 */
const linking: LinkingOptions<RootStackParamList> = {
  enabled: Platform.OS === "web",
  prefixes: [],
  config: {
    screens: {
      // Entrada: sem parâmetros (códigos de convite/recuperação nunca vão no endereço).
      SignIn: "entrar",
      Activate: "ativar",
      Recover: "recuperar",
      Reset: "redefinir",
      Tabs: {
        screens: {
          Home: "",
          Care: "cuidado",
          Diary: "diario",
          Agenda: "agenda",
          Support: "apoio",
        },
      },
      UrgentHelp: "ajuda",
      Profile: "perfil",
      Settings: "configuracoes",
      Privacy: "privacidade",
      CarePlan: "cuidado/plano",
      Medications: "cuidado/medicacoes",
      Routine: "cuidado/rotina",
      Exercises: "cuidado/exercicios",
      ExerciseDetail: "cuidado/exercicios/:id",
      RelapsePlan: "cuidado/prevencao",
      Goals: "cuidado/metas",
      GoalDetail: "cuidado/metas/:id",
      CheckIn: "diario/checkin",
      JournalEntryNew: "diario/novo",
      JournalEntryDetail: "diario/registro/:id",
      Craving: "diario/vontade",
      AppointmentDetail: "agenda/consulta/:id",
      RequestAppointment: "agenda/solicitar",
      Network: "apoio/rede",
      Learn: "apoio/aprender",
      ContentDetail: "apoio/aprender/:id",
    },
  },
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();

const tabIcons: Record<keyof TabParamList, IconName> = {
  Home: "home",
  Care: "heart-pulse",
  Diary: "pen",
  Agenda: "calendar",
  Support: "users",
};

const tabTitles: Record<keyof TabParamList, TranslationKey> = {
  Home: "nav.home",
  Care: "nav.care",
  Diary: "nav.diary",
  Agenda: "nav.agenda",
  Support: "nav.support",
};

function Tabs() {
  const { colors, fontsLoaded } = useTheme();
  const { t } = useI18n();
  const family = fontsLoaded ? fontFamilyByWeight[700] : undefined;
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: colors.navBg },
        headerTintColor: colors.navInk,
        headerShadowVisible: false,
        headerTitleStyle: {
          fontFamily: family,
          fontSize: 18,
          color: colors.navInk,
        },
        headerTitleAlign: "left",
        headerLeft: () => (
          <View style={{ paddingLeft: 16 }}>
            <BrandMark size={30} />
          </View>
        ),
        headerRight: () => (
          <View style={{ paddingRight: 8 }}>
            <HeaderActions />
          </View>
        ),
        headerTitle:
          route.name === "Home"
            ? () => <Wordmark tone="nav" size="sm" />
            : t(tabTitles[route.name]),
        title: t(tabTitles[route.name]),
        tabBarLabel: t(tabTitles[route.name]),
        tabBarAccessibilityLabel: t(tabTitles[route.name]),
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.inkMuted,
        tabBarLabelStyle: {
          fontFamily: fontsLoaded ? fontFamilyByWeight[600] : undefined,
          fontSize: 11,
        },
        tabBarStyle: {
          backgroundColor: colors.surfaceRaised,
          borderTopColor: colors.line,
          // Na web o navegador não informa safe area: reserva altura para ícone + rótulo.
          ...Platform.select({
            web: { height: 64, paddingTop: 6, paddingBottom: 8 },
            default: {},
          }),
        },
        tabBarIcon: ({ color }) => (
          <Icon name={tabIcons[route.name]} size={22} color={color} />
        ),
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Care" component={CareHubScreen} />
      <Tab.Screen name="Diary" component={DiaryHubScreen} />
      <Tab.Screen name="Agenda" component={AgendaScreen} />
      <Tab.Screen name="Support" component={SupportHubScreen} />
    </Tab.Navigator>
  );
}

/**
 * Qual conjunto de telas está disponível:
 * - `app`: preview, ou live com sessão ativa (as abas e as telas de dados);
 * - `auth`: live sem sessão (entrar, ativar, recuperar e redefinir a senha);
 * - `config`: live sem endereço válido do servidor (tela de configuração ausente);
 * - `restoring`: lendo a sessão guardada no cofre do aparelho;
 * - `consent`: sessão ativa, mas há documento obrigatório sem decisão (aceite primeiro).
 * A Ajuda urgente existe em todos eles.
 */
export type NavGate = "app" | "auth" | "config" | "restoring" | "consent";

function useNavGate(): NavGate {
  const { mode, snapshot } = useStore();
  const session = useOptionalSession();
  if (mode === "preview") return "app";
  if (!session || session.status === "disabled") return "config";
  if (session.status === "restoring") return "restoring";
  if (session.status !== "active") return "auth";
  const mustAccept = snapshot?.consents.some(
    (item) => item.mandatory && item.status === "pending",
  );
  return mustAccept ? "consent" : "app";
}

export function RootNavigator() {
  const { colors, scheme, fontsLoaded } = useTheme();
  const { t } = useI18n();
  const gate = useNavGate();

  const navTheme: NavTheme = {
    ...DefaultTheme,
    dark: scheme === "dark",
    colors: {
      primary: colors.primary,
      background: colors.surface,
      card: colors.navBg,
      text: colors.navInk,
      border: colors.navLine,
      notification: colors.danger,
    },
  };

  const header: NativeStackNavigationOptions = {
    headerStyle: { backgroundColor: colors.navBg },
    headerTintColor: colors.navInk,
    headerShadowVisible: false,
    headerBackTitle: t("common.back"),
    headerTitleAlign: "left",
    headerTitleStyle: {
      fontFamily: fontsLoaded ? fontFamilyByWeight[700] : undefined,
      fontSize: 18,
      color: colors.navInk,
    },
    headerRight: () => <HeaderActions />,
    contentStyle: { backgroundColor: colors.surface },
  };

  const screen = (title: TranslationKey): NativeStackNavigationOptions => ({
    title: t(title),
  });

  // Telas de entrada: só a Ajuda no cabeçalho (o perfil não existe sem sessão).
  const authActions = () => <HeaderActions showProfile={false} />;

  return (
    <NavigationContainer theme={navTheme} linking={linking}>
      <Stack.Navigator screenOptions={header}>
        {gate === "app" ? (
          <>
            <Stack.Screen
              name="Tabs"
              component={Tabs}
              // As abas desenham o próprio cabeçalho; evita um segundo conjunto de ações oculto.
              options={{ headerShown: false, headerRight: () => null }}
            />
            <Stack.Screen
              name="Profile"
              component={ProfileScreen}
              options={screen("profile.title")}
            />
            <Stack.Screen
              name="Settings"
              component={SettingsScreen}
              options={screen("settings.title")}
            />
            <Stack.Screen
              name="Privacy"
              component={PrivacyScreen}
              options={screen("privacy.title")}
            />
            <Stack.Screen
              name="CarePlan"
              component={CarePlanScreen}
              options={screen("care.plan")}
            />
            <Stack.Screen
              name="Medications"
              component={MedicationsScreen}
              options={screen("meds.title")}
            />
            <Stack.Screen
              name="Routine"
              component={RoutineScreen}
              options={screen("routine.title")}
            />
            <Stack.Screen
              name="Exercises"
              component={ExercisesScreen}
              options={screen("exercise.title")}
            />
            <Stack.Screen
              name="ExerciseDetail"
              component={ExerciseDetailScreen}
              options={screen("exercise.title")}
            />
            <Stack.Screen
              name="RelapsePlan"
              component={RelapsePlanScreen}
              options={screen("relapse.title")}
            />
            <Stack.Screen
              name="RelapsePlanEdit"
              component={RelapsePlanEditScreen}
              options={screen("relapse.edit.title")}
            />
            <Stack.Screen
              name="UrgentPlanEdit"
              component={UrgentPlanEditScreen}
              options={screen("urgent.edit.title")}
            />
            <Stack.Screen
              name="LowEnergyEdit"
              component={LowEnergyEditScreen}
              options={screen("lowenergy.edit.title")}
            />
            <Stack.Screen
              name="RecoveryGoal"
              component={RecoveryGoalScreen}
              options={screen("recovery.goal.title")}
            />
            <Stack.Screen
              name="Goals"
              component={GoalsScreen}
              options={screen("goals.title")}
            />
            <Stack.Screen
              name="GoalDetail"
              component={GoalDetailScreen}
              options={screen("goals.title")}
            />
            <Stack.Screen
              name="CheckIn"
              component={CheckInScreen}
              options={screen("checkin.title")}
            />
            <Stack.Screen
              name="JournalEntryNew"
              component={JournalEntryNewScreen}
              options={screen("entry.title")}
            />
            <Stack.Screen
              name="JournalEntryDetail"
              component={JournalEntryDetailScreen}
              options={screen("entry.detail")}
            />
            <Stack.Screen
              name="Craving"
              component={CravingScreen}
              options={screen("craving.title")}
            />
            <Stack.Screen
              name="AppointmentDetail"
              component={AppointmentDetailScreen}
              options={screen("agenda.title")}
            />
            <Stack.Screen
              name="RequestAppointment"
              component={RequestAppointmentScreen}
              options={screen("agenda.request.title")}
            />
            <Stack.Screen
              name="Network"
              component={NetworkScreen}
              options={screen("network.title")}
            />
            <Stack.Screen
              name="Learn"
              component={LearnScreen}
              options={screen("learn.title")}
            />
            <Stack.Screen
              name="ContentDetail"
              component={ContentDetailScreen}
              options={screen("learn.title")}
            />
          </>
        ) : gate === "auth" ? (
          <>
            <Stack.Screen
              name="SignIn"
              component={SignInScreen}
              options={{
                ...screen("auth.signin.title"),
                headerRight: authActions,
              }}
            />
            <Stack.Screen
              name="Activate"
              component={ActivateScreen}
              options={{
                ...screen("auth.activate.title"),
                headerRight: authActions,
              }}
            />
            <Stack.Screen
              name="Recover"
              component={RecoverScreen}
              options={{
                ...screen("auth.recover.title"),
                headerRight: authActions,
              }}
            />
            <Stack.Screen
              name="Reset"
              component={ResetScreen}
              options={{
                ...screen("auth.reset.title"),
                headerRight: authActions,
              }}
            />
          </>
        ) : gate === "consent" ? (
          <Stack.Screen
            name="ConsentGate"
            component={ConsentGateScreen}
            options={{
              ...screen("gate.consent.title"),
              headerRight: authActions,
            }}
          />
        ) : gate === "config" ? (
          <Stack.Screen
            name="ConfigMissing"
            component={ConfigMissingScreen}
            options={{
              ...screen("config.missing.title"),
              headerRight: authActions,
            }}
          />
        ) : (
          <Stack.Screen
            name="Restoring"
            component={RestoringScreen}
            options={{
              ...screen("auth.restoring"),
              headerRight: authActions,
            }}
          />
        )}
        <Stack.Screen
          name="UrgentHelp"
          component={UrgentHelpScreen}
          options={{
            ...screen("help.title"),
            presentation: "modal",
            headerLeft: () => <CloseButton />,
            headerRight: () => (
              <HeaderActions showHelp={false} showProfile={false} />
            ),
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
