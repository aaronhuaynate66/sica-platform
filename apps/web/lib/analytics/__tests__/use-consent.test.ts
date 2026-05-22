import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { STORAGE_KEY, useConsent } from "../use-consent";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});

describe("useConsent", () => {
  it("defaults to 'pending' when localStorage is empty", () => {
    const { result } = renderHook(() => useConsent());
    expect(result.current.consent).toBe("pending");
  });

  it("reads existing state from localStorage on mount", () => {
    window.localStorage.setItem(STORAGE_KEY, "granted");
    const { result } = renderHook(() => useConsent());
    expect(result.current.consent).toBe("granted");
  });

  it("accept() persists 'granted' and updates state", () => {
    const { result } = renderHook(() => useConsent());
    act(() => result.current.accept());
    expect(result.current.consent).toBe("granted");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("granted");
  });

  it("decline() persists 'denied' and updates state", () => {
    const { result } = renderHook(() => useConsent());
    act(() => result.current.decline());
    expect(result.current.consent).toBe("denied");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("denied");
  });

  it("reset() removes storage and goes back to 'pending'", () => {
    window.localStorage.setItem(STORAGE_KEY, "granted");
    const { result } = renderHook(() => useConsent());
    expect(result.current.consent).toBe("granted");
    act(() => result.current.reset());
    expect(result.current.consent).toBe("pending");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("invalid stored value falls back to 'pending'", () => {
    window.localStorage.setItem(STORAGE_KEY, "garbage");
    const { result } = renderHook(() => useConsent());
    expect(result.current.consent).toBe("pending");
  });
});
