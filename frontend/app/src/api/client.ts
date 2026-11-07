// El único cliente HTTP de la app. La sesión viaja en la cookie HttpOnly de Django: aquí no hay tokens
// de sesión, y el token CSRF (la cookie también es HttpOnly) se pide a la API y vive solo en memoria.
import type { BodyOf, ParamsOf, PathWith, RequestOf, ResponseOf } from "./operations";
import type { components } from "./schema";
import { fill, withQuery } from "./url";

/** El cuerpo de un 400 de una escritura: el mensaje general y los de cada campo, para mostrarlos tal cual. */
export type ApiErrorBody = components["schemas"]["ApiError"];

export const LOGIN_PATH = "/cuenta/login/";
const CSRF_PATH = "/api/v1/csrf/";
const CSRF_HEADER = "X-CSRFToken";
const UNAUTHORIZED = 401;
/** Sin sesión, la API responde 403 con este código (no usa 401). Un 403 por falta de permiso trae
 * `permission_denied` y no saca a nadie de la pantalla. */
const NO_SESSION = "not_authenticated";
/** El token CSRF ya no corresponde a la sesión (que sigue viva): se pide otro y se reintenta una vez. */
const CSRF_FAILED = "csrf_failed";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: ApiErrorBody | null = null,
  ) {
    super(`La API respondió ${String(status)}`);
    this.name = "ApiError";
  }
}

/** El servidor no respondió: sin conexión o la red cortó la petición. */
export class OfflineError extends Error {
  constructor() {
    super("No hubo respuesta del servidor");
    this.name = "OfflineError";
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

async function request(options: ApiClientOptions, path: string, init: RequestInit): Promise<Response> {
  try {
    return await options.fetch(path, { ...init, credentials: "same-origin" });
  } catch (error) {
    // fetch solo rechaza con TypeError cuando no hubo respuesta (sin red, servidor caído o petición cortada).
    if (error instanceof TypeError) throw new OfflineError();
    throw error;
  }
}

async function send(options: ApiClientOptions, path: string, init: RequestInit): Promise<unknown> {
  const response = await request(options, path, init);
  if (response.redirected) {
    // El servidor mandó a otra página (por ejemplo, a configurar la verificación en dos pasos).
    options.navigate(response.url);
    throw new ApiError(response.status);
  }
  if (response.ok) return response.json();
  const body = await errorBody(response);
  // Solo sin sesión se va al login (y se vuelve aquí); sin permiso, la pantalla lo dice.
  if (response.status === UNAUTHORIZED || body?.code === NO_SESSION) {
    options.navigate(loginUrl(options.currentPath()));
  }
  throw new ApiError(response.status, body);
}

interface CsrfTokenSource {
  get: () => Promise<string>;
  /** Olvida el token: el siguiente `get` pide uno nuevo. */
  renew: () => void;
}

/** Pide el token CSRF la primera vez que hace falta y lo reutiliza; solo vive en esta closure. */
function csrfTokenSource(options: ApiClientOptions): CsrfTokenSource {
  let token: string | null = null;
  return {
    async get() {
      if (token === null) {
        const body = (await send(options, CSRF_PATH, { method: "GET", headers: JSON_ACCEPT })) as ResponseOf<
          typeof CSRF_PATH,
          "get"
        >;
        token = body.csrf_token;
      }
      return token;
    },
    renew() {
      token = null;
    },
  };
}

const isCsrfFailure = (error: unknown) => error instanceof ApiError && error.body?.code === CSRF_FAILED;

/** JSON o multipart (la foto de un producto): con FormData el navegador pone el Content-Type con su límite. */
async function writeInit(csrf: CsrfTokenSource, method: string, body: string | FormData): Promise<RequestInit> {
  const type = typeof body === "string" ? { "Content-Type": "application/json" } : {};
  return { method, headers: { ...JSON_ACCEPT, ...type, [CSRF_HEADER]: await csrf.get() }, body };
}

/** Con el token vencido y la sesión viva, pide otro y repite una sola vez la misma petición: el mismo cuerpo, así
 * que una escritura de dinero conserva su `request_key` y no se duplica. Un segundo fallo llega a la pantalla. */
function writer(options: ApiClientOptions, csrf: CsrfTokenSource) {
  return async (method: string, path: string, body: string | FormData): Promise<unknown> => {
    try {
      return await send(options, path, await writeInit(csrf, method, body));
    } catch (error) {
      if (!isCsrfFailure(error)) throw error;
      csrf.renew();
      return send(options, path, await writeInit(csrf, method, body));
    }
  };
}

/** Las escrituras: JSON (post y patch) o multipart (upload), todas con CSRF y su único reintento. */
function writes(write: ReturnType<typeof writer>) {
  return {
    async post<P extends PathWith<"post">>(
      path: P,
      body: BodyOf<P, "post">,
      params?: ParamsOf<P, "post">,
    ): Promise<ResponseOf<P, "post">> {
      return (await write("POST", fill(path, params), JSON.stringify(body))) as ResponseOf<P, "post">;
    },
    /** Un archivo por multipart (la foto de un producto), con el mismo token CSRF y el mismo reintento. */
    async upload<P extends PathWith<"post">>(
      path: P,
      form: FormData,
      params?: ParamsOf<P, "post">,
    ): Promise<ResponseOf<P, "post">> {
      return (await write("POST", fill(path, params), form)) as ResponseOf<P, "post">;
    },
    async patch<P extends PathWith<"patch">>(path: P, body: RequestOf<P, "patch">): Promise<ResponseOf<P, "patch">> {
      return (await write("PATCH", path, JSON.stringify(body))) as ResponseOf<P, "patch">;
    },
  };
}

export function createApiClient(options: ApiClientOptions) {
  const csrf = csrfTokenSource(options);
  return {
    async get<P extends PathWith<"get">>(
      path: P,
      query?: Record<string, string>,
      params?: ParamsOf<P, "get">,
    ): Promise<ResponseOf<P, "get">> {
      const url = withQuery(fill(path, params), query);
      return (await send(options, url, { method: "GET", headers: JSON_ACCEPT })) as ResponseOf<P, "get">;
    },
    ...writes(writer(options, csrf)),
    /** Para los formularios POST a Django (cerrar sesión): el mismo token, solo en memoria. */
    csrfToken: csrf.get,
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
