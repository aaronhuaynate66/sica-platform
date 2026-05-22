import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// @testing-library/react no limpia automáticamente en Vitest (a diferencia
// de Jest). Sin este afterEach, los renders se acumulan entre tests.
afterEach(() => {
  cleanup();
});
