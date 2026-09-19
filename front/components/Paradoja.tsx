'use client'

/**
 * La pantalla de apertura del pitch.
 *
 * El enunciado §2 nos regala la historia: en el mes 24 Northbrook saca 65 y Velasco 68.
 * Tres puntos. "Una es mucho mejor riesgo que la otra, y en la foto de hoy no se
 * distingue cuál." Esta pantalla enseña primero la foto —y solo la foto—, y después
 * revela los 24 meses.
 *
 * Son los primeros 60-90 segundos del guion (B12), y por eso es una pantalla y no una
 * diapositiva: lo que el jurado ve en pantalla es lo que puntúa.
 */

import { useState } from 'react'
import Link from 'next/link'
import type { RespuestaScore } from '@/lib/contract'
import { nombre } from '@/lib/identity'
import { colorScore, fmtMes, fmtNum } from '@/lib/format'
import { BandaScore, EstadoEtiqueta, ScoreNumero } from './Score'
import { Trayectoria } from './Trayectoria'

export function Paradoja({ a, b, mesDeteccion }: { a: RespuestaScore; b: RespuestaScore; mesDeteccion: string }) {
  const [revelado, setRevelado] = useState(false)

  return (
    <div>
      <section className="-mx-6 mb-10 rounded-none bg-navy px-6 py-14 sm:mx-0 sm:rounded-2xl sm:px-12">
        <p className="mb-4 text-xs uppercase tracking-[0.2em] text-agua">Septiembre de 2026</p>
        <h1 className="max-w-3xl text-4xl leading-[1.15] text-white sm:text-5xl">
          Dos empresas. <span className="text-agua">Tres puntos</span> de diferencia.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-[var(--inv-content-secondary)]">
          Una de las dos es mucho mejor riesgo que la otra. En la foto de hoy no se distingue cuál — y la
          foto de hoy es todo lo que mira un bureau de crédito.
        </p>
      </section>

      <div className="grid gap-5 sm:grid-cols-2">
        <Tarjeta s={a} revelado={revelado} mesDeteccion={undefined} />
        <Tarjeta s={b} revelado={revelado} mesDeteccion={mesDeteccion} />
      </div>

      {!revelado ? (
        <div className="mt-10 text-center">
          <button
            onClick={() => setRevelado(true)}
            className="rounded-full bg-navy px-7 py-3.5 text-sm peso-medio text-white transition-transform hover:scale-[1.02]"
          >
            Enseñar los 24 meses
          </button>
          <p className="mt-3 text-xs text-ink-2">Lo que el rastro del dinero sí distingue</p>
        </div>
      ) : (
        <Conclusion a={a} b={b} />
      )}
    </div>
  )
}

function Tarjeta({
  s,
  revelado,
  mesDeteccion,
}: {
  s: RespuestaScore
  revelado: boolean
  mesDeteccion?: string
}) {
  const primero = s.trayectoria[0]
  const delta = s.score - primero.score

  return (
    <article className="rounded-2xl border border-line bg-surface p-7">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="peso-medio text-lg">{nombre(s.entity_id)}</h2>
          <p className="text-xs text-ink-2">
            {s.peer.etiqueta} · {s.peer.n_empresas} empresas comparables
          </p>
        </div>
        {revelado && <EstadoEtiqueta estado={s.estado} tendencia={s.tendencia} />}
      </header>

      <ScoreNumero score={s.score} />
      <div className="mt-5">
        <BandaScore score={s.score} />
      </div>

      {revelado && (
        <div className="mt-8 border-t border-line pt-6">
          <p className="tabular mb-4 text-sm">
            <span className="text-ink-2">Desde {fmtMes(primero.mes)}:</span>{' '}
            <span className="peso-medio" style={{ color: delta >= 0 ? 'var(--positivo)' : 'var(--negativo)' }}>
              {fmtNum(primero.score)} → {fmtNum(s.score)} ({delta >= 0 ? '+' : '−'}
              {fmtNum(Math.abs(delta))} puntos)
            </span>
          </p>
          <Trayectoria puntos={s.trayectoria} color={colorScore(s.score)} mesDeteccion={mesDeteccion} />
          {s.frase && <p className="mt-5 text-sm leading-relaxed text-ink-3">{s.frase}</p>}
          <Link
            href={`/empresa/${s.entity_id}`}
            className="mt-5 inline-flex text-sm peso-medio text-agua-oscuro hover:underline"
          >
            Ver por qué →
          </Link>
        </div>
      )}
    </article>
  )
}

function Conclusion({ a, b }: { a: RespuestaScore; b: RespuestaScore }) {
  return (
    <section className="mt-10 rounded-2xl border border-line bg-surface-2 p-8">
      <h3 className="peso-medio mb-3 text-lg">La foto miente; la trayectoria no</h3>
      <p className="max-w-3xl text-sm leading-relaxed text-ink-3">
        {nombre(a.entity_id)} lleva dos años subiendo y {nombre(b.entity_id)} lleva nueve meses cayendo. Hoy
        sacan casi lo mismo. Un bureau de crédito puntúa con cuentas depositadas en el Registro Mercantil:
        su input financiero arrastra entre 8 y 18 meses. Nosotros leemos el movimiento del mes pasado.
      </p>
      <p className="mt-5 max-w-3xl border-l-2 border-agua pl-4 text-sm leading-relaxed peso-medio">
        Informa te puntúa con un balance de hace quince meses. Nosotros, con el movimiento de ayer.
      </p>
    </section>
  )
}
