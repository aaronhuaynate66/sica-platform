"use client";

import { Check, Pencil, RotateCcw, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type EditType = "text" | "number" | "textarea";

interface EditableFieldProps {
  /** Valor mostrado / inicial del input. */
  value: string | number;
  /** Tipo de input. Default "text". */
  editType?: EditType;
  /** Etiqueta accesible (sr-only) para screen readers. */
  label: string;
  /** Llamado al hacer click en "Guardar" con el valor parseado. */
  onSave: (newValue: string | number) => void;
  /** Si onReset existe + isEdited=true, se renderiza el botón revertir. */
  onReset?: () => void;
  /** True si este campo está actualmente editado vs original. */
  isEdited?: boolean;
  /** Render del valor en modo lectura — default formatea según editType. */
  renderValue?: (value: string | number) => React.ReactNode;
  /** Clase opcional para el contenedor. */
  className?: string;
}

export function EditableField({
  value,
  editType = "text",
  label,
  onSave,
  onReset,
  isEdited = false,
  renderValue,
  className,
}: EditableFieldProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<string>(String(value ?? ""));
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const inputId = useId();

  // Cuando entra a modo edición, sincroniza el draft con el valor actual.
  useEffect(() => {
    if (isEditing) {
      setDraft(String(value ?? ""));
    }
  }, [isEditing, value]);

  // Auto-focus al abrir editor.
  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      if (inputRef.current instanceof HTMLTextAreaElement) {
        inputRef.current.setSelectionRange(draft.length, draft.length);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing]);

  function handleSave() {
    if (editType === "number") {
      const parsed = Number(draft);
      if (Number.isNaN(parsed)) {
        // No-op si no es número válido. La UI muestra el draft sin guardar.
        return;
      }
      onSave(parsed);
    } else {
      onSave(draft);
    }
    setIsEditing(false);
  }

  function handleCancel() {
    setDraft(String(value ?? ""));
    setIsEditing(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && editType !== "textarea") {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Enter" && editType === "textarea" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      e.preventDefault();
      handleCancel();
    }
  }

  const valueNode = renderValue ? renderValue(value) : <span>{value}</span>;

  if (!isEditing) {
    return (
      <span className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
        <span data-testid="editable-value">{valueNode}</span>
        {isEdited ? (
          <Badge
            variant="outline"
            className="border-warn-yellow/50 text-warn-yellow font-normal text-[10px]"
            data-testid="edited-badge"
          >
            editado
          </Badge>
        ) : null}
        <Button
          variant="ghost"
          size="icon-xs"
          aria-label={`Editar ${label}`}
          onClick={() => setIsEditing(true)}
          data-testid="edit-trigger"
        >
          <Pencil />
        </Button>
        {isEdited && onReset ? (
          <Button
            variant="ghost"
            size="icon-xs"
            aria-label={`Revertir ${label}`}
            onClick={onReset}
            data-testid="reset-trigger"
            title="Volver al valor original"
          >
            <RotateCcw />
          </Button>
        ) : null}
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
      <label htmlFor={inputId} className="sr-only">
        {label}
      </label>
      {editType === "textarea" ? (
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          id={inputId}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          rows={4}
          className="w-full min-w-[20rem] rounded-md border border-border bg-background px-2 py-1.5 text-sm"
          data-testid="editable-input"
        />
      ) : (
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          id={inputId}
          type={editType === "number" ? "number" : "text"}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          className="rounded-md border border-border bg-background px-2 py-1 text-sm font-mono tabular-nums w-24"
          data-testid="editable-input"
        />
      )}
      <Button
        variant="ghost"
        size="icon-xs"
        aria-label="Guardar"
        onClick={handleSave}
        data-testid="save-trigger"
      >
        <Check />
      </Button>
      <Button
        variant="ghost"
        size="icon-xs"
        aria-label="Cancelar"
        onClick={handleCancel}
        data-testid="cancel-trigger"
      >
        <X />
      </Button>
    </span>
  );
}
