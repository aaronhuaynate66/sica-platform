import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearAvailabilityCache,
  getConfiguredMode,
  isApiAvailable,
  resolveEffectiveMode,
} from "../mode-detector";

const ORIGINAL_MODE = process.env.NEXT_PUBLIC_API_MODE;

beforeEach(() => {
  clearAvailabilityCache();
  vi.unstubAllGlobals();
});

afterEach(() => {
  process.env.NEXT_PUBLIC_API_MODE = ORIGINAL_MODE;
});

describe("getConfiguredMode", () => {
  it("returns 'demo' when env var is missing or invalid", () => {
    delete process.env.NEXT_PUBLIC_API_MODE;
    expect(getConfiguredMode()).toBe("demo");
    process.env.NEXT_PUBLIC_API_MODE = "garbage";
    expect(getConfiguredMode()).toBe("demo");
  });

  it("returns 'live' only when the env var is exactly 'live'", () => {
    process.env.NEXT_PUBLIC_API_MODE = "live";
    expect(getConfiguredMode()).toBe("live");
    process.env.NEXT_PUBLIC_API_MODE = "LIVE";
    expect(getConfiguredMode()).toBe("live");
  });
});

describe("isApiAvailable", () => {
  it("returns false without hitting the network in demo mode", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "demo";
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    await expect(isApiAvailable()).resolves.toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns true when /health responds ok in live mode", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "live";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({ status: "ok", version: "0.1.0", extractor_available: true }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );
    await expect(isApiAvailable()).resolves.toBe(true);
  });

  it("returns false when /health rejects (network error)", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "live";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    await expect(isApiAvailable()).resolves.toBe(false);
  });
});

describe("resolveEffectiveMode", () => {
  it("falls back to demo when configured=live but API is down", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "live";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    await expect(resolveEffectiveMode()).resolves.toBe("demo");
  });
});
