// El único cliente HTTP de la app. La sesión viaja en la cookie HttpOnly de Django: aquí no hay tokens
// de sesión, y el token CSRF (la cookie también es HttpOnly) se pide a la API y vive solo en memoria.
import type { components, paths } from "./schema";

type Method = "get" | "post" | "patch";
type PathWith<M extends Method> = {
  [P in keyof paths]: paths[P][M] extends undefined ? never : P;
}[keyof paths];
type Operation<P extends keyof paths, M extends Method> = NonNullable<paths[P][M]>;
type JsonOf<T> = T extends { content: { "application/json": infer Body } } ? Body : never;
type Success<R> = R extends { 200: infer Ok } ? Ok : R extends { 201: infer Created } ? Created : never;
export type ResponseOf<P extends keyof paths, M extends Method> = JsonOf<Success<Operation<P, M>["responses"]>>;
export type RequestOf<P extends keyof paths, M extends Exclude<Method, "get">> =
  Operation<P, M> extends { requestBody?: infer Body } ? JsonOf<NonNullable<Body>> : never;
/** Una escritura sin cuerpo (quitar una línea) se envía con `undefined`. */
type BodyOf<P extends keyof paths, M extends Exclude<Method, "get">> = [RequestOf<P, M>] extends [never]
  ? undefined
  : RequestOf<P, M>;
/** Los parámetros de la ruta ({public_id}); las rutas sin parámetros no los reciben. */
export type ParamsOf<P extends keyof paths, M extends Method> =
  Operation<P, M> extends { parameters: { path: infer Params extends Record<string, string> } } ? Params : never;
/** El cuerpo de un 400 de una escritura: el mensaje general y los de cada campo, para mostrarlos tal cual. */
export type ApiErrorBody = components["schemas"]["ApiError"];

export const LOGIN_PATH = "/cuenta/login/";
const CSRF_PATH = "/api/v1/csrf/";
const CSRF_HEADER = "X-CSRFToken";
const UNAUTHORIZED = new Set([401, 403]);

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: ApiErrorBody | null = null,
  ) {
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

function isErrorBody(value: unknown): value is ApiErrorBody {
  return typeof value === "object" && value !== null && "detail" in value && "field_errors" in value;
}

/** Solo un 400 de validación trae mensajes para el usuario; lo demás se muestra con un texto genérico. */
async function errorBody(response: Response): Promise<ApiErrorBody | null> {
  try {
    const body: unknown = await response.json();
    return isErrorBody(body) ? body : null;
  } catch {
    return null;
  }
}

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
  if (!response.ok) throw new ApiError(response.status, await errorBody(response));
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

/** /api/v1/orders/{public_id}/ con sus parámetros, cada uno codificado para la URL. */
function fill(path: string, params: Record<string, string> = {}): string {
  return path.replace(/\{(\w+)\}/g, (_, name: string) => encodeURIComponent(params[name] ?? ""));
}

function withQuery(path: string, query?: Record<string, string>): string {
  return query ? `${path}?${new URLSearchParams(query).toString()}` : path;
}

export function createApiClient(options: ApiClientOptions) {
  const csrfToken = csrfTokenSource(options);
  const write = async (method: string, body: unknown): Promise<RequestInit> => ({
    method,
    headers: { ...JSON_ACCEPT, "Content-Type": "application/json", [CSRF_HEADER]: await csrfToken() },
    body: JSON.stringify(body),
  });
  return {
    async get<P extends PathWith<"get">>(
      path: P,
      query?: Record<string, string>,
      params?: ParamsOf<P, "get">,
    ): Promise<ResponseOf<P, "get">> {
      const url = withQuery(fill(path, params), query);
      return (await send(options, url, { method: "GET", headers: JSON_ACCEPT })) as ResponseOf<P, "get">;
    },
    async post<P extends PathWith<"post">>(
      path: P,
      body: BodyOf<P, "post">,
      params?: ParamsOf<P, "post">,
    ): Promise<ResponseOf<P, "post">> {
      return (await send(options, fill(path, params), await write("POST", body))) as ResponseOf<P, "post">;
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
