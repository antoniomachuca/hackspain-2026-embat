import Link from 'next/link'
import { notFound } from 'next/navigation'
import { EstadoEtiqueta, ScoreNumero } from '@/components/Score'
import { ApiError, api } from '@/lib/api'
import { colorScore, fmtNum } from '@/lib/format'
import { nombre, nombreGrupo } from '@/lib/identity'

/**
 * Vista de grupo (B6) · "El grupo saca 71, pero la filial francesa saca 38 y arrastra al
 * consolidado". Multi-entidad es la razón de ser de Embat: por eso este módulo es
 * opcional para el leaderboard y obligatorio para el producto (PRODUCTO.md §4).
 */
export default async function Grupo({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let g
  try {
    g = await api.getGroup(id)
  } catch (e) {
    if (e instanceof ApiError) notFound()
    throw e
  }
  const peor = g.filiales.find((f) => f.entity_id === g.peor_filial)

  return (
    <div>
      <h1 className="text-3xl peso-medio tracking-tight">{nombreGrupo(g.group_id)}</h1>
      <p className="mt-1.5 text-sm text-ink-2">{g.filiales.length} entidades consolidadas</p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_1.4fr]">
        <section className="rounded-2xl border border-line p-7">
          <p className="mb-3 text-xs uppercase tracking-wide text-ink-2">Consolidado</p>
          <ScoreNumero score={g.consolidado} />
          {peor && (
            <p className="mt-6 border-l-2 border-[var(--negativo)] pl-4 text-sm leading-relaxed text-ink-3">
              El grupo saca {fmtNum(g.consolidado)}, pero {nombre(peor.entity_id)} saca{' '}
              {fmtNum(peor.score)} y arrastra al consolidado. La penalización por contagio resta{' '}
              {fmtNum(g.penalizacion_contagio)} puntos a la media ponderada.
            </p>
          )}
        </section>

        <section>
          <h2 className="peso-medio mb-4 text-sm">Filiales</h2>
          <div className="space-y-2">
            {[...g.filiales]
              .sort((a, b) => a.score - b.score)
              .map((f) => (
                <Link
                  key={f.entity_id}
                  href={`/empresa/${f.entity_id}`}
                  className="flex items-center gap-4 rounded-xl border border-line p-4 transition-colors hover:bg-surface-3"
                >
                  <span className="tabular w-12 text-xl peso-medio" style={{ color: colorScore(f.score) }}>
                    {fmtNum(f.score)}
                  </span>
                  <span className="min-w-0 flex-1 text-sm">{nombre(f.entity_id)}</span>
                  <span className="tabular text-xs text-ink-2">{Math.round(f.peso * 100)} % del grupo</span>
                  <EstadoEtiqueta estado={f.estado} />
                </Link>
              ))}
          </div>
        </section>
      </div>
    </div>
  )
}
