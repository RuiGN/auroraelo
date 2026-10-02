// O Expo substitui `process.env.EXPO_PUBLIC_*` em tempo de compilação.
declare const process: {
  env: { EXPO_PUBLIC_APP_MODE?: string } & Record<string, string | undefined>;
};
