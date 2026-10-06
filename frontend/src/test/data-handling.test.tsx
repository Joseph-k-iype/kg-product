import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, refresh, useData } from "@/api/client";

const fetchMock = vi.fn<typeof fetch>();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((fulfill) => {
    resolve = fulfill;
  });
  return { promise, resolve };
}

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("shared API transport", () => {
  it("rejects a malformed successful JSON response rather than returning fabricated data", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("<html>proxy error</html>", { status: 200 }),
    );
    await expect(api("/products")).rejects.toBeInstanceOf(ApiError);
  });
  it("retains FastAPI validation status and useful error details", async () => {
    fetchMock.mockResolvedValueOnce(
      json({ detail: [{ msg: "Enter a product name" }] }, 422),
    );
    await expect(api("/products", "POST", { name: "" })).rejects.toMatchObject({
      status: 422,
      message: "Enter a product name",
    });
  });
  it("keeps a transport failure explicit", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Connection closed"));
    await expect(api("/health")).rejects.toThrow("Connection closed");
  });
});

describe("scope-owned server reads", () => {
  it("clears prior-scope data immediately while the next scope is loading", async () => {
    const next = deferred<Response>();
    fetchMock
      .mockResolvedValueOnce(json({ name: "First product" }))
      .mockReturnValueOnce(next.promise);
    const { result, rerender } = renderHook(
      ({ path }) => useData<{ name: string }>(path),
      { initialProps: { path: "/products/first" } },
    );
    await waitFor(() =>
      expect(result.current.data?.name).toBe("First product"),
    );
    rerender({ path: "/products/second" });
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(true);
    await act(async () => next.resolve(json({ name: "Second product" })));
    await waitFor(() =>
      expect(result.current.data?.name).toBe("Second product"),
    );
  });
  it("disabled reads discard an error from the previous scope", async () => {
    fetchMock.mockResolvedValueOnce(json({ detail: "Fact not found" }, 404));
    const { result, rerender } = renderHook(({ path }) => useData(path), {
      initialProps: { path: "/entities/missing" as string | null },
    });
    await waitFor(() => expect(result.current.error).toBe("Fact not found"));
    rerender({ path: null });
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });
  it("does not overlap slow polling requests", async () => {
    vi.useFakeTimers();
    const pending = deferred<Response>();
    fetchMock.mockReturnValue(pending.promise);
    const { result } = renderHook(() =>
      useData<{ ready: boolean }>("/processing", 100),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(350);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.current.data).toBeNull();
    await act(async () => pending.resolve(json({ ready: true })));
    expect(result.current.data).toEqual({ ready: true });
  });
  it("releases an in-flight request when its view unmounts", () => {
    fetchMock.mockReturnValue(new Promise(() => {}));
    const { unmount } = renderHook(() => useData("/documents/one"));
    const options = fetchMock.mock.calls[0]?.[1];
    const signal = options?.signal;
    expect(signal).toBeInstanceOf(AbortSignal);
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});

it("revisiting a scope while an intervening read is pending starts fresh", async () => {
  const second = deferred<Response>();
  const revisited = deferred<Response>();
  fetchMock
    .mockResolvedValueOnce(json({ name: "Old first product" }))
    .mockReturnValueOnce(second.promise)
    .mockReturnValueOnce(revisited.promise);
  const { result, rerender } = renderHook(
    ({ path }) => useData<{ name: string }>(path),
    { initialProps: { path: "/first" } },
  );
  await waitFor(() =>
    expect(result.current.data?.name).toBe("Old first product"),
  );
  rerender({ path: "/second" });
  rerender({ path: "/first" });
  expect(result.current.data).toBeNull();
  expect(result.current.loading).toBe(true);
  await act(async () =>
    revisited.resolve(json({ name: "Updated first product" })),
  );
  expect(result.current.data?.name).toBe("Updated first product");
});

it("re-enabling a disabled scope does not restore an obsolete error", async () => {
  const retried = deferred<Response>();
  fetchMock
    .mockResolvedValueOnce(json({ detail: "Earlier error" }, 404))
    .mockReturnValueOnce(retried.promise);
  const { result, rerender } = renderHook(({ path }) => useData(path), {
    initialProps: { path: "/first" as string | null },
  });
  await waitFor(() => expect(result.current.error).toBe("Earlier error"));
  rerender({ path: null });
  rerender({ path: "/first" });
  expect(result.current.error).toBeNull();
  expect(result.current.loading).toBe(true);
});

it("ignores an obsolete response even when a transport does not honor abort", async () => {
  const old = deferred<Response>();
  fetchMock
    .mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce(json({ name: "Current product" }));
  const { result, rerender } = renderHook(
    ({ path }) => useData<{ name: string }>(path),
    { initialProps: { path: "/old" } },
  );
  rerender({ path: "/current" });
  await waitFor(() =>
    expect(result.current.data?.name).toBe("Current product"),
  );
  await act(async () => old.resolve(json({ name: "Obsolete product" })));
  expect(result.current.data?.name).toBe("Current product");
});

it("refreshes active reads while retaining last-known data for the same scope", async () => {
  const updated = deferred<Response>();
  fetchMock
    .mockResolvedValueOnce(json({ name: "First snapshot" }))
    .mockReturnValueOnce(updated.promise);
  const { result } = renderHook(() => useData<{ name: string }>("/product"));
  await waitFor(() => expect(result.current.data?.name).toBe("First snapshot"));
  act(() => refresh());
  expect(result.current.data?.name).toBe("First snapshot");
  await act(async () => updated.resolve(json({ name: "Updated snapshot" })));
  expect(result.current.data?.name).toBe("Updated snapshot");
});
