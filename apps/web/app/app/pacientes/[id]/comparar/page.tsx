import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { ControlDiff } from "@/components/clinical/control/control-diff";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { listControlesByPaciente } from "@/lib/queries/controles";
import { getPaciente } from "@/lib/queries/pacientes";
import { createClient } from "@/lib/supabase/server";
import { formatDateEs } from "@/lib/utils/dates";

interface ComparePageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ a?: string; b?: string }>;
}

export default async function ComparePage({
  params,
  searchParams,
}: ComparePageProps) {
  const { id } = await params;
  const { a, b } = await searchParams;
  const supabase = await createClient();

  const [paciente, controles] = await Promise.all([
    getPaciente(supabase, id),
    listControlesByPaciente(supabase, id),
  ]);

  if (!paciente) notFound();

  if (controles.length < 2) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8">
        <Link
          href={`/app/pacientes/${id}`}
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          {paciente.nombre_completo}
        </Link>
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-sm text-muted-foreground">
              Necesitas al menos 2 controles del mismo paciente para comparar.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const controlA = a ? controles.find((c) => c.id === a) : controles[0];
  const controlB = b ? controles.find((c) => c.id === b) : controles[controles.length - 1];

  if (!controlA || !controlB) {
    redirect(`/app/pacientes/${id}/comparar?a=${controles[0].id}&b=${controles[controles.length - 1].id}`);
  }

  if (controlA.id === controlB.id) {
    redirect(`/app/pacientes/${id}`);
  }

  // A debe ser el más antiguo cronológicamente para una lectura natural izquierda→derecha
  const [first, second] =
    new Date(controlA.fecha_control ?? controlA.created_at).getTime() <=
    new Date(controlB.fecha_control ?? controlB.created_at).getTime()
      ? [controlA, controlB]
      : [controlB, controlA];

  const labelA = formatDateEs(first.fecha_control);
  const labelB = formatDateEs(second.fecha_control);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <Link
        href={`/app/pacientes/${id}`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        {paciente.nombre_completo}
      </Link>

      <h1 className="mb-4 text-2xl font-semibold tracking-tight">
        Comparación entre controles
      </h1>

      {/* ---------- Selector visual ---------- */}
      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card className="border-clinical-blue/30">
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Control A — antes
            </p>
            <p className="mt-1 font-medium">{labelA}</p>
            {first.semanas_gestacion != null && (
              <Badge variant="outline" className="mt-2">
                {first.semanas_gestacion.toFixed(1)} sem
              </Badge>
            )}
          </CardContent>
        </Card>
        <Card className="border-clinical-blue/30">
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Control B — después
            </p>
            <p className="mt-1 font-medium">{labelB}</p>
            {second.semanas_gestacion != null && (
              <Badge variant="outline" className="mt-2">
                {second.semanas_gestacion.toFixed(1)} sem
              </Badge>
            )}
          </CardContent>
        </Card>
      </div>

      <ControlDiff
        a={first.resumen_json}
        b={second.resumen_json}
        labelA={labelA}
        labelB={labelB}
      />

      {/* ---------- Cambiar selección ---------- */}
      {controles.length > 2 && (
        <Card className="mt-6">
          <CardContent className="p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
              Seleccionar otros controles
            </p>
            <div className="flex flex-wrap gap-2">
              {controles.map((c) => {
                const isA = c.id === first.id;
                const isB = c.id === second.id;
                return (
                  <Link
                    key={c.id}
                    href={`/app/pacientes/${id}/comparar?a=${isA ? second.id : first.id}&b=${c.id}`}
                    className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                      isA || isB
                        ? "border-clinical-blue/40 bg-clinical-blue/10"
                        : "border-border hover:border-clinical-blue/40 hover:bg-muted/40"
                    }`}
                  >
                    {formatDateEs(c.fecha_control)}
                    {c.semanas_gestacion != null
                      ? ` · ${c.semanas_gestacion.toFixed(1)} sem`
                      : ""}
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
