export type ErrorCode =
  | "configuration"
  | "network"
  | "timeout"
  | "http"
  | "invalid_response"
  | "unavailable";
export class ApiError extends Error {
  constructor(
    public readonly code: ErrorCode,
    public readonly status?: number,
  ) {
    super(code);
    this.name = "ApiError";
  }
}
type Options = { transport?: typeof fetch; timeoutMs?: number };

// Apenas transporte público GET. Nenhum contrato clínico é presumido.
export function createPublicClient(
  base: string | undefined,
  options: Options = {},
) {
  return {
    async get<T>(
      path: string,
      validate: (value: unknown) => value is T,
    ): Promise<T> {
      // Gramática deliberadamente restrita: DNS ASCII, HTTPS, porta opcional.
      // A URL global do RN 0.76 não implementa protocol/origin/username.
      const origin = base?.match(
        /^https:\/\/([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+)(?::([0-9]{1,5}))?\/?$/,
      );
      if (
        !origin ||
        (origin[2] && (Number(origin[2]) < 1 || Number(origin[2]) > 65535))
      ) {
        throw new ApiError("configuration");
      }
      if (!/^\/(?:[a-zA-Z0-9_-]+\/)*$/.test(path))
        throw new ApiError("configuration");
      const timeoutMs = options.timeoutMs ?? 8000;
      if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 30000) {
        throw new ApiError("configuration");
      }
      const url =
        "https://" + origin[1] + (origin[2] ? ":" + origin[2] : "") + path;
      const controller = new AbortController();
      let timer: ReturnType<typeof setTimeout> | undefined;
      const timeout = new Promise<never>((_, reject) => {
        timer = setTimeout(() => {
          reject(new ApiError("timeout"));
          controller.abort();
        }, timeoutMs);
      });
      async function request(): Promise<T> {
        const response = await (options.transport ?? fetch)(url, {
          method: "GET",
          credentials: "omit",
          redirect: "error",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) throw new ApiError("http", response.status);
        // RN pode seguir redirects antes desta checagem: só usar para dados públicos.
        if (
          response.url !== url ||
          !response.headers.get("content-type")?.includes("application/json")
        ) {
          throw new ApiError("invalid_response");
        }
        let data: unknown;
        try {
          data = await response.json();
        } catch {
          throw new ApiError("invalid_response");
        }
        if (!validate(data)) throw new ApiError("invalid_response");
        return data;
      }
      try {
        return await Promise.race([request(), timeout]);
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError("network");
      } finally {
        clearTimeout(timer);
      }
    },
  };
}
