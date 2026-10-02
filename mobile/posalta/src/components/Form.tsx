import React, { useState } from "react";
import { Pressable, StyleSheet, TextInput, View } from "react-native";
import { useTheme } from "../theme/ThemeProvider";
import { CONTROL_HEIGHT, radius, TOUCH_TARGET } from "../theme/tokens";
import { Icon } from "./Icon";
import { Text } from "./Text";

interface FieldProps {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  help?: string;
  error?: string;
  required?: boolean;
  optionalLabel?: string;
  multiline?: boolean;
  maxLength?: number;
  keyboardType?: "default" | "numeric";
  testID?: string;
}

/** Campo de texto (`.ae-field`): rótulo, controle de 48 px, ajuda e erro. */
export function Field({
  label,
  value,
  onChangeText,
  placeholder,
  help,
  error,
  required,
  optionalLabel,
  multiline,
  maxLength,
  keyboardType = "default",
  testID,
}: FieldProps) {
  const { colors, text } = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.field}>
      <Text variant="label">
        {label}
        {required ? (
          <Text variant="label" tone="danger">
            {" "}
            *
          </Text>
        ) : null}
        {!required && optionalLabel ? (
          <Text variant="label" tone="muted">
            {` (${optionalLabel})`}
          </Text>
        ) : null}
      </Text>
      <TextInput
        testID={testID}
        accessibilityLabel={label}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.inkMuted}
        multiline={multiline}
        maxLength={maxLength}
        keyboardType={keyboardType}
        textAlignVertical={multiline ? "top" : "center"}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={[
          text("body"),
          styles.input,
          multiline && styles.multiline,
          {
            color: colors.ink,
            backgroundColor: colors.surfaceRaised,
            borderColor: error
              ? colors.danger
              : focused
                ? colors.focus
                : colors.lineStrong,
            borderWidth: focused ? 2 : 1,
          },
        ]}
      />
      {help && !error ? (
        <Text variant="bodySm" tone="muted">
          {help}
        </Text>
      ) : null}
      {error ? (
        <Text variant="bodySm" tone="danger" accessibilityRole="alert">
          {error}
        </Text>
      ) : null}
    </View>
  );
}

export interface Option<T extends string> {
  value: T;
  label: string;
  hint?: string;
}

interface ChipGroupProps<T extends string> {
  label?: string;
  options: Option<T>[];
  value: T | null;
  onChange: (value: T) => void;
  testID?: string;
}

/** Escolha única em chips de 44 px (idioma, tema, visibilidade, tipo de pedido). */
export function ChipGroup<T extends string>({
  label,
  options,
  value,
  onChange,
  testID,
}: ChipGroupProps<T>) {
  const { colors } = useTheme();
  return (
    <View style={styles.field} accessibilityRole="radiogroup" testID={testID}>
      {label ? <Text variant="label">{label}</Text> : null}
      <View style={styles.chips}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              testID={testID ? `${testID}-${option.value}` : undefined}
              accessibilityRole="radio"
              accessibilityLabel={option.label}
              accessibilityState={{ selected, checked: selected }}
              onPress={() => onChange(option.value)}
              style={[
                styles.chip,
                {
                  backgroundColor: selected
                    ? colors.primarySoft
                    : colors.surfaceRaised,
                  borderColor: selected ? colors.primary : colors.lineStrong,
                },
              ]}
            >
              {selected ? (
                <Icon name="check" size={16} color={colors.primary} />
              ) : null}
              <Text variant="label" tone={selected ? "primary" : "ink"}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      {value && options.find((option) => option.value === value)?.hint ? (
        <Text variant="bodySm" tone="muted">
          {options.find((option) => option.value === value)?.hint}
        </Text>
      ) : null}
    </View>
  );
}

interface MultiChipGroupProps<T extends string> {
  label?: string;
  options: Option<T>[];
  value: T[];
  onChange: (value: T[]) => void;
  testID?: string;
}

/** Escolha múltipla (emoções). */
export function MultiChipGroup<T extends string>({
  label,
  options,
  value,
  onChange,
  testID,
}: MultiChipGroupProps<T>) {
  const { colors } = useTheme();
  return (
    <View style={styles.field} testID={testID}>
      {label ? <Text variant="label">{label}</Text> : null}
      <View style={styles.chips}>
        {options.map((option) => {
          const selected = value.includes(option.value);
          return (
            <Pressable
              key={option.value}
              testID={testID ? `${testID}-${option.value}` : undefined}
              accessibilityRole="checkbox"
              accessibilityLabel={option.label}
              accessibilityState={{ checked: selected }}
              onPress={() =>
                onChange(
                  selected
                    ? value.filter((item) => item !== option.value)
                    : [...value, option.value],
                )
              }
              style={[
                styles.chip,
                {
                  backgroundColor: selected
                    ? colors.primarySoft
                    : colors.surfaceRaised,
                  borderColor: selected ? colors.primary : colors.lineStrong,
                },
              ]}
            >
              {selected ? (
                <Icon name="check" size={16} color={colors.primary} />
              ) : null}
              <Text variant="label" tone={selected ? "primary" : "ink"}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

interface ScaleInputProps {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  lowLabel?: string;
  highLabel?: string;
  testID?: string;
}

/** Escala numérica acessível (1–5 ou 0–10): cada número é um alvo de toque de 44 px. */
export function ScaleInput({
  label,
  value,
  onChange,
  min = 1,
  max = 5,
  lowLabel,
  highLabel,
  testID,
}: ScaleInputProps) {
  const { colors } = useTheme();
  const numbers = Array.from(
    { length: max - min + 1 },
    (_, index) => min + index,
  );
  return (
    <View
      style={styles.field}
      accessibilityRole="radiogroup"
      accessibilityLabel={label}
      testID={testID}
    >
      <Text variant="label">{label}</Text>
      <View style={styles.scale}>
        {numbers.map((number) => {
          const selected = number === value;
          return (
            <Pressable
              key={number}
              testID={testID ? `${testID}-${number}` : undefined}
              accessibilityRole="radio"
              accessibilityLabel={`${label}: ${number}`}
              accessibilityState={{ selected, checked: selected }}
              onPress={() => onChange(number)}
              style={[
                styles.scalePoint,
                {
                  minWidth: numbers.length > 6 ? 34 : TOUCH_TARGET,
                  backgroundColor: selected
                    ? colors.primary
                    : colors.surfaceRaised,
                  borderColor: selected ? colors.primary : colors.lineStrong,
                },
              ]}
            >
              <Text variant="label" tone={selected ? "onPrimary" : "ink"}>
                {number}
              </Text>
            </Pressable>
          );
        })}
      </View>
      {lowLabel || highLabel ? (
        <View style={styles.scaleLabels}>
          <Text variant="caption" tone="muted" style={styles.scaleCaption}>
            {lowLabel}
          </Text>
          <Text
            variant="caption"
            tone="muted"
            style={[styles.scaleCaption, styles.right]}
          >
            {highLabel}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: 6 },
  input: {
    minHeight: CONTROL_HEIGHT,
    borderRadius: radius.md,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  multiline: { minHeight: 96, paddingTop: 10 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    minHeight: TOUCH_TARGET,
    paddingHorizontal: 14,
    borderRadius: radius.full,
    borderWidth: 1,
  },
  scale: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  scalePoint: {
    flex: 1,
    height: TOUCH_TARGET,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.md,
    borderWidth: 1,
  },
  scaleLabels: { flexDirection: "row", justifyContent: "space-between" },
  scaleCaption: { letterSpacing: 0, flex: 1 },
  right: { textAlign: "right" },
});

interface CheckRowProps {
  label: string;
  checked: boolean;
  onToggle: () => void;
  hint?: string;
  testID?: string;
}

/** Linha com caixa de seleção; o alvo de toque é a linha inteira (≥ 44 px). */
export function CheckRow({
  label,
  checked,
  onToggle,
  hint,
  testID,
}: CheckRowProps) {
  const { colors } = useTheme();
  return (
    <Pressable
      testID={testID}
      accessibilityRole="checkbox"
      accessibilityLabel={label}
      accessibilityHint={hint}
      accessibilityState={{ checked }}
      onPress={onToggle}
      style={checkStyles.row}
    >
      <View
        style={[
          checkStyles.box,
          {
            backgroundColor: checked ? colors.primary : colors.surfaceRaised,
            borderColor: checked ? colors.primary : colors.lineStrong,
          },
        ]}
      >
        {checked ? (
          <Icon
            name="check"
            size={16}
            color={colors.onPrimary}
            strokeWidth={2.5}
          />
        ) : null}
      </View>
      <Text
        variant="body"
        style={[checkStyles.label, checked && { color: colors.inkMuted }]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const checkStyles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    minHeight: TOUCH_TARGET,
  },
  box: {
    width: 24,
    height: 24,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
  },
  label: { flex: 1 },
});
