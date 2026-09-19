import Link from 'next/link'
import { notFound } from 'next/navigation'
import { CodigosRazon, Drivers } from '@/components/Drivers'
import { BandaScore, ConfianzaEtiqueta, EstadoEtiqueta, ScoreNumero } from '@/components/Score'
import { Trayectoria } from '@/components/Trayectoria'
import { ApiError, api } from '@/lib/api'
import { colorScore, fmtMes, fmtMesLargo, fmtNum } from '@/lib/format'
import { identidad, nombre, nombreGrupo } from '@/lib/identity'

export default async function Ficha({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  let s
  try {
    s = await api.getScore(id)
  } catch (e) {
    if (e instanceof ApiError) notFound()
    throw e
  }

  const ident = identidad(id)
  const alertas = await api.getAlerts()
  const alerta = alertas.find((a) => a.entity_id === id)
  const primero = s.trayectoria[0]

  // RF-B11.9 · el 32 % de las empresas tiene menos de 12 meses y el jurado va a hacer clic
  if (s.scoring_pendiente) {
    return <ScoringPendiente id={id} meses={s.meses_historia} />
  }

  return (
    <div>
      <Cabecera id={id} grupo={ident.group_id} pais={ident.pais} peer={s.peer.etiqueta} n={s.peer.n_empresas} />

      <div className="mt-8 grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        <section className="rounded-2xl border border-line p-7">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-5">
            <div>
              <ScoreNumero score={s.score} />
              <p className="tabular mt-2 text-sm text-ink-2">
                {fmtMes(primero.mes)} · {fmtNum(primero.score)} → hoy {fmtNum(s.score)}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <EstadoEtiqueta estado={s.estado} tendencia={s.tendencia} />
              <ConfianzaEtiqueta semaforo={s.confianza.semaforo} valor={s.confianza.valor} />
            </div>
          </div>

          <BandaScore score={s.score} />

          <div className="mt-8">
            <Trayectoria
              puntos={s.trayectoria}
              color={colorScore(s.score)}
              mesDeteccion={alerta?.mes_deteccion}
              alto={230}
            />
          </div>

          {s.frase && (
            <p className="mt-7 border-l-2 border-agua pl-4 text-sm leading-relaxed text-ink-3">{s.frase}</p>
          )}
        </section>

        <aside className="space-y-8">
          {alerta && (
            <section className="rounded-2xl border border-line bg-surface-2 p-6">
              <h2 className="peso-medio mb-1 text-sm">Cuándo se vio venir</h2>
              <p className="tabular mb-3 text-xs text-ink-2">
                Detectado en {fmtMesLargo(alerta.mes_deteccion)} · {alerta.meses_anticipacion} meses de
                anticipación
              </p>
              <p className="text-sm leading-relaxed text-ink-3">{alerta.frase}</p>
            </section>
          )}

          <section>
            <h2 className="peso-medio mb-4 text-sm">Por qué este número</h2>
            <Drivers drivers={s.drivers} />
          </section>

          {s.codigos_razon.length > 0 && (
            <section>
              <h2 className="peso-medio mb-3 text-sm">Códigos de razón</h2>
              <CodigosRazon codigos={s.codigos_razon} />
            </section>
          )}

          <section className="rounded-2xl border border-dashed border-line-2 p-6">
            <h2 className="peso-medio mb-2 text-sm">Qué pasaría si…</h2>
            <p className="text-sm leading-relaxed text-ink-2">
              El simulador traduce cada palanca a puntos de score y a euros. Pendiente de `/simulate` (B8).
            </p>
          </section>
        </aside>
      </div>

      <p className="mt-10 text-xs text-ink-2">
        Grupo <Link href={`/grupo/${ident.group_id}`} className="underline hover:text-ink">{nombreGrupo(ident.group_id)}</Link>
      </p>
    </div>
  )
}

function Cabecera({ id, grupo, pais, peer, n }: { id: string; grupo: string; pais?: string; peer: string; n: number }) {
  return (
    <header>
      <Link href="/cartera" className="text-xs text-ink-2 hover:text-ink">
        ← Cartera
      </Link>
      <h1 className="mt-2 text-3xl peso-medio tracking-tight">{nombre(id)}</h1>
      <p className="mt-1.5 text-sm text-ink-2">
        {nombreGrupo(grupo)}
        {pais && ` · ${pais}`} · comparada contra {peer.toLowerCase()} ({n} empresas)
      </p>
    </header>
  )
}

/** Un estado vacío con contenido real, no un placeholder (research §8). */
function ScoringPendiente({ id, meses }: { id: string; meses: number }) {
  return (
    <div className="mx-auto max-w-2xl py-10">
      <Link href="/cartera" className="text-xs text-ink-2 hover:text-ink">
        ← Cartera
      </Link>
      <h1 className="mt-2 text-3xl peso-medio tracking-tight">{nombre(id)}</h1>
      <div className="mt-8 rounded-2xl border border-line bg-surface-2 p-8">
        <p className="peso-medio mb-3">Scoring pendiente · datos insuficientes</p>
        <p className="text-sm leading-relaxed text-ink-3">
          Esta empresa lleva {meses} meses conectada. El motor necesita doce para medir trayectoria, y la
          trayectoria es la mitad del score: emitir un número con seis meses sería fingir una precisión que
          no tenemos.
        </p>
        <div className="tabular mt-6 border-t border-line pt-5 text-sm text-ink-2">
          <p>
            Historia conectada <span className="peso-medio text-ink">{meses} / 12 meses</span>
          </p>
          <div className="mt-2 h-1.5 w-full rounded-full bg-surface">
            <div className="h-1.5 rounded-full bg-agua" style={{ width: `${(meses / 12) * 100}%` }} />
          </div>
        </div>
        <p className="mt-6 text-xs text-ink-2">
          En el dataset del reto, el 32 % de las empresas está en esta situación. Decirlo es parte del
          producto.
        </p>
      </div>
    </div>
  )
}
