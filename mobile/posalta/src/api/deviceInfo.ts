/**
 * Identificação do aparelho enviada ao entrar (`device_label`, `platform`,
 * `app_version`): aparece na lista "Aparelhos" para a pessoa reconhecer cada sessão.
 * Só plataforma e, no Android, o modelo que o próprio sistema informa: sem permissão
 * nem dependência nova, e sem identificador único do aparelho.
 */
import { Platform } from "react-native";
import Constants from "expo-constants";

export interface DeviceInfo {
  deviceLabel: string;
  platform: "ios" | "android" | "other";
  appVersion: string;
}

function clean(value: unknown, max: number): string {
  if (typeof value !== "string") return "";
  return value.replace(/\s+/g, " ").trim().slice(0, max);
}

export function describeDevice(): DeviceInfo {
  const appVersion = clean(Constants.expoConfig?.version, 100);
  if (Platform.OS === "ios") {
    const pad = (Platform as { isPad?: boolean }).isPad === true;
    return {
      deviceLabel: pad ? "iPad" : "iPhone",
      platform: "ios",
      appVersion,
    };
  }
  if (Platform.OS === "android") {
    const constants = Platform.constants as { Model?: unknown };
    const model = clean(constants?.Model, 60);
    return {
      deviceLabel: model ? `Android ${model}` : "Android",
      platform: "android",
      appVersion,
    };
  }
  return { deviceLabel: "Web", platform: "other", appVersion };
}
