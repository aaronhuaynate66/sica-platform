import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, GitCompare, Upload } from "lucide-react";

import { ControlTimeline } from "@/components/clinical/control/control-timeline";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { listControlesByPaciente } from "@/lib/queries/controles";
import { getPaciente } from "@/lib/queries/pacientes";
import { createClient } from "@/lib/supabase/server";
import { calculateAge, formatDateEs } from "@/lib/utils/dates";

interface PacientePageProps {
  params: Promise<{ id: string }>;
}

export default async function PacientePage({ params }: PacientePageProps) {
  const { id } = await params;
  const supabase = await createClient();

  const [paciente, controles] = await Promise.all([
    getPaciente(supabase, id),
    listControlesByPaciente(supabase, id),
  ]);

  if (!paciente) notFound();

  const edad = calculateAge(paciente.fecha_nacimiento);
  const ultimoControl = controles[controles.length - 1] ?? null;
  const egActual = ultimoControl?.semanas_gestacion ?? null;
  const problemasActuales = ultimoControl?.resumen_json.active_problems ?? [];

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <Link
        href="/app"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Pacientes
      </Link>

      {/* ---------- Header ---------- */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {paciente.nombre_completo}
          </h1>
          <p className="text-sm text-muted-foreground">
            {paciente.dni && <>DNI {paciente.dni} · </>}
            {edad != null && <>{edad} años · </>}
            {paciente.hc_id && <>HC {paciente.hc_id} · </>}
            Registrada el {formatDateEs(paciente.created_at)}
          </p>
        </div>
        <div className="flex gap-2">
          {controles.length >= 2 && (
            <Link
              href={`/app/pacientes/${paciente.id}/comparar?a=${controles[0].id}&b=${controles[controles.length - 1].id}`}
              className={buttonVariants({ variant: "outline" })}
            >
              <GitCompare className="mr-2 size-4" />
              Comparar
            </Link>
          )}
          <Link
            href={`/app/upload?paciente_id=${paciente.id}`}
            className={buttonVariants()}
          >
            <Upload className="mr-2 size-4" />
            Subir control
          </Link>
        </div>
      </div>

      {/* ---------- Stats globales ---------- */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Controles
            </p>
            <p className="mt-1 text-2xl font-semibold">{controles.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              EG actual
            </p>
            <p className="mt-1 text-2xl font-semibold">
              {egActual != null ? (
                <>
                  {egActual.toFixed(1)}
                  <span className="ml-1 text-sm font-normal text-muted-foreground">
                    sem
                  </span>
                </>
              ) : (
                "—"
              )}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Último control
            </p>
            <p className="mt-1 text-sm font-medium">
              {formatDateEs(ultimoControl?.fecha_control ?? null)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Problemas activos
            </p>
            <p className="mt-1 text-2xl font-semibold">{problemasActuales.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* ---------- Problemas activos resumen ---------- */}
      {problemasActuales.length > 0 && (
        <Card className="mb-6">
          <CardContent className="p-5">
            <p className="mb-3 text-sm font-medium">
              Problemas activos (último control)
            </p>
            <div className="flex flex-wrap gap-2">
              {problemasActuales.map((p, i) => (
                <Badge key={i} variant="secondary" className="font-normal">
                  {p}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---------- Timeline ---------- */}
      <div>
        <h2 className="mb-4 text-lg font-medium">Línea de tiempo</h2>
        <ControlTimeline pacienteId={paciente.id} controles={controles} />
      </div>
    </div>
  );
}
