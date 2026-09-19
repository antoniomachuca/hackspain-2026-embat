import { notFound } from "next/navigation";
import { cargarGrupoDetalle } from "@/lib/motor";
import { VistaGrupo } from "@/components/vista-grupo";

/** Un grupo de la cartera, leído desde Embat. */
export default async function Grupo({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const g = await cargarGrupoDetalle(id);
  if (!g || !g.miembros.length) notFound();
  return <VistaGrupo g={g} base="/embat" />;
}
