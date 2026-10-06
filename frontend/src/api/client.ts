import { useCallback, useEffect, useState } from "react";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail: unknown,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch("/api" + path, {
    method,
    headers: form ? {} : body ? { "Content-Type": "application/json" } : {},
    body: body ? (form ? body : JSON.stringify(body)) : undefined,
  });
  const data = await response
    .json()
    .catch(() => ({ detail: "Service unavailable" }));
  if (!response.ok) {
    const d = data.detail;
    throw new ApiError(
      response.status,
      typeof d === "string"
        ? d
        : Array.isArray(d)
          ? d.map((e: { msg: string }) => e.msg).join(". ")
          : d?.message || "Unable to complete this action",
      d,
    );
  }
  return data as T;
}
export function refresh() {
  window.dispatchEvent(new Event("knowledge-updated"));
}
export function useData<T>(path: string | null, poll = 0) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState<string | null>(null),
    [loading, setLoading] = useState(true),
    [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  useEffect(() => {
    window.addEventListener("knowledge-updated", reload);
    return () => window.removeEventListener("knowledge-updated", reload);
  }, [reload]);
  useEffect(() => {
    if (!path) {
      setLoading(false);
      setData(null);
      return;
    }
    let alive = true;
    const load = () =>
      api<T>(path)
        .then((d) => {
          if (alive) {
            setData(d);
            setError(null);
            setLoading(false);
          }
        })
        .catch((e) => {
          if (alive) {
            setError(e.message);
            setLoading(false);
          }
        });
    load();
    const timer = poll ? setInterval(load, poll) : undefined;
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [path, tick, poll]);
  return { data, error, loading, reload };
}
