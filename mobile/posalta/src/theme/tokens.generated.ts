// GERADO por scripts/sync-tokens.mjs a partir de
// auroraelo_design_system/static/css/aurora-elo.css — não edite à mão.
/* eslint-disable */

export const lightColors = {
  brandNavy: "#0d3665",
  brandBlue: "#2072ab",
  brandSky: "#58abdf",
  brandAqua: "#6fc5dd",
  brandIce: "#d1e7f7",
  surface: "#f3f7fb",
  surfaceRaised: "#ffffff",
  surfaceSunken: "#e8f0f7",
  line: "#d6e2ec",
  lineStrong: "#6f879f",
  ink: "#0c2440",
  inkMuted: "#4b6178",
  navBg: "#0a2342",
  navBgHover: "#12345c",
  navLine: "#1c3b62",
  navInk: "#ffffff",
  navInkMuted: "#b9cde1",
  navAccent: "#58abdf",
  primary: "#2072ab",
  primaryHover: "#185a8a",
  onPrimary: "#ffffff",
  primarySoft: "#e9f3fb",
  focus: "#2072ab",
  success: "#1d6b45",
  successSoft: "#e0f2e8",
  warning: "#8a5300",
  warningSoft: "#fdf0d8",
  danger: "#b3261e",
  dangerSoft: "#fbe4e2",
  onDanger: "#ffffff",
} as const;

export const darkColors = {
  brandNavy: "#0d3665",
  brandBlue: "#2072ab",
  brandSky: "#58abdf",
  brandAqua: "#6fc5dd",
  brandIce: "#d1e7f7",
  surface: "#0b1726",
  surfaceRaised: "#122236",
  surfaceSunken: "#0e1c2e",
  line: "#25405c",
  lineStrong: "#5d7a97",
  ink: "#e7f0f8",
  inkMuted: "#9fb3c8",
  navBg: "#071a33",
  navBgHover: "#10294a",
  navLine: "#173356",
  navInk: "#ffffff",
  navInkMuted: "#b9cde1",
  navAccent: "#58abdf",
  primary: "#58abdf",
  primaryHover: "#7fc3ea",
  onPrimary: "#06182c",
  primarySoft: "#133552",
  focus: "#58abdf",
  success: "#5fcf95",
  successSoft: "#12301f",
  warning: "#f0b35a",
  warningSoft: "#35260e",
  danger: "#ff8a80",
  dangerSoft: "#3b1614",
  onDanger: "#2a0906",
} as const;

export type ColorTokens = { [Key in keyof typeof lightColors]: string };

export const space = {
  "1": 4,
  "2": 8,
  "3": 12,
  "4": 16,
  "6": 24,
  "8": 32,
  "12": 48,
} as const;

export const radius = { sm: 6, md: 10, lg: 16, full: 9999 } as const;

export const designTypography = {
  wordmark: {
    fontSize: 22,
    lineHeight: 24,
    fontWeight: 800,
    letterSpacingEm: -0.02,
  },
  display: {
    fontSize: 32,
    lineHeight: 40,
    fontWeight: 800,
    letterSpacingEm: -0.02,
  },
  title1: {
    fontSize: 24,
    lineHeight: 32,
    fontWeight: 800,
    letterSpacingEm: -0.01,
  },
  title2: {
    fontSize: 18,
    lineHeight: 26,
    fontWeight: 700,
    letterSpacingEm: 0,
  },
  title3: {
    fontSize: 15,
    lineHeight: 22,
    fontWeight: 700,
    letterSpacingEm: 0,
  },
  body: {
    fontSize: 15,
    lineHeight: 24,
    fontWeight: 500,
    letterSpacingEm: 0,
  },
  bodySm: {
    fontSize: 13,
    lineHeight: 20,
    fontWeight: 500,
    letterSpacingEm: 0,
  },
  menu: {
    fontSize: 15,
    lineHeight: 24,
    fontWeight: 600,
    letterSpacingEm: 0,
  },
  label: {
    fontSize: 13,
    lineHeight: 16,
    fontWeight: 700,
    letterSpacingEm: 0,
  },
  caption: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: 700,
    letterSpacingEm: 0.04,
  },
} as const;

export const designShadows = {
  shadowSm: "0 1px 2px #0c24400f, 0 1px 3px #0c24401a",
  shadowMd: "0 2px 6px #0c24401a, 0 12px 28px -4px #0c244033",
} as const;

export const designSystemSource =
  "auroraelo_design_system/static/css/aurora-elo.css";
