import { notFound } from "next/navigation";
import { empresa } from "@/lib/data";
import Simulador from "./simulador";

export default async function Escenarios({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const e = empresa(id);
  if (!e) notFound();
  return <Simulador empresa={e} />;
}
