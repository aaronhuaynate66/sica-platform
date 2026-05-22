import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EditableField } from "../editable-field";

describe("EditableField", () => {
  it("renders the value in read mode by default", () => {
    render(
      <EditableField label="Edad" value={32} editType="number" onSave={vi.fn()} />,
    );
    expect(screen.getByTestId("editable-value").textContent).toContain("32");
    expect(screen.queryByTestId("editable-input")).toBeNull();
  });

  it("enters edit mode when pencil is clicked", () => {
    render(
      <EditableField label="Edad" value={32} editType="number" onSave={vi.fn()} />,
    );
    fireEvent.click(screen.getByTestId("edit-trigger"));
    expect(screen.getByTestId("editable-input")).toBeTruthy();
  });

  it("calls onSave with the parsed numeric value", () => {
    const onSave = vi.fn();
    render(
      <EditableField label="Edad" value={32} editType="number" onSave={onSave} />,
    );
    fireEvent.click(screen.getByTestId("edit-trigger"));
    const input = screen.getByTestId("editable-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "45" } });
    fireEvent.click(screen.getByTestId("save-trigger"));
    expect(onSave).toHaveBeenCalledWith(45);
  });

  it("calls onSave with string for text fields", () => {
    const onSave = vi.fn();
    render(
      <EditableField label="Problema" value="Anemia" editType="text" onSave={onSave} />,
    );
    fireEvent.click(screen.getByTestId("edit-trigger"));
    const input = screen.getByTestId("editable-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Anemia severa" } });
    fireEvent.click(screen.getByTestId("save-trigger"));
    expect(onSave).toHaveBeenCalledWith("Anemia severa");
  });

  it("cancel exits edit mode without calling onSave", () => {
    const onSave = vi.fn();
    render(
      <EditableField label="Edad" value={32} editType="number" onSave={onSave} />,
    );
    fireEvent.click(screen.getByTestId("edit-trigger"));
    const input = screen.getByTestId("editable-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "999" } });
    fireEvent.click(screen.getByTestId("cancel-trigger"));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.queryByTestId("editable-input")).toBeNull();
  });

  it("shows 'Editado' badge when isEdited=true", () => {
    render(
      <EditableField
        label="Edad"
        value={45}
        editType="number"
        isEdited
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByTestId("edited-badge")).toBeTruthy();
  });

  it("renders reset button only when onReset provided AND isEdited=true", () => {
    const onReset = vi.fn();
    const { rerender } = render(
      <EditableField
        label="Edad"
        value={45}
        editType="number"
        isEdited
        onReset={onReset}
        onSave={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("reset-trigger"));
    expect(onReset).toHaveBeenCalled();

    rerender(
      <EditableField
        label="Edad"
        value={32}
        editType="number"
        isEdited={false}
        onReset={onReset}
        onSave={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("reset-trigger")).toBeNull();
  });

  it("Enter key saves a text field", () => {
    const onSave = vi.fn();
    render(
      <EditableField label="Problema" value="X" editType="text" onSave={onSave} />,
    );
    fireEvent.click(screen.getByTestId("edit-trigger"));
    const input = screen.getByTestId("editable-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Y" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSave).toHaveBeenCalledWith("Y");
  });

  it("Escape key cancels", () => {
    const onSave = vi.fn();
    render(
      <EditableField label="Edad" value={32} editType="number" onSave={onSave} />,
    );
    fireEvent.click(screen.getByTestId("edit-trigger"));
    const input = screen.getByTestId("editable-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "999" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.queryByTestId("editable-input")).toBeNull();
  });
});
