"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Isotipo } from "@/components/isotipo";

const Icono = ({ trazo, ...r }: { trazo: React.ReactNode } & React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden {...r}>{trazo}</svg>
);

const RUTAS = [
  { href: "/", label: "Resumen",
    icono: <><rect x="3" y="3" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="3" width="7.5" height="7.5" rx="2" />
      <rect x="3" y="13.5" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" /></> },
  { href: "/grupos", label: "Mi grupo",
    icono: <><circle cx="12" cy="6" r="2.6" /><circle cx="5.5" cy="17" r="2.6" /><circle cx="18.5" cy="17" r="2.6" />
      <path d="M12 8.6v3.2M10 13.5 7.4 15.4M14 13.5l2.6 1.9" /></> },
  { href: "/comparar", label: "Escenarios",
    icono: <><path d="M3 17l4.5-8 3.5 5 3-7L21 17" /><path d="M3 21h18" /></> },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="flex min-h-screen">
      <aside className="rail hidden sm:flex">
        <span className="rail-marca" title="Embat"><Isotipo size={19} /></span>
        <nav className="rail-nav">
          {RUTAS.map((r, i) => {
            const on = r.href === "/" ? path === "/" : path.startsWith(r.href);
            return (
              <Link key={r.href} href={r.href} className={on ? "on" : ""}
                style={{ "--i": i } as React.CSSProperties} aria-label={r.label}>
                <Icono width="19" height="19" trazo={r.icono} />
                <span className="tip">{r.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="rail-pie">
          <button className="rail-i" aria-label="Alertas">
            <Icono width="19" height="19" trazo={<><path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></>} />
            <span className="punto-aviso" />
          </button>
          <button className="rail-i" aria-label="Ajustes">
            <Icono width="19" height="19" trazo={<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H1.7a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 3.3 7.5" /></>} />
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-5 py-5 sm:px-7">{children}</main>
    </div>
  );
}

/** Cabecera superior: título a la izquierda, acciones redondas a la derecha. */
export function Cabecera({ titulo, sub, extra }: { titulo: string; sub?: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <header className="mb-5 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-[26px] font-semibold tracking-tight">{titulo}</h1>
        {sub && <div className="mt-1 text-[12.5px] text-[var(--color-ink-3)]">{sub}</div>}
      </div>
      <div className="flex items-center gap-2.5">
        {extra}
        <button className="flex h-10 w-10 items-center justify-center rounded-full bg-[rgba(255,255,255,.08)] text-[var(--color-ink-2)] transition-colors hover:bg-[rgba(255,255,255,.14)]" aria-label="Buscar">
          <Icono width="17" height="17" trazo={<><circle cx="11" cy="11" r="7" /><path d="m20 20-3.2-3.2" /></>} />
        </button>
        <span className="flex h-10 w-10 items-center justify-center rounded-full text-[13px] font-semibold"
          style={{ background: "linear-gradient(145deg,var(--color-purple-mid),var(--color-purple-deep))", color: "#0d0416" }}>
          Q
        </span>
      </div>
    </header>
  );
}
