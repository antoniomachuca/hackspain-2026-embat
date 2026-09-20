/**
 * Asistente de una empresa: se pregunta a sí misma. Solo ve sus datos y los
 * de su grupo; el límite lo impone el route handler, no esta página.
 */
import { notFound } from "next/navigation";
import { apiEmpresa } from "@/lib/api";
import { nombreDe } from "@/lib/motor";
import { mesCorto } from "@/lib/format";
import { normalizarId } from "@/components/ficha-empresa";
import { Cabecera } from "@/components/shell";
import { Chat } from "@/components/agente/chat";

export const metadata = { title: "Asistente · X Ray" };

export default async function AsistenteEmpresa({ params }: { params: Promise<{ company_id: string }> }) {
  const { company_id } = await params;
  const id = normalizarId(company_id);
  if (!id) notFound();
  const e = await apiEmpresa(id);
  if (!e) notFound();

  return (
    <div className="flex min-h-[calc(100vh-80px)] flex-col sm:h-[calc(100vh-40px)] sm:min-h-0">
      <Cabecera
        titulo="Tu asistente"
        sub={<>{nombreDe(e.company_id)} · Grupo {e.group_id.replace("GROUP_", "")} · corte {mesCorto(e.as_of.slice(0, 7))} · responde solo sobre tu empresa y tu grupo</>}
      />
      <Chat empresa={e.company_id} modo="empresa" />
    </div>
  );
}
