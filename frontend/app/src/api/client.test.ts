import { describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient, OfflineError } from "./client";

type FetchMock = ReturnType<typeof vi.fn<typeof globalThis.fetch>>;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function clientWith(...responses: Response[]) {
  const fetch = vi.fn<typeof globalThis.fetch>();
  for (const response of responses) fetch.mockResolvedValueOnce(response);
  const navigate = vi.fn<(url: string) => void>();
  const client = createApiClient({ fetch, navigate, currentPath: () => "/app/agenda?dia=hoy" });
  return { client, fetch, navigate };
}

function headersOf(fetch: FetchMock, call: number): Headers {
  return new Headers(fetch.mock.calls[call]?.[1]?.headers);
}

const CSRF_FAILED = { detail: "Tu sesión cambió. Vuelve a cargar la página.", code: "csrf_failed", field_errors: {} };
const BRANCH_STATE = { mode: "una", current_label: "Norte", options: [], can_view_all: false, can_manage: false };

describe("cliente HTTP", () => {
  it("envía las cookies de la sesión y no agrega token CSRF en las lecturas", async () => {
    const { client, fetch } = clientWith(jsonResponse({ user: {} }));
    await client.get("/api/v1/me/");
    expect(fetch.mock.calls[0]?.[1]?.credentials).toBe("same-origin");
    expect(headersOf(fetch, 0).has("X-CSRFToken")).toBe(false);
  });

  it("pide el token CSRF una vez y lo pone en el encabezado de cada escritura", async () => {
    const { client, fetch } = clientWith(
      jsonResponse({ csrf_token: "token-1" }),
      jsonResponse(BRANCH_STATE),
      jsonResponse(BRANCH_STATE),
    );
    await client.post("/api/v1/branch/", { sede: "norte" });
    await client.post("/api/v1/branch/", { sede: "centro" });
    expect(fetch.mock.calls.map((call) => call[0])).toEqual(["/api/v1/csrf/", "/api/v1/branch/", "/api/v1/branch/"]);
    expect(headersOf(fetch, 1).get("X-CSRFToken")).toBe("token-1");
    expect(headersOf(fetch, 2).get("X-CSRFToken")).toBe("token-1");
    expect(fetch.mock.calls[1]?.[1]?.body).toBe(JSON.stringify({ sede: "norte" }));
  });

  it.each([
    [401, "not_authenticated"],
    [403, "not_authenticated"],
  ])("sin sesión (%i, %s) manda al login de Django y vuelve a la ruta actual", async (status, code) => {
    const { client, navigate } = clientWith(jsonResponse({ detail: "Inicia sesión", code, field_errors: {} }, status));
    await expect(client.get("/api/v1/me/")).rejects.toBeInstanceOf(ApiError);
    expect(navigate).toHaveBeenCalledWith("/cuenta/login/?next=%2Fapp%2Fagenda%3Fdia%3Dhoy");
  });

  it("un 403 por falta de permiso NO manda al login: la pantalla lo dice", async () => {
    const denied = { detail: "No tienes permiso para esta acción.", code: "permission_denied", field_errors: {} };
    const { client, navigate } = clientWith(jsonResponse(denied, 403));
    await expect(client.get("/api/v1/dashboard/")).rejects.toMatchObject({ status: 403, body: denied });
    expect(navigate).not.toHaveBeenCalled();
  });

  it("con el token CSRF vencido y la sesión viva pide otro y reintenta una vez, sin pasar por el login", async () => {
    const { client, fetch, navigate } = clientWith(
      jsonResponse({ csrf_token: "viejo" }),
      jsonResponse(CSRF_FAILED, 403),
      jsonResponse({ csrf_token: "nuevo" }),
      jsonResponse(BRANCH_STATE),
    );

    await expect(client.post("/api/v1/branch/", { sede: "norte" })).resolves.toEqual(BRANCH_STATE);

    expect(fetch.mock.calls.map((call) => call[0])).toEqual([
      "/api/v1/csrf/",
      "/api/v1/branch/",
      "/api/v1/csrf/",
      "/api/v1/branch/",
    ]);
    expect(headersOf(fetch, 3).get("X-CSRFToken")).toBe("nuevo");
    expect(navigate).not.toHaveBeenCalled();
  });

  it("si el reintento también falla por CSRF, el error llega a la pantalla sin otro intento ni login", async () => {
    const { client, fetch, navigate } = clientWith(
      jsonResponse({ csrf_token: "viejo" }),
      jsonResponse(CSRF_FAILED, 403),
      jsonResponse({ csrf_token: "nuevo" }),
      jsonResponse(CSRF_FAILED, 403),
    );

    await expect(client.post("/api/v1/branch/", { sede: "norte" })).rejects.toMatchObject({
      status: 403,
      body: CSRF_FAILED,
    });

    expect(fetch).toHaveBeenCalledTimes(4);
    expect(navigate).not.toHaveBeenCalled();
  });

  it("el reintento de un cobro rápido repite la misma llave: no se cobra dos veces", async () => {
    const charge = {
      request_key: crypto.randomUUID(),
      barber: crypto.randomUUID(),
      service: crypto.randomUUID(),
      product: null,
      method: "efectivo",
      reference: "",
    };
    const { client, fetch } = clientWith(
      jsonResponse({ csrf_token: "viejo" }),
      jsonResponse(CSRF_FAILED, 403),
      jsonResponse({ csrf_token: "nuevo" }),
      jsonResponse({}),
    );

    await client.post("/api/v1/orders/quick-charge/", charge);

    const [first, retry] = [fetch.mock.calls[1]?.[1]?.body, fetch.mock.calls[3]?.[1]?.body];
    expect(retry).toBe(first);
    expect(typeof retry === "string" ? JSON.parse(retry) : null).toMatchObject({ request_key: charge.request_key });
  });

  it("sin conexión rechaza con OfflineError y no navega", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockRejectedValue(new TypeError("Failed to fetch"));
    const navigate = vi.fn<(url: string) => void>();
    const client = createApiClient({ fetch, navigate, currentPath: () => "/app/" });
    await expect(client.get("/api/v1/me/")).rejects.toBeInstanceOf(OfflineError);
    expect(navigate).not.toHaveBeenCalled();
  });

  it("un error del servidor no manda al login", async () => {
    const { client, navigate } = clientWith(jsonResponse({ detail: "Error" }, 500));
    await expect(client.get("/api/v1/me/")).rejects.toMatchObject({ status: 500 });
    expect(navigate).not.toHaveBeenCalled();
  });
});
