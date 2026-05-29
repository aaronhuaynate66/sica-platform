import Link from "next/link";
import { FileText, Plus, Upload } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listPacientesWithStats } from "@/lib/queries/pacientes";
import { createClient } from "@/lib/supabase/server";
import { formatDateEs } from "@/lib/utils/dates";

export default async function PacientesPage() {
  const supabase = await createClient();
  const pacientes = await listPacientesWithStats(supabase);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Pacientes</h1>
          <p className="text-sm text-muted-foreground">
            Gestantes registradas por ti. Cada PDF subido se asocia a un paciente.
          </p>
        </div>
        <Link href="/app/upload" className={buttonVariants()}>
          <Upload className="mr-2 size-4" />
          Subir control
        </Link>
      </div>

      {pacientes.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>DNI</TableHead>
                <TableHead className="text-right">Controles</TableHead>
                <TableHead>Último control</TableHead>
                <TableHead>EG actual</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pacientes.map((p) => (
                <TableRow key={p.id} className="cursor-pointer">
                  <TableCell className="font-medium">
                    <Link
                      href={`/app/pacientes/${p.id}`}
                      className="hover:underline"
                    >
                      {p.nombre_completo}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {p.dni ?? "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge variant="secondary">{p.total_controles}</Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateEs(p.ultimo_control_fecha)}
                  </TableCell>
                  <TableCell>
                    {p.semanas_gestacion_actual != null ? (
                      <Badge variant="outline">
                        {p.semanas_gestacion_actual.toFixed(1)} sem
                      </Badge>
                    ) : (
                      <span className="text-sm text-muted-foreground">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card/40 p-12 text-center">
      <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-full bg-muted">
        <FileText className="size-6 text-muted-foreground" />
      </div>
      <h2 className="mb-1 font-medium">Aún no hay pacientes</h2>
      <p className="mx-auto mb-6 max-w-md text-sm text-muted-foreground">
        Comienza subiendo el PDF de un control prenatal. Cada paciente se crea
        automáticamente la primera vez que registras un control suyo.
      </p>
      <Link href="/app/upload" className={buttonVariants()}>
        <Plus className="mr-2 size-4" />
        Subir primer control
      </Link>
    </div>
  );
}
