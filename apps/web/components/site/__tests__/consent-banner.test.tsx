import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ConsentBanner } from "../consent-banner";
import { STORAGE_KEY } from "@/lib/analytics/use-consent";

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  window.localStorage.clear();
});

describe("ConsentBanner", () => {
  it("renders when consent state is pending (default)", () => {
    render(<ConsentBanner />);
    expect(screen.getByTestId("consent-banner")).toBeTruthy();
    expect(screen.getByTestId("consent-accept")).toBeTruthy();
    expect(screen.getByTestId("consent-decline")).toBeTruthy();
  });

  it("does NOT render when consent === 'granted'", () => {
    window.localStorage.setItem(STORAGE_KEY, "granted");
    render(<ConsentBanner />);
    expect(screen.queryByTestId("consent-banner")).toBeNull();
  });

  it("does NOT render when consent === 'denied'", () => {
    window.localStorage.setItem(STORAGE_KEY, "denied");
    render(<ConsentBanner />);
    expect(screen.queryByTestId("consent-banner")).toBeNull();
  });

  it("clicking 'Aceptar' hides the banner and persists 'granted'", () => {
    render(<ConsentBanner />);
    fireEvent.click(screen.getByTestId("consent-accept"));
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("granted");
    expect(screen.queryByTestId("consent-banner")).toBeNull();
  });

  it("clicking 'Rechazar' hides the banner and persists 'denied'", () => {
    render(<ConsentBanner />);
    fireEvent.click(screen.getByTestId("consent-decline"));
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("denied");
    expect(screen.queryByTestId("consent-banner")).toBeNull();
  });

  it("includes a link to /privacy", () => {
    render(<ConsentBanner />);
    const link = screen.getByRole("link", { name: /saber más/i }) as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe("/privacy");
  });
});
