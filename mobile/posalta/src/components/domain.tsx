import React from "react";
import { Visibility } from "../domain/types";
import { useI18n } from "../i18n";
import { ChipGroup } from "./Form";

const VISIBILITIES: Visibility[] = [
  "private",
  "shareable",
  "confirmation_required",
];

interface VisibilityPickerProps {
  value: Visibility;
  onChange: (value: Visibility) => void;
  label: string;
  testID?: string;
}

/** Quem pode ver um registro: só eu (padrão), compartilhável ou “perguntar antes”. */
export function VisibilityPicker({
  value,
  onChange,
  label,
  testID,
}: VisibilityPickerProps) {
  const { t } = useI18n();
  return (
    <ChipGroup
      testID={testID}
      label={label}
      value={value}
      onChange={onChange}
      options={VISIBILITIES.map((item) => ({
        value: item,
        label: t(`visibility.${item}`),
        hint: t(`visibility.${item}.hint`),
      }))}
    />
  );
}
