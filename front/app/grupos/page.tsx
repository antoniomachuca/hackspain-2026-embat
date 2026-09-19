import { cargarCarteraGrupos, type MotivoGrupo } from "@/lib/motor";
import type { Motivo as MotivoDef } from "@/components/bandeja-grupos";
import { eur, num } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Card, KPI, Vacio } from "@/components/ui";
import { Dispersion, AnilloReparto } from "@/components/cartera-grupos";
import { Bandeja } from "@/components/bandeja-grupos";

/**
 * Los grupos, leídos desde Embat. No es un catálogo de 250 fichas: es lo que un
 * score por empresa no puede ver —que una filial arrastre al grupo entero—
 * repartido en motivos. Lo que no tiene nada que contar se queda en una línea.
 */
const MOTIVOS: MotivoDef[] = [
  { clave: "CONTAGIO", label: "Contagio", color: "#e5775b", bg: "rgba(229,119,91,.14)",
    accion: "Una filial por debajo de 40 tira del consolidado. Aquí se retiene." },
  { clave: "DETERIORO", label: "Deterioro", color: "#e59f5e", bg: "rgba(229,159,94,.14)",
    accion: "No es una sociedad suelta: el problema se repite en varias." },
  { clave: "DISPERSION", label: "Dispersión", color: "#dfb631", bg: "rgba(223,182,49,.14)",
    accion: "La media del grupo esconde el recorrido entre sus filiales." },
  { clave: "OPORTUNIDAD", label: "Crecer", color: "#80efa2", bg: "rgba(128,239,162,.14)",
    accion: "Sanos y sin riesgo: candidatos a producto." },
];

export default async function Grupos() {
  const grupos = await cargarCarteraGrupos();

  if (!grupos.length) {
    return (
      <>
        <Cabecera titulo="Grupos Embat" sub="Cartera consolidada" />
        <Vacio titulo="El motor no responde"
          texto="Arranca el backend (uvicorn backend.main:app) para ver los grupos. Esta vista lee de xray.duckdb." />
      </>
    );
  }

  const por = (m: MotivoGrupo) =>
    grupos.filter((g) => g.motivo === m).sort((a, b) => b.gravedad - a.gravedad);

  const sinSenal = por("SIN_SENAL");
  const piden = grupos.length - sinSenal.length;
  const enRiesgo = grupos.reduce((s, g) => s + g.enRiesgo, 0);
  const filiales = grupos.reduce((s, g) => s + g.filiales, 0);
  const consolidadoMedio = grupos.reduce((s, g) => s + g.consolidado, 0) / grupos.length;
  const flujoTotal = grupos.reduce((s, g) => s + g.flujoInterno, 0);
  const contagio = por("CONTAGIO");
  const puntosEnJuego = contagio.reduce((s, g) => s + g.penalizacion, 0);

  const enganan = grupos.filter((g) => g.media - g.peor.score > 25).length;

  return (
    <div className="flex h-[calc(100dvh-40px)] flex-col">
      <Cabecera
        titulo="Grupos Embat"
        sub={
          <>
            {num(grupos.length, 0)} grupos · {num(filiales, 0)} sociedades ·{" "}
            <span className="tnum text-[var(--color-ink-4)]">motor conectado</span>
          </>
        }
      />

      {/* ── Los cuatro números ─────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPI etiqueta="Grupos que piden acción" valor={num(piden, 0)} nota={`de ${grupos.length} · el resto, sin señal`} />
        <KPI etiqueta="Puntos en juego" valor={num(puntosEnJuego)} nota={`de consolidado, en ${contagio.length} grupos con contagio`} />
        <KPI etiqueta="Sociedades en riesgo" valor={num(enRiesgo, 0)} nota={`de ${num(filiales, 0)} en toda la cartera`} />
        <KPI etiqueta="Flujo intragrupo" valor={eur(flujoTotal, true)} nota="dinero que se mueve dentro de los grupos" />
      </div>

      {/* ── Cómo está repartida y qué esconde ──────────────────────── */}
      <div className="mt-4 grid flex-none auto-rows-fr gap-4 lg:grid-cols-2">
        <Card className="flex flex-col justify-center px-5 py-4">
          <h2 className="text-[15px] font-semibold tracking-tight">Cómo se reparte el consolidado</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            {grupos.length} grupos por banda · media {num(consolidadoMedio)}
          </p>
          <div className="mt-4"><AnilloReparto grupos={grupos} /></div>
        </Card>

        <Card className="flex flex-col justify-center px-5 py-4">
          <h2 className="text-[15px] font-semibold tracking-tight">Lo que la media esconde</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            Cada punto es un grupo · en{" "}
            <strong className="tnum font-medium text-[var(--color-ink-2)]">{enganan}</strong> de ellos la peor
            filial está más de 25 puntos por debajo de la media
          </p>
          <div className="mt-4"><Dispersion grupos={grupos} /></div>
        </Card>
      </div>

      {/* ── Qué hacer ──────────────────────────────────────────────── */}
      <div className="mt-4 flex min-h-0 flex-1 flex-col"><Bandeja motivos={MOTIVOS} grupos={grupos} /></div>
    </div>
  );
}
