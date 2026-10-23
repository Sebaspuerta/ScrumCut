import { describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient, loginUrl } from "./client";

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

  it.each([401, 403])("ante un %i manda al login de Django y vuelve a la ruta actual", async (status) => {
    const { client, navigate } = clientWith(jsonResponse({ detail: "No" }, status));
    await expect(client.get("/api/v1/me/")).rejects.toBeInstanceOf(ApiError);
    expect(navigate).toHaveBeenCalledWith("/cuenta/login/?next=%2Fapp%2Fagenda%3Fdia%3Dhoy");
  });

  it("una escritura rechazada (CSRF vencido) también manda al login", async () => {
    const { client, navigate } = clientWith(jsonResponse({ csrf_token: "viejo" }), jsonResponse({}, 403));
    await expect(client.post("/api/v1/branch/", { sede: "norte" })).rejects.toMatchObject({ status: 403 });
    expect(navigate).toHaveBeenCalledWith(loginUrl("/app/agenda?dia=hoy"));
  });

  it("un error del servidor no manda al login", async () => {
    const { client, navigate } = clientWith(jsonResponse({ detail: "Error" }, 500));
    await expect(client.get("/api/v1/me/")).rejects.toMatchObject({ status: 500 });
    expect(navigate).not.toHaveBeenCalled();
  });
});
