// Gera src/theme/tokens.generated.ts a partir do CSS do design system Aurora Elo.
// Uso: npm run tokens [-- /caminho/para/aurora-elo.css]
// Não edite tokens.generated.ts à mão: altere o design system e gere de novo.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const cssPath = resolve(
  process.argv[2] ??
    process.env.AURORA_DESIGN_SYSTEM_CSS ??
    resolve(here, "../../../../auroraelo_design_system/static/css/aurora-elo.css"),
);
const css = readFileSync(cssPath, "utf8");

function block(selectorPattern) {
  const match = css.match(new RegExp(`${selectorPattern}\\s*\\{([^}]*)\\}`));
  if (!match) throw new Error(`Bloco não encontrado no CSS: ${selectorPattern}`);
  return match[1];
}

function declarations(body) {
  const out = {};
  for (const m of body.matchAll(/--([a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    out[m[1]] = m[2].trim();
  }
  return out;
}

function resolveVars(map, base = {}) {
  const resolved = { ...base };
  const lookup = (name) => resolved[name] ?? map[name];
  for (const [key, raw] of Object.entries(map)) {
    let value = raw;
    for (let i = 0; i < 5 && value.includes("var("); i += 1) {
      value = value.replace(/var\(--([a-z0-9-]+)\)/g, (_, ref) => lookup(ref) ?? `var(--${ref})`);
    }
    resolved[key] = value;
  }
  return resolved;
}

const lightRaw = declarations(block(String.raw`:root,\s*\[data-theme="light"\]`));
const darkRaw = declarations(block(String.raw`\[data-theme="dark"\]`));
const scaleRaw = declarations(block(String.raw`:root(?=\s*\{\s*--space-1)`));

const light = resolveVars(lightRaw);
const dark = resolveVars(darkRaw, light);

const colorKeys = Object.keys(light).filter((k) => /^#[0-9a-f]{6,8}$/i.test(light[k]));
const shadowKeys = ["shadow-sm", "shadow-md"];

function camel(key) {
  return key.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());
}

function colorObject(map) {
  const lines = colorKeys.map((k) => `  ${camel(k)}: "${map[k]}",`);
  return `{\n${lines.join("\n")}\n}`;
}

for (const k of colorKeys) {
  if (!/^#[0-9a-f]{6,8}$/i.test(dark[k])) {
    throw new Error(`Token escuro inválido para ${k}: ${dark[k]}`);
  }
}

const px = (value) => Number(String(value).replace("px", ""));
const space = Object.fromEntries(
  Object.entries(scaleRaw)
    .filter(([k]) => k.startsWith("space-"))
    .map(([k, v]) => [k.slice(6), px(v)]),
);
const radius = Object.fromEntries(
  Object.entries(scaleRaw)
    .filter(([k]) => k.startsWith("radius-"))
    .map(([k, v]) => [k.slice(7), px(v)]),
);

const typography = {};
for (const m of css.matchAll(/\.ae-text-([a-z0-9-]+)\s*\{([^}]*)\}/g)) {
  const body = m[2];
  const size = body.match(/font-size:\s*(\d+)px/);
  const line = body.match(/line-height:\s*(\d+)px/);
  const weight = body.match(/font-weight:\s*(\d+)/);
  const spacing = body.match(/letter-spacing:\s*(-?[\d.]+)em/);
  if (!size || !line || !weight) continue;
  typography[camel(m[1])] = {
    fontSize: Number(size[1]),
    lineHeight: Number(line[1]),
    fontWeight: Number(weight[1]),
    letterSpacingEm: spacing ? Number(spacing[1]) : 0,
  };
}

const shadows = Object.fromEntries(shadowKeys.map((k) => [camel(k), light[k]]));

const out = `// GERADO por scripts/sync-tokens.mjs a partir de
// auroraelo_design_system/static/css/aurora-elo.css — não edite à mão.
/* eslint-disable */

export const lightColors = ${colorObject(light)} as const;

export const darkColors = ${colorObject(dark)} as const;

export type ColorTokens = { [Key in keyof typeof lightColors]: string };

export const space = ${JSON.stringify(space)} as const;

export const radius = ${JSON.stringify(radius)} as const;

export const designTypography = ${JSON.stringify(typography, null, 2)} as const;

export const designShadows = ${JSON.stringify(shadows, null, 2)} as const;

export const designSystemSource = "auroraelo_design_system/static/css/aurora-elo.css";
`;

writeFileSync(resolve(here, "../src/theme/tokens.generated.ts"), out);
console.log(
  `tokens.generated.ts: ${colorKeys.length} cores, ${Object.keys(space).length} espaços, ` +
    `${Object.keys(typography).length} estilos de texto (${cssPath})`,
);
