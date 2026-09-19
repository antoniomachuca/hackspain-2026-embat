import { notFound } from "next/navigation";
import { apiEmpresa } from "@/lib/api";
import { cargarGrupoDetalle } from "@/lib/motor";
import { VistaGrupo } from "@/components/vista-grupo";

/** "Mi grupo": una empresa mira el grupo al que pertenece, y solo ese. */
export default async function MiGrupo({ params }: { params: Promise<{ company_id: string }> }) {
  const { company_id } = await params;
  const e = await apiEmpresa(company_id);
  if (!e) notFound();
  const g = await cargarGrupoDetalle(e.group_id);
  if (!g || !g.miembros.length) notFound();
  return <VistaGrupo g={g} base="" />;
}
