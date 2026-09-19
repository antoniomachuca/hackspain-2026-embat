import { EMPRESAS_CON_SCORE } from "@/lib/data";
import SplitScreen from "./split";

export default function Comparar() {
  // Northbrook y Velasco no existen en los CSV: se eligen dos empresas reales
  // por su trayectoria — una que se recupera y otra que se tuerce.
  const sube = EMPRESAS_CON_SCORE.find((e) => e.estado === "MEJORANDO" || e.estado === "RECUPERACION")!;
  const baja = EMPRESAS_CON_SCORE.find((e) => e.estado === "DETERIORO" || e.estado === "TORCIENDOSE")!;
  return <SplitScreen sube={sube} baja={baja} />;
}
