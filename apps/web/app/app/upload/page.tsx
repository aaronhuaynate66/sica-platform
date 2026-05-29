import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { UploadForm } from "@/components/app/upload-form";
import { listPacientesWithStats } from "@/lib/queries/pacientes";
import { createClient } from "@/lib/supabase/server";

interface UploadPageProps {
  searchParams: Promise<{ paciente_id?: string }>;
}

export default async function UploadPage({ searchParams }: UploadPageProps) {
  const supabase = await createClient();
  const pacientes = await listPacientesWithStats(supabase);
  const params = await searchParams;

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <Link
        href="/app"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Volver a pacientes
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Subir control</h1>
        <p className="text-sm text-muted-foreground">
          Sube el PDF del control prenatal. SICA extrae automáticamente el
          resumen obstétrico y lo asocia al paciente.
        </p>
      </div>

      <UploadForm
        pacientes={pacientes.map((p) => ({
          id: p.id,
          nombre_completo: p.nombre_completo,
          dni: p.dni,
        }))}
        defaultPacienteId={params.paciente_id}
      />
    </div>
  );
}
