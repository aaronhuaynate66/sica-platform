import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  extractFromPdf,
  getHealth,
  getModels,
} from "../client";
import {
  ApiError,
  ApiTimeoutError,
  ApiUnavailableError,
} from "../types";

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("getHealth", () => {
  it("returns parsed body when API responds 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          status: "ok",
          version: "0.1.0",
          extractor_available: true,
        }),
      ),
    );

    const health = await getHealth({ baseUrl: "http://api.test" });
    expect(health).toEqual({
      status: "ok",
      version: "0.1.0",
      extractor_available: true,
    });
  });

  it("throws ApiError on 503 with structured body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: "extractor_unavailable",
            detail: "missing key",
            request_id: "rid-xyz",
          }),
          { status: 503, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    await expect(getHealth({ baseUrl: "http://api.test" })).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      code: "extractor_unavailable",
    });
  });
});

describe("getModels", () => {
  it("returns the model list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse([
          {
            id: "claude-sonnet-4-5-20250929",
            provider: "anthropic",
            type: "cloud",
            phi_allowed: false,
            active: true,
            role: "dev_only",
            notes: "",
          },
        ]),
      ),
    );

    const models = await getModels({ baseUrl: "http://api.test" });
    expect(models).toHaveLength(1);
    expect(models[0].id).toBe("claude-sonnet-4-5-20250929");
  });
});

describe("extractFromPdf", () => {
  it("posts multipart/form-data and parses the summary", async () => {
    const fetchSpy = vi.fn(async (_url, init: RequestInit) => {
      expect(init.method).toBe("POST");
      expect(init.body).toBeInstanceOf(FormData);
      return jsonResponse({
        patient_age: 32,
        gestational_age_weeks: 28.3,
        fum: null,
        fpp: null,
        active_problems: [],
        risk_factors: [],
        lab_results: [],
        notes_summary: "ok",
        confidence_score: 0.9,
        evidence_spans: [],
      });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const file = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], "x.pdf", {
      type: "application/pdf",
    });
    const summary = await extractFromPdf(file, { baseUrl: "http://api.test" });
    expect(summary.patient_age).toBe(32);
    expect(summary.confidence_score).toBe(0.9);
    expect(fetchSpy).toHaveBeenCalledOnce();
  });

  it("translates 500 into ApiError with error_id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: "extraction_failed",
            detail: "boom",
            request_id: "rid-1",
            error_id: "err-99",
          }),
          { status: 500, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    const file = new File(["x"], "x.pdf", { type: "application/pdf" });
    await expect(
      extractFromPdf(file, { baseUrl: "http://api.test" }),
    ).rejects.toSatisfy((e: unknown) => {
      const err = e as ApiError;
      return (
        err.name === "ApiError" &&
        err.status === 500 &&
        err.code === "extraction_failed" &&
        err.errorId === "err-99"
      );
    });
  });
});

describe("transport errors", () => {
  it("raises ApiTimeoutError when fetch is aborted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url, init: RequestInit) => {
        const signal = init.signal as AbortSignal | undefined;
        return await new Promise<Response>((_resolve, reject) => {
          signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        });
      }),
    );

    await expect(
      getHealth({ baseUrl: "http://api.test", timeoutMs: 10 }),
    ).rejects.toBeInstanceOf(ApiTimeoutError);
  });

  it("raises ApiUnavailableError when fetch rejects with a network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );

    await expect(getHealth({ baseUrl: "http://api.test" })).rejects.toBeInstanceOf(
      ApiUnavailableError,
    );
  });
});
