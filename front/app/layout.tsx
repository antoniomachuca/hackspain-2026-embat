import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'
import { modoApi } from '@/lib/api'

export const metadata: Metadata = {
  title: 'X-Ray · Salud financiera en movimiento',
  description:
    'El score de salud financiera que lee el rastro del dinero: trayectoria, explicación y euros. HackSpain 2026 · reto Embat.',
}

/** Topbar, no sidebar: es la estructura de embat.io (research §1). */
const NAV = [
  { href: '/', texto: 'La paradoja' },
  { href: '/cartera', texto: 'Cartera' },
  { href: '/prevision', texto: 'Previsión' },
  { href: '/grupo/GROUP_0162', texto: 'Grupo' },
]

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <header className="sticky top-0 z-50 border-b border-line bg-surface/85 backdrop-blur">
          <div className="mx-auto flex min-h-14 max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3 sm:flex-nowrap">
            <Link href="/" className="peso-medio tracking-tight">
              X<span className="text-agua-oscuro">-</span>Ray
            </Link>
            <nav className="flex flex-wrap items-center gap-4 text-sm text-ink-2">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className="transition-colors hover:text-ink">
                  {n.texto}
                </Link>
              ))}
            </nav>
            <span className="ml-auto hidden rounded-full border border-line px-2.5 py-1 text-[11px] text-ink-2 sm:block">
              {modoApi() === 'live' ? 'motor conectado' : 'datos de demostración'}
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-12">{children}</main>
        <footer className="border-t border-line py-8">
          <p className="mx-auto max-w-6xl px-6 text-xs text-ink-2">
            HackSpain 2026 · reto Embat. Dataset sintético: ninguna fila corresponde a una empresa real, y
            los nombres son etiquetas de demostración sobre identificadores anónimos.
          </p>
        </footer>
      </body>
    </html>
  )
}
