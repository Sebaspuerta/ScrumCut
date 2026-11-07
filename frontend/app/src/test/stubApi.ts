// fetch falso para las pruebas: cada ruta de la API responde con su cuerpo, con un error o con la red caída.
import { vi } from "vitest";

function pathOf(input: RequestInfo | URL): string {
  const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  return raw.split("?")[0] ?? raw;
}

/** Una respuesta de error de la API para stubApi; con estado 0, la red caída (fetch rechaza). */
export class FakeFailure {
  constructor(
    readonly status: number,
    readonly body: unknown = {},
  ) {}
}

export const NETWORK_DOWN = new FakeFailure(0);

function respond(body: unknown): Promise<Response> {
  if (body instanceof FakeFailure) {
    if (body.status === NETWORK_DOWN.status) return Promise.reject(new TypeError("Failed to fetch"));
    return Promise.resolve(new Response(JSON.stringify(body.body), { status: body.status }));
  }
  const status = body === undefined ? 404 : 200;
  return Promise.resolve(new Response(JSON.stringify(body ?? {}), { status }));
}

/** fetch falso: cada ruta de la API responde con su cuerpo; una ruta sin cuerpo, 404 (sin reintentos). */
export function stubApi(bodies: Record<string, unknown>) {
  const fetch = vi.fn<typeof globalThis.fetch>((input) => respond(bodies[pathOf(input)]));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
