import { Paradoja } from '@/components/Paradoja'
import { api } from '@/lib/api'
import { NORTHBROOK, VELASCO } from '@/lib/identity'

export default async function Home() {
  const [northbrook, velasco, alertas] = await Promise.all([
    api.getScore(NORTHBROOK),
    api.getScore(VELASCO),
    api.getAlerts(),
  ])
  const alertaVelasco = alertas.find((a) => a.entity_id === VELASCO)

  return (
    <Paradoja a={northbrook} b={velasco} mesDeteccion={alertaVelasco?.mes_deteccion ?? '2026-04'} />
  )
}
