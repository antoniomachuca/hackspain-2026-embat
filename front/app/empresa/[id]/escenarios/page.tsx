import { notFound } from "next/navigation";
import { empresa } from "@/lib/data";
import { cargarEmpresa } from "@/lib/motor";
import Simulador from "./simulador";

export default async function Escenarios({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const e = (await cargarEmpresa(id)) ?? empresa(id);
  if (!e) notFound();
  return <Simulador empresa={e} />;
}
