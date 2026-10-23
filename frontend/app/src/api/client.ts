// El único cliente HTTP de la app. La sesión viaja en la cookie HttpOnly de Django: aquí no hay tokens
// de sesión, y el token CSRF (la cookie también es HttpOnly) se pide a la API y vive solo en memoria.
import type { paths } from "./schema";

type Method = "get" | "post" | "patch";
type PathWith<M extends Method> = {
  [P in keyof paths]: paths[P][M] extends undefined ? never : P;
}[keyof paths];
type Operation<P extends keyof paths, M extends Method> = NonNullable<paths[P][M]>;
type JsonOf<T> = T extends { content: { "application/json": infer Body } } ? Body : never;
export type ResponseOf<P extends keyof paths, M extends Method> = JsonOf<Operation<P, M>["responses"][200]>;
export type RequestOf<P extends keyof paths, M extends Exclude<Method, "get">> =
  Operation<P, M> extends { requestBody?: infer Body } ? JsonOf<NonNullable<Body>> : never;

export const LOGIN_PATH = "/cuenta/login/";
const CSRF_PATH = "/api/v1/csrf/";
const CSRF_HEADER = "X-CSRFToken";
const UNAUTHORIZED = new Set([401, 403]);

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`La API respondió ${String(status)}`);
    this.name = "ApiError";
  }
}

export interface ApiClientOptions {
  fetch: typeof fetch;
  /** Navegación completa (fuera de la app): al login de Django o a donde redirigió el servidor. */
  navigate: (url: string) => void;
  /** La ruta actual, para volver a ella después de iniciar sesión. */
  currentPath: () => string;
}

export function loginUrl(next: string): string {
  return `${LOGIN_PATH}?${new URLSearchParams({ next }).toString()}`;
}

const JSON_ACCEPT = { Accept: "application/json" };

async function send(options: ApiClientOptions, path: string, init: RequestInit): Promise<unknown> {
  const response = await options.fetch(path, { ...init, credentials: "same-origin" });
  if (response.redirected) {
    // El servidor mandó a otra página (por ejemplo, a configurar la verificación en dos pasos).
    options.navigate(response.url);
    throw new ApiError(response.status);
  }
  if (UNAUTHORIZED.has(response.status)) {
    options.navigate(loginUrl(options.currentPath()));
    throw new ApiError(response.status);
  }
  if (!response.ok) throw new ApiError(response.status);
  return response.json();
}

/** Pide el token CSRF la primera vez que hace falta y lo reutiliza; solo vive en esta closure. */
function csrfTokenSource(options: ApiClientOptions): () => Promise<string> {
  let token: string | null = null;
  return async () => {
    if (token === null) {
      const body = (await send(options, CSRF_PATH, { method: "GET", headers: JSON_ACCEPT })) as ResponseOf<
        typeof CSRF_PATH,
        "get"
      >;
      token = body.csrf_token;
    }
    return token;
  };
}

export function createApiClient(options: ApiClientOptions) {
  const csrfToken = csrfTokenSource(options);
  const write = async (method: string, body: unknown): Promise<RequestInit> => ({
    method,
    headers: { ...JSON_ACCEPT, "Content-Type": "application/json", [CSRF_HEADER]: await csrfToken() },
    body: JSON.stringify(body),
  });
  return {
    async get<P extends PathWith<"get">>(path: P, query?: Record<string, string>): Promise<ResponseOf<P, "get">> {
      const url = query ? `${path}?${new URLSearchParams(query).toString()}` : path;
      return (await send(options, url, { method: "GET", headers: JSON_ACCEPT })) as ResponseOf<P, "get">;
    },
    async post<P extends PathWith<"post">>(path: P, body: RequestOf<P, "post">): Promise<ResponseOf<P, "post">> {
      return (await send(options, path, await write("POST", body))) as ResponseOf<P, "post">;
    },
    async patch<P extends PathWith<"patch">>(path: P, body: RequestOf<P, "patch">): Promise<ResponseOf<P, "patch">> {
      return (await send(options, path, await write("PATCH", body))) as ResponseOf<P, "patch">;
    },
    /** Para los formularios POST a Django (cerrar sesión): el mismo token, solo en memoria. */
    csrfToken,
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

export const api: ApiClient = createApiClient({
  fetch: (input, init) => globalThis.fetch(input, init),
  navigate: (url) => {
    window.location.assign(url);
  },
  currentPath: () => window.location.pathname + window.location.search,
});
