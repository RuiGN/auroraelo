// O Expo substitui `process.env.EXPO_PUBLIC_*` em tempo de compilação.
declare const process: {
  env: {
    EXPO_PUBLIC_APP_MODE?: string;
    EXPO_PUBLIC_API_BASE_URL?: string;
  } & Record<string, string | undefined>;
};
