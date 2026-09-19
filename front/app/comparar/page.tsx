import { cargarComparativa } from "@/lib/motor";
import SplitScreen from "./split";

export default async function Comparar({
  searchParams,
}: {
  searchParams?: Promise<{ sube?: string; baja?: string }>;
}) {
  const params = await searchParams;
  const comp = await cargarComparativa(params?.sube, params?.baja);
  return (
    <SplitScreen
      sube={comp.sube}
      baja={comp.baja}
      opcionesSube={comp.opcionesSube}
      opcionesBaja={comp.opcionesBaja}
    />
  );
}
