import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  Animated,
  Easing,
  StyleSheet,
  View,
} from "react-native";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import { Button } from "./Button";
import { Text } from "./Text";

const INHALE_MS = 4000;
const EXHALE_MS = 6000;

type Phase = "inhale" | "exhale";

/**
 * Respiração guiada 4–6 (inspirar 4 s, soltar 6 s), 100% local e sem conexão.
 * Não mede nem registra nada; o usuário pode parar a qualquer momento. Com
 * “reduzir movimento” ativo, mantém apenas a instrução em texto.
 */
export function BreathingExercise() {
  const { colors } = useTheme();
  const { t } = useI18n();
  const [running, setRunning] = useState(false);
  const [phase, setPhase] = useState<Phase>("inhale");
  const [reduceMotion, setReduceMotion] = useState(false);
  const scale = useRef(new Animated.Value(0.6)).current;
  const active = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let mounted = true;
    AccessibilityInfo.isReduceMotionEnabled()
      .then((value) => {
        if (mounted) setReduceMotion(value);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, []);

  const stop = useCallback(() => {
    active.current = false;
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    scale.stopAnimation();
    scale.setValue(0.6);
    setRunning(false);
    setPhase("inhale");
  }, [scale]);

  const cycle = useCallback(
    (next: Phase) => {
      if (!active.current) return;
      setPhase(next);
      const duration = next === "inhale" ? INHALE_MS : EXHALE_MS;
      if (!reduceMotion) {
        Animated.timing(scale, {
          toValue: next === "inhale" ? 1 : 0.6,
          duration,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: false,
        }).start();
      }
      timer.current = setTimeout(
        () => cycle(next === "inhale" ? "exhale" : "inhale"),
        duration,
      );
    },
    [reduceMotion, scale],
  );

  const start = useCallback(() => {
    active.current = true;
    setRunning(true);
    cycle("inhale");
  }, [cycle]);

  useEffect(() => stop, [stop]);

  return (
    <View style={styles.wrap} testID="breathing">
      <View style={styles.stage}>
        <Animated.View
          style={[
            styles.circle,
            {
              backgroundColor: colors.primarySoft,
              borderColor: colors.primary,
              transform: [{ scale }],
            },
          ]}
        />
        <View style={styles.stageText} pointerEvents="none">
          <Text
            variant="title3"
            tone="primary"
            accessibilityLiveRegion="polite"
            style={styles.center}
            testID="breathing-phase"
          >
            {running
              ? t(
                  phase === "inhale"
                    ? "help.breathing.inhale"
                    : "help.breathing.exhale",
                )
              : ""}
          </Text>
        </View>
      </View>
      <Button
        label={running ? t("help.breathing.stop") : t("help.breathing.start")}
        variant={running ? "secondary" : "primary"}
        onPress={running ? stop : start}
        testID="breathing-toggle"
      />
      <Text variant="bodySm" tone="muted" style={styles.center}>
        {t("help.breathing.note")}
      </Text>
    </View>
  );
}

const SIZE = 160;

const styles = StyleSheet.create({
  wrap: { alignItems: "stretch", gap: 12 },
  stage: { height: SIZE + 20, alignItems: "center", justifyContent: "center" },
  circle: {
    width: SIZE,
    height: SIZE,
    borderRadius: radius.full,
    borderWidth: 2,
  },
  stageText: {
    position: "absolute",
    alignItems: "center",
    justifyContent: "center",
    width: SIZE,
  },
  center: { textAlign: "center" },
});
