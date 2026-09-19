import Link from "next/link";
import { banda, num } from "@/lib/format";
import type { Estado } from "@/lib/data";
import { ESTADO_LABEL } from "@/lib/data";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`panel ${className}`}>
      {children}
    </div>
  );
}

export function CardHead({ titulo, sub, extra }: { titulo: string; sub?: string; extra?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-[var(--color-line)] px-5 py-3.5">
      <div>
        <h2 className="text-[14.5px] font-semibold tracking-tight">{titulo}</h2>
        {sub && <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">{sub}</p>}
      </div>
      {extra}
    </div>
  );
}

/** Variación: flecha + signo + color. Tres canales, nunca solo el color. */
export function Delta({ v, sufijo = "", className = "" }: { v: number; sufijo?: string; className?: string }) {
  const up = v > 0, zero = Math.abs(v) < 0.05;
  const color = zero ? "var(--color-ink-3)" : up ? "var(--color-risk-4)" : "var(--color-risk-2)";
  return (
    <span className={`tnum inline-flex items-center gap-1 text-[12px] font-medium ${className}`} style={{ color }}>
      <span aria-hidden>{zero ? "→" : up ? "↑" : "↓"}</span>
      {zero ? "0" : `${up ? "+" : "−"}${num(Math.abs(v))}`}{sufijo}
    </span>
  );
}

export function ScoreBadge({ score, size = "md" }: { score: number; size?: "sm" | "md" | "lg" }) {
  const b = banda(score);
  const s = size === "lg" ? "text-[56px] leading-none" : size === "sm" ? "text-[15px]" : "text-[28px] leading-none";
  return (
    <span className={`tnum font-medium ${s}`} style={{ color: b.color }}>
      {num(score, size === "sm" ? 0 : 1)}
    </span>
  );
}

export function BandaChip({ score }: { score: number }) {
  const b = banda(score);
  return (
    <span className="rounded-md px-2 py-0.5 text-[11px] font-medium" style={{ background: b.bg, color: b.color }}>
      {b.label}
    </span>
  );
}

export function EstadoChip({ estado }: { estado: Estado | string }) {
  const st = (estado || "").toUpperCase();
  const color =
    st === "DETERIORO"
      ? "#e5775b"
      : st === "TORCIENDOSE"
      ? "#e59f5e"
      : st === "BACHE"
      ? "#dfb631"
      : st === "MEJORANDO" || st === "RECUPERACION"
      ? "#80efa2"
      : st === "ESTABLE"
      ? "#9fe3b4"
      : "var(--color-ink-3)";
  const bg =
    st === "DETERIORO"
      ? "rgba(229,119,91,.16)"
      : st === "TORCIENDOSE"
      ? "rgba(229,159,94,.16)"
      : st === "BACHE"
      ? "rgba(223,182,49,.16)"
      : st === "MEJORANDO" || st === "RECUPERACION"
      ? "rgba(128,239,162,.16)"
      : st === "ESTABLE"
      ? "rgba(159,227,180,.16)"
      : "var(--color-surface-3)";
  const label = ESTADO_LABEL[estado as Estado] ?? estado;
  return (
    <span className="rounded-md px-2 py-0.5 text-[11px] font-medium" style={{ background: bg, color }}>
      {label}
    </span>
  );
}

export function Confianza({ nivel }: { nivel: "ALTA" | "MEDIA" | "BAJA" }) {
  const n = nivel === "ALTA" ? 3 : nivel === "MEDIA" ? 2 : 1;
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-[var(--color-ink-3)]" title={`Confianza del dato: ${nivel.toLowerCase()}`}>
      <span className="flex gap-[2px]" aria-hidden>
        {[1, 2, 3].map((i) => (
          <span key={i} className="h-3 w-[3px] rounded-full"
            style={{ background: i <= n ? "var(--color-purple)" : "rgba(255,255,255,.18)" }} />
        ))}
      </span>
      {nivel.charAt(0) + nivel.slice(1).toLowerCase()}
    </span>
  );
}

export function KPI({ etiqueta, valor, delta, sufijo, nota }:
  { etiqueta: string; valor: string; delta?: number; sufijo?: string; nota?: string }) {
  return (
    <Card className="px-5 py-4">
      <p className="text-[12px] text-[var(--color-ink-3)]">{etiqueta}</p>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="tnum text-[22px] font-medium leading-none">{valor}</span>
        {delta !== undefined && <Delta v={delta} sufijo={sufijo} />}
      </div>
      {nota && <p className="mt-1 text-[11px] text-[var(--color-ink-4)]">{nota}</p>}
    </Card>
  );
}

export function Vacio({ titulo, texto, accion }: { titulo: string; texto: string; accion?: React.ReactNode }) {
  return (
    <div className="panel flex flex-col items-center justify-center border-dashed px-6 py-16 text-center">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--color-surface-3)] text-[var(--color-ink-3)]" aria-hidden>—</div>
      <p className="text-[14px] font-medium">{titulo}</p>
      <p className="mt-1 max-w-sm text-[12px] leading-relaxed text-[var(--color-ink-3)]">{texto}</p>
      {accion && <div className="mt-4">{accion}</div>}
    </div>
  );
}

export function Boton({ children, href, onClick, tono = "primario", type }:
  { children: React.ReactNode; href?: string; onClick?: () => void; tono?: "primario" | "plano"; type?: "button" | "submit" }) {
  const cls = tono === "primario"
    ? "bg-white text-[#0d0416] hover:brightness-95 shadow-[0_6px_20px_rgba(0,0,0,.28)]"
    : "bg-[rgba(255,255,255,.08)] border border-[rgba(255,255,255,.10)] text-[var(--color-ink-2)] hover:bg-[rgba(255,255,255,.14)] hover:text-[var(--color-ink)]";
  const base = `inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-[12.5px] font-medium transition-colors ${cls}`;
  if (href) return <Link href={href} className={base}>{children}</Link>;
  return <button type={type ?? "button"} onClick={onClick} className={base}>{children}</button>;
}
