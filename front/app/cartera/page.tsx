import Link from 'next/link'
import { Cuadrante } from '@/components/Cuadrante'
import { EstadoEtiqueta } from '@/components/Score'
import { Trayectoria } from '@/components/Trayectoria'
import { api } from '@/lib/api'
import type { Alerta } from '@/lib/contract'
import { SEVERIDAD_TEXTO, colorScore, fmtMesLargo, fmtNum } from '@/lib/format'
import { iniciales, nombre } from '@/lib/identity'

/**
 * La cartera y el monitor · lo primero que se ve (RF-B11: vista P0).
 *
 * "El sistema no espera a que le preguntéis: levanta la mano cuando una empresa se mueve
 * de verdad" (enunciado §6, bonus). Por eso las alertas van ARRIBA, antes de la tabla.
 */
export default async function Cartera() {
  const [cartera, alertas] = await Promise.all([api.getPortfolio(), api.getAlerts()])
  const ordenada = [...cartera].sort((a, b) => a.score - b.score)

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-3xl peso-medio tracking-tight">Cartera</h1>
        <p className="mt-1.5 text-sm text-ink-2">
          {cartera.length} empresas · {alertas.length} movimientos este mes
        </p>
      </header>

      <section>
        <h2 className="peso-medio mb-4 text-sm">El sistema ha levantado la mano</h2>
        <div className="grid gap-3">
          {alertas.map((a) => (
            <FilaAlerta key={a.entity_id} a={a} />
          ))}
        </div>
      </section>

      <Cuadrante cartera={cartera} />

      <section>
        <h2 className="peso-medio mb-4 text-sm">Todas las empresas</h2>
        <div className="overflow-hidden rounded-2xl border border-line">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-surface-2 text-left text-xs text-ink-2">
                <th className="px-5 py-3 peso-medio">Empresa</th>
                <th className="px-5 py-3 peso-medio">Score</th>
                <th className="px-5 py-3 peso-medio">Estado</th>
                <th className="px-5 py-3 peso-medio">24 meses</th>
              </tr>
            </thead>
            <tbody>
              {ordenada.map((s) => (
                <tr key={s.entity_id} className="border-b border-line last:border-0 hover:bg-surface-3">
                  <td className="px-5 py-3">
                    <Link href={`/empresa/${s.entity_id}`} className="flex items-center gap-3 hover:underline">
                      <span className="tabular flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-2 text-[11px] text-ink-2">
                        {iniciales(s.entity_id)}
                      </span>
                      {nombre(s.entity_id)}
                    </Link>
                  </td>
                  <td className="tabular px-5 py-3 peso-medio" style={{ color: colorScore(s.score) }}>
                    {s.scoring_pendiente ? <span className="text-ink-2 peso-medio">—</span> : fmtNum(s.score)}
                  </td>
                  <td className="px-5 py-3">
                    {s.scoring_pendiente ? (
                      <span className="text-xs text-ink-2">Scoring pendiente · {s.meses_historia} meses</span>
                    ) : (
                      <EstadoEtiqueta estado={s.estado} tendencia={s.tendencia} />
                    )}
                  </td>
                  <td className="px-5 py-2">
                    <div className="w-32">
                      <Trayectoria puntos={s.trayectoria} color={colorScore(s.score)} alto={40} compacto />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function FilaAlerta({ a }: { a: Alerta }) {
  const color =
    a.severidad === 'ALTA' ? 'var(--negativo)' : a.severidad === 'MEDIA' ? 'var(--score-bajo)' : 'var(--positivo)'
  return (
    <Link
      href={`/empresa/${a.entity_id}`}
      className="flex items-start gap-4 rounded-xl border border-line p-4 transition-colors hover:bg-surface-3"
    >
      <span
        className="mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] peso-medio"
        style={{ color, borderColor: color }}
      >
        {SEVERIDAD_TEXTO[a.severidad]}
      </span>
      <div className="min-w-0">
        <p className="peso-medio text-sm">{nombre(a.entity_id)}</p>
        <p className="mt-0.5 text-sm leading-relaxed text-ink-3">{a.frase}</p>
        <p className="tabular mt-1 text-xs text-ink-2">
          Detectado en {fmtMesLargo(a.mes_deteccion)} · {a.meses_anticipacion} meses de anticipación
        </p>
      </div>
    </Link>
  )
}
