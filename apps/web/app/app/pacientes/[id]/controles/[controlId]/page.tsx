import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, GitCompare } from "lucide-react";

import { ControlSummary } from "@/components/clinical/control/control-summary";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  getControl,
  listControlesByPaciente,
} from "@/lib/queries/controles";
import { getPaciente } from "@/lib/queries/pacientes";
import { createClient } from "@/lib/supabase/server";
import { formatDateEs, formatDateTimeEs } from "@/lib/utils/dates";

interface ControlPageProps {
  params: Promise<{ id: string; controlId: string }>;
}

export default async function ControlPage({ params }: ControlPageProps) {
  const { id, controlId } = await params;
  const supabase = await createClient();

  const [paciente, control, allControles] = await Promise.all([
    getPaciente(supabase, id),
    getControl(supabase, controlId),
    listControlesByPaciente(supabase, id),
  ]);

  if (!paciente || !control) notFound();

  // Signed URL del PDF para el botón "Ver PDF". Caduca en 5 min.
  let pdfSignedUrl: string | null = null;
  if (control.pdf_storage_path) {
    const { data } = await supabase.storage
      .from("pdfs")
      .createSignedUrl(control.pdf_storage_path, 300);
    pdfSignedUrl = data?.signedUrl ?? null;
  }

  // Sugerencia de comparación: control anterior si existe
  const idx = allControles.findIndex((c) => c.id === controlId);
  const previous = idx > 0 ? allControles[idx - 1] : null;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <Link
        href={`/app/pacientes/${paciente.id}`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        {paciente.nombre_completo}
      </Link>

      {/* ---------- Header del control ---------- */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Control del {formatDateEs(control.fecha_control)}
          </h1>
          <p className="text-sm text-muted-foreground">
            {control.semanas_gestacion != null && (
              <>EG {control.semanas_gestacion.toFixed(1)} sem · </>
            )}
            Procesado el {formatDateTimeEs(control.created_at)}
          </p>
        </div>
        <div className="flex gap-2">
          {previous && (
            <Link
              href={`/app/pacientes/${paciente.id}/comparar?a=${previous.id}&b=${control.id}`}
              className={buttonVariants({ variant: "outline" })}
            >
              <GitCompare className="mr-2 size-4" />
              Comparar con anterior
            </Link>
          )}
          {pdfSignedUrl && (
            <a
              href={pdfSignedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonVariants({ variant: "outline" })}
            >
              <ExternalLink className="mr-2 size-4" />
              Ver PDF original
            </a>
          )}
        </div>
      </div>

      <ControlSummary summary={control.resumen_json} />

      {/* ---------- Metadata operacional ---------- */}
      <Card className="mt-4">
        <CardContent className="p-5">
          <h3 className="mb-3 text-sm font-medium">Metadata técnico</h3>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs sm:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">Confianza</dt>
              <dd className="mt-0.5 font-mono">
                {control.confidence_score != null
                  ? `${(control.confidence_score * 100).toFixed(0)}%`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Latencia</dt>
              <dd className="mt-0.5 font-mono">
                {control.latency_ms != null
                  ? `${(control.latency_ms / 1000).toFixed(1)}s`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Provider</dt>
              <dd className="mt-0.5">
                {control.provider_id ? (
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {control.provider_id}
                  </Badge>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Trace ID</dt>
              <dd
                className="mt-0.5 truncate font-mono text-[10px]"
                title={control.trace_id ?? undefined}
              >
                {control.trace_id ? control.trace_id.slice(0, 12) + "…" : "—"}
              </dd>
            </div>
          </dl>
          <p className="mt-3 text-[10px] text-muted-foreground">
            Archivo: {control.pdf_filename}
          </p>
        </CardContent>
      </Card>

      <p className="mt-6 text-center text-xs text-muted-foreground">
        Este resumen es asistivo. SICA no reemplaza el juicio clínico — revisa
        y confirma antes de cualquier decisión.
      </p>
    </div>
  );
}
