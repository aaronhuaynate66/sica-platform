import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { STORAGE_KEY } from "../use-consent";
import { sanitizeParams, useAnalytics } from "../use-analytics";

beforeEach(() => {
  window.localStorage.clear();
  // Remover gtag/clarity de window entre tests.
  delete (window as unknown as { gtag?: unknown }).gtag;
  delete (window as unknown as { clarity?: unknown }).clarity;
});
afterEach(() => {
  window.localStorage.clear();
});

describe("sanitizeParams", () => {
  it("keeps numbers, booleans and short strings", () => {
    expect(
      sanitizeParams({ a: 1, b: true, c: "demo", d: 0, e: false }),
    ).toEqual({ a: 1, b: true, c: "demo", d: 0, e: false });
  });

  it("drops strings longer than 100 chars (likely PHI)", () => {
    const longStr = "x".repeat(101);
    expect(sanitizeParams({ note: longStr, ok: "short" })).toEqual({
      ok: "short",
    });
  });

  it("accepts strings of exactly 100 chars (boundary)", () => {
    const boundary = "y".repeat(100);
    expect(sanitizeParams({ s: boundary })).toEqual({ s: boundary });
  });

  it("drops null, undefined and empty strings", () => {
    expect(sanitizeParams({ a: null, b: undefined, c: "" })).toEqual({});
  });

  it("drops nested objects and arrays", () => {
    expect(
      sanitizeParams({
        a: 1,
        // @ts-expect-error -- intentional invalid input for sanitizer
        b: { nested: "x" },
        // @ts-expect-error -- intentional invalid input for sanitizer
        c: [1, 2],
      }),
    ).toEqual({ a: 1 });
  });

  it("returns empty object when params is undefined", () => {
    expect(sanitizeParams(undefined)).toEqual({});
  });
});

describe("useAnalytics.trackEvent", () => {
  it("is a noop when consent !== 'granted'", () => {
    const gtag = vi.fn();
    (window as unknown as { gtag: typeof gtag }).gtag = gtag;
    const { result } = renderHook(() => useAnalytics());
    act(() => result.current.trackEvent("click", { x: 1 }));
    expect(gtag).not.toHaveBeenCalled();
  });

  it("calls gtag with sanitized params when consent === 'granted'", () => {
    window.localStorage.setItem(STORAGE_KEY, "granted");
    const gtag = vi.fn();
    (window as unknown as { gtag: typeof gtag }).gtag = gtag;
    const { result } = renderHook(() => useAnalytics());
    act(() => result.current.trackEvent("custom_event", { ok: "demo", n: 7 }));
    expect(gtag).toHaveBeenCalledWith("event", "custom_event", {
      ok: "demo",
      n: 7,
    });
  });

  it("strips PHI-shaped params before calling gtag", () => {
    window.localStorage.setItem(STORAGE_KEY, "granted");
    const gtag = vi.fn();
    (window as unknown as { gtag: typeof gtag }).gtag = gtag;
    const { result } = renderHook(() => useAnalytics());
    const long = "z".repeat(200);
    act(() => result.current.trackEvent("custom_event", { note: long, n: 1 }));
    expect(gtag).toHaveBeenCalledWith("event", "custom_event", { n: 1 });
  });

  it("calls clarity('event', name) without params", () => {
    window.localStorage.setItem(STORAGE_KEY, "granted");
    const clarity = vi.fn();
    (window as unknown as { clarity: typeof clarity }).clarity = clarity;
    const { result } = renderHook(() => useAnalytics());
    act(() => result.current.trackEvent("custom_event", { ok: "demo" }));
    expect(clarity).toHaveBeenCalledWith("event", "custom_event");
  });

  it("isReady reflects gtag/clarity availability gated by consent", () => {
    const { result: noConsent } = renderHook(() => useAnalytics());
    (window as unknown as { gtag: () => void }).gtag = () => {};
    expect(noConsent.current.isReady).toBe(false);

    window.localStorage.setItem(STORAGE_KEY, "granted");
    const { result: withConsent } = renderHook(() => useAnalytics());
    expect(withConsent.current.isReady).toBe(true);
  });
});

describe("useAnalytics.trackPageView", () => {
  it("calls gtag with page_view + page_path when granted", () => {
    window.localStorage.setItem(STORAGE_KEY, "granted");
    const gtag = vi.fn();
    (window as unknown as { gtag: typeof gtag }).gtag = gtag;
    const { result } = renderHook(() => useAnalytics());
    act(() => result.current.trackPageView("/timeline"));
    expect(gtag).toHaveBeenCalledWith("event", "page_view", {
      page_path: "/timeline",
    });
  });

  it("is a noop when consent !== 'granted'", () => {
    const gtag = vi.fn();
    (window as unknown as { gtag: typeof gtag }).gtag = gtag;
    const { result } = renderHook(() => useAnalytics());
    act(() => result.current.trackPageView("/x"));
    expect(gtag).not.toHaveBeenCalled();
  });
});
