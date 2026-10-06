import { useCallback, useEffect, useState } from "react";
import { api } from "./http";
export function refresh() {
  window.dispatchEvent(new Event("knowledge-updated"));
}
interface ReadState<T> {
  path: string | null;
  data: T | null;
  error: string | null;
  loading: boolean;
}
/** Scope-owned reads with cancellation and non-overlapping polling. */
export function useData<T>(path: string | null, poll = 0) {
  const [state, setState] = useState<ReadState<T>>({
    path,
    data: null,
    error: null,
    loading: Boolean(path),
  });
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((value) => value + 1), []);
  useEffect(() => {
    window.addEventListener("knowledge-updated", reload);
    return () => window.removeEventListener("knowledge-updated", reload);
  }, [reload]);
  useEffect(() => {
    setState((previous) =>
      previous.path === path
        ? previous
        : { path, data: null, error: null, loading: Boolean(path) },
    );
    if (!path) return;
    const requestPath = path;
    let alive = true;
    let inFlight = false;
    let controller: AbortController | undefined;
    async function load() {
      if (inFlight) return;
      inFlight = true;
      controller = new AbortController();
      const signal = controller.signal;
      try {
        const data = await api<T>(requestPath, "GET", undefined, { signal });
        if (alive && !signal.aborted)
          setState({ path: requestPath, data, error: null, loading: false });
      } catch (error) {
        if (alive && !signal.aborted)
          setState((previous) => ({
            path: requestPath,
            data: previous.path === requestPath ? previous.data : null,
            error:
              error instanceof Error ? error.message : "Service unavailable",
            loading: false,
          }));
      } finally {
        inFlight = false;
      }
    }
    void load();
    const timer =
      poll > 0 ? window.setInterval(() => void load(), poll) : undefined;
    return () => {
      alive = false;
      window.clearInterval(timer);
      controller?.abort();
    };
  }, [path, tick, poll]);
  if (!path) return { data: null, error: null, loading: false, reload };
  if (state.path !== path)
    return { data: null, error: null, loading: true, reload };
  return {
    data: state.data,
    error: state.error,
    loading: state.loading,
    reload,
  };
}
