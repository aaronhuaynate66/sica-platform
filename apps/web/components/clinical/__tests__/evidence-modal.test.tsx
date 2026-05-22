import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvidenceModal } from "../evidence-modal";
import type { EvidenceSpan } from "@/lib/types/obstetric-summary";

function openModal() {
  fireEvent.click(screen.getByRole("button", { name: /ver evidencia/i }));
}

const oneSpan: EvidenceSpan[] = [
  { claim: "Edad 32 años", source_page: 1, source_text: "Edad:\n32 años" },
];

const twoSpans: EvidenceSpan[] = [
  { claim: "Hb 10.8", source_page: 1, source_text: "Hemoglobina 10.8 g/dL" },
  { claim: "TSH 2.1", source_page: 2, source_text: "TSH 2.1 mUI/L" },
];

describe("EvidenceModal", () => {
  it("renders trigger and shows the field name in the dialog title", () => {
    render(
      <EvidenceModal evidence={oneSpan} fieldName="Edad" pdfUrl="/sample.pdf" />,
    );
    openModal();
    expect(screen.getByText(/evidencia: edad/i)).toBeTruthy();
  });

  it("renders verbatim source_text and page number for a single span", () => {
    render(
      <EvidenceModal evidence={oneSpan} fieldName="Edad" pdfUrl="/sample.pdf" />,
    );
    openModal();
    // happy-dom normaliza whitespace al exponer textContent; verificamos por
    // contenido del <pre> directamente, que sí preserva el newline literal.
    const item = screen.getByTestId("evidence-item");
    const pre = item.querySelector("pre");
    expect(pre?.textContent).toBe("Edad:\n32 años");
    expect(screen.getByText(/p\. 1/)).toBeTruthy();
  });

  it("lists every span when several are provided", () => {
    render(
      <EvidenceModal evidence={twoSpans} fieldName="Laboratorios" pdfUrl="/x.pdf" />,
    );
    openModal();
    const items = screen.getAllByTestId("evidence-item");
    expect(items).toHaveLength(2);
  });

  it("shows fallback message when evidence is empty and disables the trigger", () => {
    render(
      <EvidenceModal evidence={[]} fieldName="Algo" pdfUrl="/x.pdf" />,
    );
    const trigger = screen.getByRole("button", { name: /ver evidencia/i }) as HTMLButtonElement;
    expect(trigger.disabled).toBe(true);
  });

  it('renders an "Open PDF" anchor with the correct #page=N anchor', () => {
    render(
      <EvidenceModal evidence={oneSpan} fieldName="Edad" pdfUrl="/sample.pdf" />,
    );
    openModal();
    const link = screen.getByTestId("open-pdf-link") as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe("/sample.pdf#page=1");
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("hides the PDF anchor when pdfUrl is null (uploaded PDFs in memory)", () => {
    render(
      <EvidenceModal evidence={oneSpan} fieldName="Edad" pdfUrl={null} />,
    );
    openModal();
    expect(screen.queryByTestId("open-pdf-link")).toBeNull();
    expect(screen.getByText(/PDF subido vive sólo en memoria/i)).toBeTruthy();
  });
});
