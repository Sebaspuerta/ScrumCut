// Los tipos de cada operación de la API (ruta, método, cuerpo, respuesta y parámetros), sacados del esquema OpenAPI.
import type { paths } from "./schema";

type Method = "get" | "post" | "patch";
export type PathWith<M extends Method> = {
  [P in keyof paths]: paths[P][M] extends undefined ? never : P;
}[keyof paths];
type Operation<P extends keyof paths, M extends Method> = NonNullable<paths[P][M]>;
type JsonOf<T> = T extends { content: { "application/json": infer Body } } ? Body : never;
type Success<R> = R extends { 200: infer Ok } ? Ok : R extends { 201: infer Created } ? Created : never;
export type ResponseOf<P extends keyof paths, M extends Method> = JsonOf<Success<Operation<P, M>["responses"]>>;
export type RequestOf<P extends keyof paths, M extends Exclude<Method, "get">> =
  Operation<P, M> extends { requestBody?: infer Body } ? JsonOf<NonNullable<Body>> : never;
/** Una escritura sin cuerpo (quitar una línea) se envía con `undefined`. */
export type BodyOf<P extends keyof paths, M extends Exclude<Method, "get">> = [RequestOf<P, M>] extends [never]
  ? undefined
  : RequestOf<P, M>;
/** Los parámetros de la ruta ({public_id}); las rutas sin parámetros no los reciben. */
export type ParamsOf<P extends keyof paths, M extends Method> =
  Operation<P, M> extends { parameters: { path: infer Params extends Record<string, string> } } ? Params : never;
