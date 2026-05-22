"use client";

import { Eye, Pencil, Trash2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { applyMaskingProps } from "@/lib/analytics/masking";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { FieldEdit } from "@/lib/hooks/use-editable-summary";

interface EditsIndicatorProps {
  edits: FieldEdit[];
  onResetAll: () => void;
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v.length === 0 ? "(vacío)" : v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

function readablePath(path: string): string {
  // Convierte "active_problems.0" → "Problema activo #1"
  // "patient_age" → "Edad"
  // "notes_summary" → "Resumen"
  if (path === "patient_age") return "Edad";
  if (path === "notes_summary") return "Resumen y plan";
  if (path.startsWith("active_problems.")) {
    const idx = Number(path.split(".")[1]);
    return `Problema activo #${idx + 1}`;
  }
  return path;
}

export function EditsIndicator({ edits, onResetAll }: EditsIndicatorProps) {
  if (edits.length === 0) return null;

  return (
    <div className="flex items-center gap-1.5">
      <Dialog>
        <DialogTrigger
          render={
            <Button
              variant="outline"
              size="xs"
              className="gap-1 border-warn-yellow/50 text-warn-yellow"
            >
              <Pencil className="size-3" />
              {edits.length} campo{edits.length === 1 ? "" : "s"} editado
              {edits.length === 1 ? "" : "s"}
            </Button>
          }
        />
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="size-4 text-clinical-blue" />
              Ver cambios ({edits.length})
            </DialogTitle>
            <DialogDescription>
              Estas ediciones viven sólo en memoria de la sesión. Persistencia y
              feedback formal llegan con el orquestador (R1+).
            </DialogDescription>
          </DialogHeader>

          <ul className="space-y-2 max-h-[60vh] overflow-y-auto">
            {edits.map((edit) => (
              <li
                key={edit.path}
                className="rounded-md border border-border bg-muted/30 p-3 text-xs"
                data-testid="edit-row"
              >
                <div className="font-medium text-foreground mb-1.5">
                  {readablePath(edit.path)}{" "}
                  <Badge variant="outline" className="ml-1 font-mono text-[10px]">
                    {edit.path}
                  </Badge>
                </div>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                  <dt className="text-muted-foreground">Original</dt>
                  <dd
                    {...applyMaskingProps()}
                    className="font-mono text-muted-foreground line-through"
                  >
                    {formatValue(edit.original)}
                  </dd>
                  <dt className="text-muted-foreground">Nuevo</dt>
                  <dd {...applyMaskingProps()} className="font-mono text-foreground">
                    {formatValue(edit.current)}
                  </dd>
                </dl>
              </li>
            ))}
          </ul>

          <DialogFooter>
            <DialogClose
              render={
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={onResetAll}
                  data-testid="discard-all"
                />
              }
            >
              <Trash2 className="size-3" />
              Descartar todo
            </DialogClose>
            <DialogClose render={<Button variant="outline" size="sm" />}>
              <X className="size-3" />
              Cerrar
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
