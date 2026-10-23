import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./api/client";

const MAX_RETRIES = 2;
const SERVER_ERROR = 500;

/** Reintenta solo fallas de red o del servidor: un 4xx no cambia por repetirlo. */
function shouldRetry(failures: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < SERVER_ERROR) return false;
  return failures < MAX_RETRIES;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: shouldRetry, refetchOnWindowFocus: false } } });
}
