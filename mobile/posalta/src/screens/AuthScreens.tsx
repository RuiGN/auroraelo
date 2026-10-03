import React, {
  ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { ActivityIndicator, StyleSheet, TextInput, View } from "react-native";
import { useIsFocused } from "@react-navigation/native";
import { DeepLinkKind, useDeepLinkCode, useDeepLinks } from "../api/deepLinks";
import { ClinicRef } from "../api/errors";
import { AuthFailureReason, AuthResult, useSession } from "../api/session";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Alert } from "../components/Feedback";
import { ChipGroup, Field } from "../components/Form";
import { BrandMark, Screen, Wordmark } from "../components/Layout";
import { Text } from "../components/Text";
import { IS_DEV } from "../config";
import { TranslationKey, useI18n } from "../i18n";
import { authFailureKey } from "../i18n/errorCodes";
import { useNav } from "../navigation/useNav";
import { useTheme } from "../theme/ThemeProvider";

/*
 * Telas de entrada do modo live (sem sessão ativa): entrar, ativar conta, recuperar
 * e redefinir senha, mais o aviso de configuração ausente e a abertura da sessão.
 * Todas têm um acesso visível à Ajuda urgente (botão no cabeçalho e no corpo): os
 * números de emergência funcionam sem login e sem rede.
 *
 * Senhas e códigos ficam só no estado local da tela: não vão para parâmetros de
 * navegação (na web viram endereço), log nem armazenamento.
 */

type Failure = Extract<AuthResult, { ok: false }>;

const WARNING_REASONS: AuthFailureReason[] = [
  "offline",
  "rate_limited",
  "blocked",
  "unexpected",
];

function useMounted() {
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  return mounted;
}

/**
 * Leva à tela de ativar ou de redefinir quando chega um link do app (e-mail). Só a tela
 * em foco reage, e a tela de destino não se redireciona a si mesma (ela mesma recebe
 * o código por `useDeepLinkCode`). O código não passa por parâmetro de navegação.
 */
function useDeepLinkNavigation(current?: DeepLinkKind) {
  const nav = useNav();
  const focused = useIsFocused();
  const { pending } = useDeepLinks();
  const kind = pending?.kind;
  useEffect(() => {
    if (!focused || !kind || kind === current) return;
    nav.navigate(kind === "activate" ? "Activate" : "Reset");
  }, [focused, kind, current, nav]);
}

interface AuthShellProps {
  testID: string;
  title: string;
  intro?: string;
  children?: ReactNode;
}

/** Moldura das telas de entrada: marca, título e acesso à Ajuda urgente. */
function AuthShell({ testID, title, intro, children }: AuthShellProps) {
  const { t } = useI18n();
  const nav = useNav();
  return (
    <Screen testID={testID}>
      <View style={styles.brand}>
        <BrandMark size={56} />
        <Wordmark tone="surface" size="lg" />
        <Text variant="bodySm" tone="muted">
          {t("brand.tagline")}
        </Text>
      </View>
      <Text variant="title1" header>
        {title}
      </Text>
      {intro ? (
        <Text variant="body" tone="muted">
          {intro}
        </Text>
      ) : null}
      {children}
      <Card tone="danger">
        <Button
          testID="auth-help"
          label={t("help.title")}
          icon="lifebuoy"
          variant="danger"
          onPress={() => nav.navigate("UrgentHelp")}
          fullWidth
        />
        <Text variant="bodySm" tone="muted">
          {t("auth.help.note")}
        </Text>
      </Card>
    </Screen>
  );
}

interface FailureAlertProps {
  failure: Failure | null;
  /** Troca o texto de um motivo (ex.: senha atual errada na ativação). */
  override?: Partial<Record<AuthFailureReason, TranslationKey>>;
}

function FailureAlert({ failure, override }: FailureAlertProps) {
  const { t } = useI18n();
  if (!failure) return null;
  const key = override?.[failure.reason] ?? authFailureKey(failure.reason);
  return (
    <Alert
      tone={WARNING_REASONS.includes(failure.reason) ? "warning" : "danger"}
      testID="auth-error"
      live
    >
      <Text variant="bodySm">{t(key)}</Text>
      {failure.errors?.map((line) => (
        <Text key={line} variant="bodySm">
          • {line}
        </Text>
      ))}
    </Alert>
  );
}

// ── Entrar ──────────────────────────────────────────────────────────────────

export function SignInScreen() {
  const { t } = useI18n();
  const nav = useNav();
  const session = useSession();
  const mounted = useMounted();
  useDeepLinkNavigation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [clinics, setClinics] = useState<ClinicRef[] | null>(null);
  const [clinicId, setClinicId] = useState<string | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [busy, setBusy] = useState(false);
  const passwordRef = useRef<TextInput>(null);

  const canSubmit =
    email.trim().length > 0 &&
    password.length > 0 &&
    (clinics === null || clinicId !== null) &&
    !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setFailure(null);
    session.clearNotice();
    const result = await session.login({
      email,
      password,
      clinicId: clinicId ?? undefined,
    });
    if (!mounted.current) return;
    setBusy(false);
    if (result.ok) return; // a navegação troca para as abas
    if (result.reason === "clinic_choice") {
      setClinics(result.clinics ?? []);
      setClinicId(null);
      return;
    }
    setFailure(result);
  };

  return (
    <AuthShell
      testID="screen-signin"
      title={t("auth.signin.title")}
      intro={t("auth.signin.intro")}
    >
      {session.notice ? (
        <Alert
          tone={session.notice === "password_reset" ? "success" : "info"}
          testID="auth-notice"
          live
        >
          <Text variant="bodySm">
            {t(
              session.notice === "password_reset"
                ? "auth.notice.reset"
                : "auth.notice.expired",
            )}
          </Text>
        </Alert>
      ) : null}
      <Field
        testID="auth-email"
        label={t("auth.email")}
        value={email}
        onChangeText={(value) => {
          setEmail(value);
          setClinics(null); // outra pessoa: a lista de clínicas deixa de valer
          setClinicId(null);
        }}
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="username"
        textContentType="username"
        returnKeyType="next"
        onSubmitEditing={() => passwordRef.current?.focus()}
        editable={!busy}
        required
      />
      <Field
        testID="auth-password"
        label={t("auth.password")}
        value={password}
        onChangeText={(value) => {
          setPassword(value);
          setClinics(null);
          setClinicId(null);
        }}
        password={{
          showLabel: t("auth.password.show"),
          hideLabel: t("auth.password.hide"),
        }}
        autoComplete="current-password"
        textContentType="password"
        returnKeyType="go"
        onSubmitEditing={() => void submit()}
        inputRef={passwordRef}
        editable={!busy}
        required
      />
      {clinics ? (
        <Card testID="auth-clinic-choice" tone="primary">
          <Text variant="title3" header>
            {t("auth.clinic.title")}
          </Text>
          <Text variant="bodySm">{t("auth.clinic.hint")}</Text>
          <ChipGroup
            testID="auth-clinic"
            label={t("auth.clinic.label")}
            value={clinicId}
            onChange={setClinicId}
            options={clinics.map((clinic) => ({
              value: clinic.id,
              label: clinic.name,
            }))}
          />
        </Card>
      ) : null}
      <FailureAlert failure={failure} />
      <Button
        testID="auth-submit"
        label={t("auth.signin.submit")}
        disabled={!canSubmit}
        loading={busy}
        onPress={() => void submit()}
        fullWidth
      />
      <Button
        testID="auth-forgot"
        label={t("auth.forgot")}
        variant="ghost"
        onPress={() => nav.navigate("Recover")}
        fullWidth
      />
      <Button
        testID="auth-have-code"
        label={t("auth.haveCode")}
        variant="ghost"
        onPress={() => nav.navigate("Activate")}
        fullWidth
      />
    </AuthShell>
  );
}

// ── Ativar conta ────────────────────────────────────────────────────────────

export function ActivateScreen() {
  const { t } = useI18n();
  const session = useSession();
  const mounted = useMounted();
  useDeepLinkNavigation("activate");

  const [code, setCode] = useState("");
  const [fromLink, setFromLink] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [failure, setFailure] = useState<Failure | null>(null);
  const [busy, setBusy] = useState(false);
  const firstNameRef = useRef<TextInput>(null);
  const lastNameRef = useRef<TextInput>(null);
  const passwordRef = useRef<TextInput>(null);

  // O link do e-mail só preenche o campo: ele continua editável.
  useDeepLinkCode(
    "activate",
    useCallback((value: string) => {
      setCode(value);
      setFromLink(true);
    }, []),
  );

  const canSubmit = code.trim().length > 0 && password.length > 0 && !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setFailure(null);
    const result = await session.activate({
      code,
      password,
      firstName,
      lastName,
    });
    if (!mounted.current) return;
    setBusy(false);
    if (!result.ok) setFailure(result);
  };

  return (
    <AuthShell
      testID="screen-activate"
      title={t("auth.activate.title")}
      intro={t("auth.activate.intro")}
    >
      <Field
        testID="auth-code"
        label={t("auth.activate.code")}
        value={code}
        onChangeText={(value) => {
          setCode(value);
          setFromLink(false);
        }}
        help={fromLink ? t("auth.codeFilled") : undefined}
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="one-time-code"
        textContentType="oneTimeCode"
        returnKeyType="next"
        onSubmitEditing={() => firstNameRef.current?.focus()}
        editable={!busy}
        required
      />
      <Field
        testID="auth-first-name"
        label={t("auth.activate.firstName")}
        value={firstName}
        onChangeText={setFirstName}
        autoCapitalize="words"
        autoComplete="given-name"
        textContentType="givenName"
        returnKeyType="next"
        onSubmitEditing={() => lastNameRef.current?.focus()}
        inputRef={firstNameRef}
        editable={!busy}
      />
      <Field
        testID="auth-last-name"
        label={t("auth.activate.lastName")}
        value={lastName}
        onChangeText={setLastName}
        autoCapitalize="words"
        autoComplete="family-name"
        textContentType="familyName"
        returnKeyType="next"
        onSubmitEditing={() => passwordRef.current?.focus()}
        inputRef={lastNameRef}
        editable={!busy}
      />
      <Field
        testID="auth-password"
        label={t("auth.activate.password")}
        value={password}
        onChangeText={setPassword}
        help={t("auth.activate.existing")}
        password={{
          showLabel: t("auth.password.show"),
          hideLabel: t("auth.password.hide"),
        }}
        autoComplete="new-password"
        textContentType="newPassword"
        returnKeyType="go"
        onSubmitEditing={() => void submit()}
        inputRef={passwordRef}
        editable={!busy}
        required
      />
      <FailureAlert
        failure={failure}
        override={{ invalid_credentials: "error.code.reauthentication_failed" }}
      />
      <Button
        testID="auth-submit"
        label={t("auth.activate.submit")}
        disabled={!canSubmit}
        loading={busy}
        onPress={() => void submit()}
        fullWidth
      />
    </AuthShell>
  );
}

// ── Recuperar senha ─────────────────────────────────────────────────────────

export function RecoverScreen() {
  const { t } = useI18n();
  const nav = useNav();
  const session = useSession();
  const mounted = useMounted();
  useDeepLinkNavigation();

  const [email, setEmail] = useState("");
  const [failure, setFailure] = useState<Failure | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const canSubmit = email.trim().length > 0 && !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setFailure(null);
    setSent(false);
    const result = await session.requestRecovery(email);
    if (!mounted.current) return;
    setBusy(false);
    // Resposta neutra: o servidor responde igual exista ou não o e-mail.
    if (result.ok) setSent(true);
    else setFailure(result);
  };

  return (
    <AuthShell
      testID="screen-recover"
      title={t("auth.recover.title")}
      intro={t("auth.recover.intro")}
    >
      <Field
        testID="auth-email"
        label={t("auth.email")}
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="username"
        textContentType="username"
        returnKeyType="go"
        onSubmitEditing={() => void submit()}
        editable={!busy}
        required
      />
      {sent ? (
        <Alert tone="success" testID="auth-recover-sent" live>
          <Text variant="bodySm">{t("auth.recover.sent")}</Text>
        </Alert>
      ) : null}
      <FailureAlert failure={failure} />
      <Button
        testID="auth-submit"
        label={t("auth.recover.submit")}
        disabled={!canSubmit}
        loading={busy}
        onPress={() => void submit()}
        fullWidth
      />
      <Button
        testID="auth-have-reset-code"
        label={t("auth.recover.haveCode")}
        variant="ghost"
        onPress={() => nav.navigate("Reset")}
        fullWidth
      />
      <Button
        testID="auth-back"
        label={t("auth.backToSignin")}
        variant="ghost"
        onPress={() => nav.navigate("SignIn", undefined, { pop: true })}
        fullWidth
      />
    </AuthShell>
  );
}

// ── Redefinir senha ─────────────────────────────────────────────────────────

export function ResetScreen() {
  const { t } = useI18n();
  const nav = useNav();
  const session = useSession();
  const mounted = useMounted();
  useDeepLinkNavigation("reset");

  const [code, setCode] = useState("");
  const [fromLink, setFromLink] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [failure, setFailure] = useState<Failure | null>(null);
  const [busy, setBusy] = useState(false);
  const passwordRef = useRef<TextInput>(null);

  useDeepLinkCode(
    "reset",
    useCallback((value: string) => {
      setCode(value);
      setFromLink(true);
    }, []),
  );

  const canSubmit = code.trim().length > 0 && newPassword.length > 0 && !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setFailure(null);
    const result = await session.resetPassword({ code, newPassword });
    if (!mounted.current) return;
    setBusy(false);
    if (result.ok) {
      setNewPassword("");
      setCode("");
      nav.navigate("SignIn", undefined, { pop: true }); // a tela de entrada avisa que a senha foi trocada
    } else {
      setFailure(result);
    }
  };

  return (
    <AuthShell
      testID="screen-reset"
      title={t("auth.reset.title")}
      intro={t("auth.reset.intro")}
    >
      <Field
        testID="auth-code"
        label={t("auth.reset.code")}
        value={code}
        onChangeText={(value) => {
          setCode(value);
          setFromLink(false);
        }}
        help={fromLink ? t("auth.codeFilled") : undefined}
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="one-time-code"
        textContentType="oneTimeCode"
        returnKeyType="next"
        onSubmitEditing={() => passwordRef.current?.focus()}
        editable={!busy}
        required
      />
      <Field
        testID="auth-new-password"
        label={t("auth.reset.newPassword")}
        value={newPassword}
        onChangeText={setNewPassword}
        help={t("auth.reset.note")}
        password={{
          showLabel: t("auth.password.show"),
          hideLabel: t("auth.password.hide"),
        }}
        autoComplete="new-password"
        textContentType="newPassword"
        returnKeyType="go"
        onSubmitEditing={() => void submit()}
        inputRef={passwordRef}
        editable={!busy}
        required
      />
      <FailureAlert failure={failure} />
      <Button
        testID="auth-submit"
        label={t("auth.reset.submit")}
        disabled={!canSubmit}
        loading={busy}
        onPress={() => void submit()}
        fullWidth
      />
      <Button
        testID="auth-back"
        label={t("auth.backToSignin")}
        variant="ghost"
        onPress={() => nav.navigate("SignIn", undefined, { pop: true })}
        fullWidth
      />
    </AuthShell>
  );
}

// ── Sem configuração e abertura da sessão ───────────────────────────────────

/** Live sem endereço válido do servidor: explica sem quebrar e mantém a Ajuda. */
export function ConfigMissingScreen() {
  const { t } = useI18n();
  return (
    <AuthShell testID="screen-config-missing" title={t("config.missing.title")}>
      <Alert tone="warning" testID="config-missing">
        <Text variant="bodySm">{t("config.missing.body")}</Text>
        <Text variant="bodySm" tone="muted">
          {t("config.missing.help")}
        </Text>
        {IS_DEV ? (
          <Text variant="bodySm" tone="muted" testID="config-missing-dev">
            {t("config.missing.dev")}
          </Text>
        ) : null}
      </Alert>
    </AuthShell>
  );
}

/** Enquanto o app lê a sessão guardada no cofre do aparelho (instantes). */
export function RestoringScreen() {
  const { t } = useI18n();
  const { colors } = useTheme();
  return (
    <AuthShell testID="screen-restoring" title={t("auth.restoring")}>
      <View style={styles.center} accessibilityLiveRegion="polite">
        <ActivityIndicator color={colors.primary} />
      </View>
    </AuthShell>
  );
}

const styles = StyleSheet.create({
  brand: { alignItems: "center", gap: 6, paddingVertical: 8 },
  center: { alignItems: "center", paddingVertical: 16 },
});
