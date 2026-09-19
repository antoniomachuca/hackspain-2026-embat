import Link from "next/link";
import { notFound } from "next/navigation";
import { empresa, recomendar, MES_ACTUAL } from "@/lib/data";
import { eur, num, mesCorto, banda } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Trayectoria, Waterfall } from "@/components/charts";
import { Anillo } from "@/components/anillo";
import { Card, CardHead, KPI, ScoreBadge, BandaChip, EstadoChip, Confianza, Delta, Boton, Vacio } from "@/components/ui";

export default async function Ficha({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const e = empresa(id);
  if (!e) notFound();

  const sinDatos = e.mesesHistoria < 12;
  const b = banda(e.score);
  const recos = sinDatos ? [] : recomendar(e, 3);

  return (
    <>
      <Cabecera
        titulo={e.nombre}
        sub={<>{e.sector} · <Link href={`/grupo/${e.grupo}`} className="underline decoration-[var(--color-line-2)] underline-offset-2 hover:text-[var(--color-aqua)]">{e.grupoNombre}</Link> · {e.id}</>}
        extra={
          <div className="flex items-center gap-2">
            <Boton tono="plano" href={`/empresa/${e.id}/drivers`}>Ver drivers</Boton>
            <Boton href={`/empresa/${e.id}/escenarios`}>Simular mejoras</Boton>
          </div>
        }
      />

      {sinDatos ? (
        <div>
          <Vacio
            titulo="Datos insuficientes para publicar un score"
            texto={`${e.nombre} tiene ${e.mesesHistoria} meses de historia. El motor necesita 12 para separar la tendencia del ruido estacional. Mostramos las señales disponibles, pero no una puntuación que no se sostiene.`}
            accion={<Boton tono="plano" href="/">Volver a la cartera</Boton>}
          />
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KPI etiqueta="Días de caja" valor={`${e.diasCaja}`} nota="cobertura operativa" />
            <KPI etiqueta="DSO" valor={`${e.dso} días`} nota="días en cobrar" />
            <KPI etiqueta="DPO" valor={`${e.dpo} días`} nota="días en pagar" />
            <KPI etiqueta="Meses de historia" valor={`${e.mesesHistoria}`} nota="mínimo 12 para score" />
          </div>
        </div>
      ) : (
        <div>
          {e.alerta && (
            <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border px-4 py-3"
              style={{ borderColor: "rgba(229,159,94,.35)", background: "rgba(229,159,94,.10)", backdropFilter: "blur(16px)" }}>
              <span className="text-[12px] font-medium" style={{ color: "var(--color-risk-2)" }}>
                Detectado en {mesCorto(e.alerta.mesDeteccion)} · {e.alerta.mesesAnticipacion} meses de anticipación
              </span>
              <span className="text-[12px] text-[var(--color-ink-2)]">{e.alerta.texto}</span>
            </div>
          )}

          <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
            <Card className="px-5 py-6">
              <p className="text-center text-[12px] text-[var(--color-ink-3)]">Score de salud financiera</p>
              <div className="mt-3 flex justify-center">
                <Anillo score={e.score} delta={e.score - e.scorePrev} />
              </div>
              <div className="mt-4 flex items-center justify-center gap-2">
                <EstadoChip estado={e.estado} />
                <Confianza nivel={e.confianza} />
              </div>
              <div className="mt-5 space-y-2 border-t border-[var(--color-line)] pt-4 text-[12px]">
                <Fila k="Historia" v={`${e.mesesHistoria} meses`} />
                <Fila k="Facturación anual" v={eur(e.facturacionAnual, true)} />
                <Fila k="Percentil en su grupo" v={`P${e.drivers[0].p_peer}`} />
              </div>
            </Card>

            <Card>
              <CardHead titulo="Trayectoria" sub="24 meses · el nivel de hoy y hacia dónde va"
                extra={<span className="text-[11px] text-[var(--color-ink-4)]">{mesCorto(e.trayectoria[0].mes)} – {mesCorto(MES_ACTUAL)}</span>} />
              <div className="px-3 py-4">
                <Trayectoria datos={e.trayectoria} alerta={e.alerta?.mesDeteccion} />
              </div>
            </Card>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <KPI etiqueta="Días de caja" valor={`${e.diasCaja}`} nota="si no cobrase nada más" />
            <KPI etiqueta="DSO" valor={`${e.dso} d`} nota="días en cobrar" />
            <KPI etiqueta="DPO" valor={`${e.dpo} d`} nota="días en pagar" />
            <KPI etiqueta="Uso de línea" valor={`${e.utilizacionLinea}%`} nota="del límite concedido" />
            <KPI etiqueta="Concentración" valor={num(e.hhiClientes, 2)} nota="HHI de clientes" />
          </div>

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHead titulo="Por qué este número" sub="Las contribuciones suman exactamente el score"
                extra={<Link href={`/empresa/${e.id}/drivers`} className="text-[12px] text-[var(--color-aqua)] hover:underline">Detalle</Link>} />
              <div className="px-3 py-4"><Waterfall drivers={e.drivers} /></div>
            </Card>

            <Card>
              <CardHead titulo="Qué hacer" sub="Simulado contra el motor. Ninguna cifra viene de un modelo de lenguaje."
                extra={<Link href={`/empresa/${e.id}/escenarios`} className="text-[12px] text-[var(--color-aqua)] hover:underline">Simulador</Link>} />
              <ul className="divide-y divide-[var(--color-line)]">
                {recos.map((r) => (
                  <li key={r.palanca.id} className="px-5 py-3.5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[13px] font-medium">
                          {r.palanca.nombre} · <span className="tnum font-normal">{r.valor} {r.palanca.unidad}</span>
                        </p>
                        <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">{r.palanca.descripcion}</p>
                      </div>
                      <Delta v={r.deltaScore} sufijo=" pts" className="shrink-0 pt-0.5" />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-[var(--color-ink-2)]">
                      {r.cajaLiberada > 0 && <span className="tnum">Caja liberada <strong className="font-medium">{eur(r.cajaLiberada)}</strong></span>}
                      {r.eurAnio > 0 && <span className="tnum">Ahorro financiero <strong className="font-medium">{eur(r.eurAnio)}/año</strong></span>}
                      {r.anclada && <span className="text-[var(--color-ink-4)]">ataca tu driver más débil</span>}
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}

function Fila({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[var(--color-ink-3)]">{k}</span>
      <span className="tnum font-medium">{v}</span>
    </div>
  );
}
