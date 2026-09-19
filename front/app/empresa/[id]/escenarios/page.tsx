import { notFound } from "next/navigation";
import { empresa, PALANCAS } from "@/lib/data";
import { cargarEmpresa, cargarRecomendaciones, simularPalanca } from "@/lib/motor";
import Simulador from "./simulador";

export default async function Escenarios({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [e, rec] = await Promise.all([
    cargarEmpresa(id),
    cargarRecomendaciones(id),
  ]);
  const finalEmpresa = e ?? empresa(id);
  if (!finalEmpresa) notFound();

  const simInicial = await simularPalanca(
    finalEmpresa.id,
    PALANCAS[0].id,
    PALANCAS[0].defecto,
    finalEmpresa
  );

  return (
    <Simulador
      empresa={finalEmpresa}
      recomendaciones={rec}
      simInicial={simInicial}
    />
  );
}
