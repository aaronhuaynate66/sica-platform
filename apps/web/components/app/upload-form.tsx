"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";

import { processPdfAction } from "@/app/app/upload/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface UploadFormProps {
  pacientes: Array<{ id: string; nombre_completo: string; dni: string | null }>;
  defaultPacienteId?: string;
}

type Stage =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "extracting" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

const NEW_PACIENTE_VALUE = "__new__";

export function UploadForm({ pacientes, defaultPacienteId }: UploadFormProps) {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);

  const [mode, setMode] = useState<"existing" | "new">(
    pacientes.length === 0 ? "new" : "existing"
  );
  const [pacienteSel, setPacienteSel] = useState<string>(
    defaultPacienteId ?? (pacientes[0]?.id ?? NEW_PACIENTE_VALUE)
  );
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>({ kind: "idle" });

  const busy = stage.kind === "uploading" || stage.kind === "extracting" || stage.kind === "saving";

  function handlePacienteChange(value: string | null) {
    if (!value || value === NEW_PACIENTE_VALUE) {
      setMode("new");
      setPacienteSel(NEW_PACIENTE_VALUE);
    } else {
      setMode("existing");
      setPacienteSel(value);
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) {
      setStage({ kind: "error", message: "Debes seleccionar un PDF" });
      return;
    }

    const formData = new FormData(e.currentTarget);
    formData.set("file", file);
    formData.set("mode", mode);
    if (mode === "existing") {
      formData.set("paciente_id", pacienteSel);
    } else {
      formData.delete("paciente_id");
    }

    // Stage 1: subiendo a Storage (server action lo hace internamente, pero
    // el feedback visual va escalando con setTimeouts para que el usuario
    // perciba progreso real durante los ~30-50s de extracción).
    setStage({ kind: "uploading" });
    const extractTimer = window.setTimeout(
      () => setStage({ kind: "extracting" }),
      2500
    );
    const savingTimer = window.setTimeout(
      () => setStage({ kind: "saving" }),
      55_000
    );

    try {
      const result = await processPdfAction(formData);

      window.clearTimeout(extractTimer);
      window.clearTimeout(savingTimer);

      if (!result.ok) {
        setStage({ kind: "error", message: result.error ?? "Error desconocido" });
        return;
      }

      // Éxito → router push (no usar redirect del server action porque queremos
      // limpiar el estado del cliente y dejar feedback de "guardando…")
      setStage({ kind: "saving" });
      router.push(`/app/pacientes/${result.pacienteId}/controles/${result.controlId}`);
      router.refresh();
    } catch (err) {
      window.clearTimeout(extractTimer);
      window.clearTimeout(savingTimer);
      setStage({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <form ref={formRef} onSubmit={handleSubmit} className="space-y-5">
          {/* ---------- Selector de paciente ---------- */}
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="paciente">
              Paciente
            </label>
            <Select
              value={pacienteSel}
              onValueChange={handlePacienteChange}
              disabled={busy}
            >
              <SelectTrigger id="paciente" className="w-full">
                <SelectValue placeholder="Selecciona o crea un paciente" />
              </SelectTrigger>
              <SelectContent>
                {pacientes.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.nombre_completo}
                    {p.dni ? ` · DNI ${p.dni}` : ""}
                  </SelectItem>
                ))}
                <SelectItem value={NEW_PACIENTE_VALUE}>
                  + Nuevo paciente…
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* ---------- Form nuevo paciente ---------- */}
          {mode === "new" && (
            <div className="space-y-3 rounded-md border border-border bg-muted/30 p-4">
              <p className="text-xs font-medium uppercase text-muted-foreground">
                Datos del nuevo paciente
              </p>
              <div className="space-y-2">
                <label htmlFor="nombre_completo" className="text-sm">
                  Nombre completo *
                </label>
                <Input
                  id="nombre_completo"
                  name="nombre_completo"
                  required={mode === "new"}
                  placeholder="Lucía Quispe Mamani"
                  disabled={busy}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label htmlFor="dni" className="text-sm">
                    DNI
                  </label>
                  <Input
                    id="dni"
                    name="dni"
                    inputMode="numeric"
                    maxLength={8}
                    placeholder="12345678"
                    disabled={busy}
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="fecha_nacimiento" className="text-sm">
                    Fecha de nacimiento
                  </label>
                  <Input
                    id="fecha_nacimiento"
                    name="fecha_nacimiento"
                    type="date"
                    disabled={busy}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ---------- File input ---------- */}
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="file">
              PDF del control prenatal *
            </label>
            <label
              htmlFor="file"
              className={cn(
                "flex cursor-pointer items-center gap-3 rounded-md border border-dashed border-border bg-muted/30 px-4 py-6 text-sm transition-colors hover:bg-muted/50",
                busy && "pointer-events-none opacity-60"
              )}
            >
              <FileUp className="size-5 text-muted-foreground" />
              <div className="flex-1">
                {file ? (
                  <>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </>
                ) : (
                  <>
                    <p>Click para seleccionar PDF</p>
                    <p className="text-xs text-muted-foreground">
                      O arrastra el archivo aquí
                    </p>
                  </>
                )}
              </div>
            </label>
            <input
              id="file"
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={busy}
            />
          </div>

          {/* ---------- Status / errors ---------- */}
          {stage.kind === "error" && (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {stage.message}
            </p>
          )}

          {/* ---------- Submit ---------- */}
          <Button type="submit" disabled={busy || !file} className="w-full">
            {busy ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                {stage.kind === "uploading" && "Subiendo PDF…"}
                {stage.kind === "extracting" && "Procesando con IA (puede tardar 30-50s)…"}
                {stage.kind === "saving" && "Guardando resultado…"}
              </>
            ) : (
              "Procesar control"
            )}
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            El resumen extraído es asistivo. Debes revisarlo antes de cualquier
            uso clínico.
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
