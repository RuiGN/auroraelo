import React from "react";
import Svg, { Circle, Path, Rect } from "react-native-svg";

/**
 * Ícones no mesmo traço do design system (24x24, traço 1.75, pontas arredondadas).
 * Os 16 primeiros vêm de auroraelo_design_system/static/icons; os demais seguem
 * a mesma gramática para cobrir as telas do app.
 */
type Shape =
  | string
  | { c: [number, number, number] }
  | { r: [number, number, number, number, number] };

const shapes = {
  // Design system
  alert: [
    "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z",
    "M12 9v4M12 17h.01",
  ],
  bed: ["M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9"],
  building: [
    "M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z",
    "M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4",
  ],
  check: [{ c: [12, 12, 10] }, "m9 12 2 2 4-4"],
  "chevron-down": ["m6 9 6 6 6-6"],
  close: ["M18 6 6 18M6 6l12 12"],
  "heart-pulse": [
    "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z",
    "M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27",
  ],
  info: [{ c: [12, 12, 10] }, "M12 16v-4M12 8h.01"],
  menu: ["M4 6h16M4 12h16M4 18h16"],
  message: ["M7.9 20A9 9 0 1 0 4 16.1L2 22Z"],
  moon: ["M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"],
  patient: [{ c: [12, 8, 5] }, "M20 21a8 8 0 0 0-16 0"],
  pill: [
    "m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z",
    "m8.5 8.5 7 7",
  ],
  stethoscope: [
    "M11 2v2M5 2v2M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1",
    "M8 15a6 6 0 0 0 12 0v-3",
    { c: [20, 10, 2] },
  ],
  sun: [
    { c: [12, 12, 4] },
    "M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41",
  ],
  users: [
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2",
    { c: [9, 7, 4] },
    "M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  ],
  // Extensões
  home: ["M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1Z"],
  calendar: [{ r: [3, 5, 18, 16, 2] }, "M16 3v4M8 3v4M3 11h18"],
  book: [
    "M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2Z",
    "M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7Z",
  ],
  pen: ["M12 20h9", "M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"],
  target: [{ c: [12, 12, 10] }, { c: [12, 12, 6] }, { c: [12, 12, 2] }],
  phone: [
    "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92Z",
  ],
  shield: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"],
  sliders: [
    "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",
  ],
  globe: [
    { c: [12, 12, 10] },
    "M2 12h20",
    "M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10Z",
  ],
  heart: [
    "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78Z",
  ],
  "chevron-right": ["m9 6 6 6-6 6"],
  "chevron-left": ["m15 6-6 6 6 6"],
  plus: ["M12 5v14M5 12h14"],
  clock: [{ c: [12, 12, 10] }, "M12 6v6l4 2"],
  file: [
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z",
    "M14 2v6h6M16 13H8M16 17H8M10 9H8",
  ],
  lifebuoy: [
    { c: [12, 12, 10] },
    { c: [12, 12, 4] },
    "m4.93 4.93 4.24 4.24M14.83 9.17l4.24-4.24M14.83 14.83l4.24 4.24M9.17 14.83l-4.24 4.24",
  ],
  lock: [{ r: [3, 11, 18, 11, 2] }, "M7 11V7a5 5 0 0 1 10 0v4"],
  eye: ["M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z", { c: [12, 12, 3] }],
  send: ["M22 2 11 13M22 2l-7 20-4-9-9-4Z"],
  checklist: ["m3 17 2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8"],
  "arrow-right": ["M5 12h14M12 5l7 7-7 7"],
  activity: ["M22 12h-4l-3 9L9 3l-3 9H2"],
  battery: [{ r: [2, 7, 16, 10, 2] }, "M22 11v2M6 11v2"],
  leaf: [
    "M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z",
    "M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12",
  ],
  star: [
    "m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1Z",
  ],
  smile: [{ c: [12, 12, 10] }, "M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"],
  wind: [
    "M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2M9.6 4.6A2 2 0 1 1 11 8H2M12.6 19.4A2 2 0 1 0 14 16H2",
  ],
  bell: [
    "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9",
    "M10.3 21a1.94 1.94 0 0 0 3.4 0",
  ],
  play: ["m6 3 14 9-14 9Z"],
  headphones: [
    "M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3",
  ],
  refresh: ["M21 12a9 9 0 1 1-3-6.7L21 8", "M21 3v5h-5"],
} satisfies Record<string, Shape[]>;

export type IconName = keyof typeof shapes;

interface IconProps {
  name: IconName;
  size?: number;
  color: string;
  strokeWidth?: number;
}

/** Ícone decorativo: o rótulo acessível fica no controle que o contém. */
export function Icon({
  name,
  size = 20,
  color,
  strokeWidth = 1.75,
}: IconProps) {
  const list: Shape[] = shapes[name];
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      {list.map((shape, index) => {
        if (typeof shape === "string") return <Path key={index} d={shape} />;
        if ("c" in shape) {
          return (
            <Circle
              key={index}
              cx={shape.c[0]}
              cy={shape.c[1]}
              r={shape.c[2]}
            />
          );
        }
        const [x, y, width, height, rx] = shape.r;
        return (
          <Rect key={index} x={x} y={y} width={width} height={height} rx={rx} />
        );
      })}
    </Svg>
  );
}
