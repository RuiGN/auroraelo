import * as http from "../../shared/http";

test("funciona com URL parcial do React Native 0.76, não só URL do Node", async () => {
  const original = global.URL;
  global.URL = require("react-native/Libraries/Blob/URL").URL;
  try {
    const client = http.createPublicClient(endpoint, {
      transport: jest.fn().mockResolvedValue(response()),
    });
    await expect(client.get("/public/", valid)).resolves.toEqual({
      title: "synthetic",
    });
  } finally {
    global.URL = original;
  }
});

const endpoint = "https://api.example.org";
const response = (status = 200, value: unknown = { title: "synthetic" }) =>
  ({
    ok: status >= 200 && status < 300,
    status,
    url: endpoint + "/public/",
    headers: { get: () => "application/json" },
    json: async () => value,
  }) as unknown as Response;
const valid = (data: unknown): data is { title: string } =>
  typeof data === "object" &&
  data !== null &&
  "title" in data &&
  typeof data.title === "string";

test("cliente público exige origem HTTPS explícita antes de enviar", async () => {
  expect(http.createPublicClient).toBeDefined();
  for (const base of [
    undefined,
    "",
    "http://api.example.org",
    "https://user:secret@api.example.org",
    "https://api.example.org/path",
    "https://api.example.org?key=secret",
  ]) {
    const transport = jest.fn();
    const client = http.createPublicClient(base, { transport });
    await expect(client.get("/public/", valid)).rejects.toMatchObject({
      code: "configuration",
    });
    expect(transport).not.toHaveBeenCalled();
  }
});

test("GET validado não envia credenciais ou cookies", async () => {
  const transport = jest.fn().mockResolvedValue(response());
  const client = http.createPublicClient(endpoint, { transport });
  await expect(client.get("/public/", valid)).resolves.toEqual({
    title: "synthetic",
  });
  expect(transport).toHaveBeenCalledWith(
    endpoint + "/public/",
    expect.objectContaining({
      method: "GET",
      credentials: "omit",
      redirect: "error",
      signal: expect.anything(),
    }),
  );
  expect(transport.mock.calls[0][1].headers).toEqual({
    Accept: "application/json",
  });
});

test.each([401, 403, 429, 500, 503])(
  "status %s nunca vira sucesso",
  async (status) => {
    const client = http.createPublicClient(endpoint, {
      transport: jest.fn().mockResolvedValue(response(status)),
    });
    await expect(client.get("/public/", valid)).rejects.toMatchObject({
      code: "http",
      status,
    });
  },
);

test("erro de rede é controlado e não expõe corpo/URL", async () => {
  const client = http.createPublicClient(endpoint, {
    transport: jest.fn().mockRejectedValue(new Error("sensitive")),
  });
  await expect(client.get("/public/", valid)).rejects.toMatchObject({
    code: "network",
    message: "network",
  });
});

test("timeout aborta transporte mesmo que ele ignore abort", async () => {
  const transport = jest.fn<ReturnType<typeof fetch>, Parameters<typeof fetch>>(
    () => new Promise<Response>(() => {}),
  );
  const client = http.createPublicClient(endpoint, {
    transport,
    timeoutMs: 10,
  });
  await expect(client.get("/public/", valid)).rejects.toMatchObject({
    code: "timeout",
  });
  expect(transport.mock.calls[0][1]?.signal?.aborted).toBe(true);
});

test("JSON inesperado não vira dado clínico", async () => {
  const client = http.createPublicClient(endpoint, {
    transport: jest.fn().mockResolvedValue(response(200, { dose: "invented" })),
  });
  await expect(client.get("/public/", valid)).rejects.toMatchObject({
    code: "invalid_response",
  });
});

test("redirecionamento não é aceito como resposta válida", async () => {
  const client = http.createPublicClient(endpoint, {
    transport: jest
      .fn()
      .mockResolvedValue({ ...response(), url: "https://other.example.org/" }),
  });
  await expect(client.get("/public/", valid)).rejects.toMatchObject({
    code: "invalid_response",
  });
});

test.each([
  "//other.example.org/",
  "/../private/",
  "/public/?token=a",
  "/public/#a",
  "https://other.example.org",
])("rejeita destino %s", async (path) => {
  const transport = jest.fn();
  const client = http.createPublicClient(endpoint, { transport });
  await expect(client.get(path, valid)).rejects.toMatchObject({
    code: "configuration",
  });
  expect(transport).not.toHaveBeenCalled();
});
