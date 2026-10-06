export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
export interface RequestOptions {
  signal?: AbortSignal;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly detail: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function errorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item: unknown) =>
      object(item) && typeof item.msg === "string" ? [item.msg] : [],
    );
    if (messages.length) return messages.join(". ");
  }
  if (object(detail) && typeof detail.message === "string")
    return detail.message;
  return "Unable to complete this action";
}
/** JSON business endpoints only; streams and originals use their own transport. */
export async function api<T = unknown>(
  path: string,
  method: HttpMethod = "GET",
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch("/api" + path, {
    method,
    signal: options.signal,
    headers:
      form || body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      response.status,
      "The server returned an unreadable response. Try again.",
      null,
    );
  }
  if (!response.ok) {
    const detail = object(data) ? data.detail : data;
    throw new ApiError(response.status, errorMessage(detail), detail);
  }
  // Domain interfaces remain caller-owned until the backend supplies typed responses.
  return data as T;
}
