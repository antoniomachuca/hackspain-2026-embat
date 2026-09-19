"use client";
import { useMemo, useState } from "react";
import { PALANCAS, type Empresa } from "@/lib/data";
import type { ApiPalanca, ApiSugerencia } from "@/lib/api";
import { combinar, choca } from "@/lib/combinacion";

type Ajuste = { id: string; calc: string; valor: number };
import { senda, acota, volatilidad } from "@/lib/proyeccion";
import { eur, num, mesCorto } from "@/lib/format";
import { Card, Delta, ScoreBadge } from "@/components/ui";
import { Deslizador } from "@/components/deslizador";
import { Contador } from "@/components/contador";

const SIN = "#787d96";
const CON = "#80efa2";

/** Nombre legible de cada palanca del motor. */
const NOMBRES: Record<string, string> = {
  adelantar_cobros: "Adelantar cobros",
  reducir_dso: "Reducir DSO",
  descuento_pronto_pago: "Descuento por pronto pago",
  recortar_opex: "Recortar opex",
  refinanciar: "Refinanciar deuda",
  renegociar_interes: "Renegociar el interés",
  leasing_a_cuota_menor: "Leasing a cuota menor",
  sustituir_factoring: "Sustituir factoring",
  reducir_concentracion: "Reducir concentración",
  bajar_devoluciones: "Bajar devoluciones",
  ampliar_dpo: "Ampliar DPO",
  usar_confirming: "Usar confirming",
  ofrecer_pronto_pago_proveedor: "Pronto pago a proveedores",
  bajar_utilizacion_linea: "Bajar utilización de línea",
  amortizar_linea_con_caja: "Amortizar línea con caja",
  disponer_linea: "Disponer de la línea",
  vender_inversiones: "Vender inversiones",
};

const DESCRIPCIONES: Record<string, string> = {
  adelantar_cobros: "Cobrar antes a los clientes que más tardan",
  descuento_pronto_pago: "Ofrecer descuento por cobro anticipado",
  recortar_opex: "Reducir gasto operativo recurrente",
  ampliar_dpo: "Negociar más plazo con proveedores",
  ofrecer_pronto_pago_proveedor: "Pagar antes a cambio de descuento",
  refinanciar: "Sustituir deuda cara por deuda a plazo",
  bajar_utilizacion_linea: "Reducir el dispuesto de la póliza",
  sustituir_factoring: "Cambiar factoring por línea de crédito",
};

/** Rango del mando cuando el catálogo local no tiene equivalente. */
const RANGO_POR_DEFECTO = { min: 1, max: 20, defecto: 10, unidad: "%" };

/** Equivalencias con los identificadores del motor: solo para el cálculo. */
const DEL_MOTOR: Record<string, string> = {
  adelantar_cobros: "reducir_dso", descuento_pronto_pago: "pronto_pago",
  recortar_opex: "recortar_opex", ampliar_dpo: "ampliar_dpo",
  ofrecer_pronto_pago_proveedor: "ampliar_dpo", refinanciar: "refinanciar",
  bajar_utilizacion_linea: "bajar_linea", sustituir_factoring: "sustituir_fact",
  reducir_concentracion: "reducir_concent",
};

/** El parámetro del motor, traducido a la unidad del mando local. */
function valorDe(s: ApiSugerencia, p: { min: number; max: number; defecto: number }) {
  const bruto = s.days ?? (s.pct != null ? s.pct * 100 : s.haircut != null ? s.haircut * 100 : null);
  if (bruto == null) return p.defecto;
  return Math.round(Math.min(p.max, Math.max(p.min, bruto)) * 10) / 10;
}

export function Combinado({ empresa: e, aplicables, palancas, inicial }:
  { empresa: Empresa; aplicables?: string[]; palancas?: ApiPalanca[]; inicial?: ApiSugerencia | null; producto?: string | null }) {
  /**
   * Una tarjeta por palanca del motor, no por entrada de mi catálogo local.
   * Varias suyas comparten fórmula aquí —adelantar cobros y reducir DSO, por
   * ejemplo—, y agruparlas hacía que el simulador enseñara menos de las que
   * el propio motor dice que se pueden aplicar.
   */
  const disponibles = useMemo(() => {
    const delMotor = (palancas ?? []).filter((p) => p.es_aplicable);
    const lista = delMotor.length
      ? delMotor.map((p) => p.id)
      : (aplicables ?? PALANCAS.map((x) => x.id));
    return lista.map((id) => {
      const local = PALANCAS.find((x) => x.id === (DEL_MOTOR[id] ?? id));
      return {
        id,
        calc: local?.id ?? "recortar_opex",
        nombre: NOMBRES[id] ?? id.replace(/_/g, " "),
        descripcion: DESCRIPCIONES[id] ?? local?.descripcion ?? "Palanca del catálogo del motor",
        unidad: local?.unidad ?? RANGO_POR_DEFECTO.unidad,
        min: local?.min ?? RANGO_POR_DEFECTO.min,
        max: local?.max ?? RANGO_POR_DEFECTO.max,
        defecto: local?.defecto ?? RANGO_POR_DEFECTO.defecto,
      };
    });
  }, [palancas, aplicables]);

  const [ajustes, setAjustes] = useState<Ajuste[]>(() => {
    if (!inicial) return [];
    const calc = DEL_MOTOR[inicial.id] ?? inicial.id;
    const p = PALANCAS.find((x) => x.id === calc);
    return p ? [{ id: inicial.id, calc, valor: valorDe(inicial, p) }] : [];
  });

  const alterna = (id: string) => {
    setAjustes((prev) => {
      if (prev.some((a) => a.id === id)) return prev.filter((a) => a.id !== id);
      const d = disponibles.find((x) => x.id === id)!;
      // Las mutuamente excluyentes se apagan solas: no se pueden firmar a la vez.
      const enConflicto = prev.filter((a) => !choca(a.calc, [d.calc]));
      return [...enConflicto, { id, calc: d.calc, valor: d.defecto }];
    });
  };

  const cambia = (id: string, valor: number) => {
    setAjustes((prev) => prev.map((a) => (a.id === id ? { ...a, valor } : a)));
  };

  const r = useMemo(() => combinar(e, ajustes.map((a) => ({ id: a.calc, valor: a.valor }))), [e, ajustes]);

  // ── Gráfico
  const g = useMemo(() => {
    const MESES = 12;
    const hist = e.trayectoria.length
      ? e.trayectoria.slice(-12)
      : [{ mes: "2026-09", score: e.score, nivel: e.nivelBase }];
    const hoy = hist[hist.length - 1].score;
    const vol = volatilidad(hist.map((p) => p.score));
    const sinActuar = acota(hoy + e.momentum * 14);
    const conPlan = acota(sinActuar + r.deltaTotal);
    return {
      hist, hoy, MESES, sinActuar, conPlan,
      a: senda(hoy, sinActuar, MESES, 0.95, vol, 4101),
      b: senda(hoy, conPlan, MESES, 0.7, vol, 4102),
    };
  }, [e, r.deltaTotal]);

  const ancho = 1000, alto = 232, padL = 14, padR = 150, padT = 16, padB = 26;
  const w = ancho - padL - padR, h = alto - padT - padB;
  const n = g.hist.length, total = n - 1 + g.MESES;
  const vals = [...g.hist.map((p) => p.score), ...g.a, ...g.b];
  const lo = Math.max(0, Math.min(...vals) - 6), hi = Math.min(100, Math.max(...vals) + 6);
  const x = (i: number) => padL + (i / total) * w;
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * h;
  const xHoy = x(n - 1), xFin = x(total);
  const pts = (vs: number[]) => vs.map((v, k) => `${x(n - 1 + k).toFixed(1)},${y(v).toFixed(1)}`);
  const linea = g.hist.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.score).toFixed(1)}`).join(" ");

  return (
    <>
      <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)] items-start gap-4 lg:grid-cols-[320px_1fr]">
        {/* ── Las decisiones ── */}
        <Card className="caja-decisiones px-5 py-4">
          <h2 className="flex-none text-[14.5px] font-semibold tracking-tight">Decisiones</h2>
          <p className="mt-0.5 flex-none text-[11.5px] text-[var(--color-ink-3)]">
            {disponibles.length} aplicables a tu empresa · {ajustes.length} activas
          </p>

          <div className="columna-scroll mt-3 flex min-h-0 flex-1 flex-col gap-2 pb-1">
            {disponibles.map((p) => {
              const a = ajustes.find((x) => x.id === p.id);
              const bloqueada = !a && choca(p.calc, ajustes.map((x) => x.calc));
              return (
                <div key={p.id} className={`accion ${a ? "on" : ""}`}>
                  <label className="flex cursor-pointer items-start gap-3">
                    <input type="checkbox" checked={!!a} onChange={() => alterna(p.id)}
                      className="marca mt-0.5 flex-none" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="text-[13px] font-medium">{p.nombre}</span>
                        {inicial && (DEL_MOTOR[inicial.id] ?? inicial.id) === p.id && (
                          <span className="rounded px-1.5 py-0.5 text-[9.5px] font-semibold tracking-wide"
                            style={{ background: "rgba(176,131,232,.2)", color: "var(--color-purple)" }}>
                            EMBAT
                          </span>
                        )}
                      </span>
                      <span className="descripcion mt-1 block text-[11.5px] leading-snug text-[var(--color-ink-3)]">
                        {p.descripcion}
                      </span>
                      {bloqueada && (
                        <span className="mt-1.5 block text-[10.5px]" style={{ color: "var(--color-warning)" }}>
                          incompatible con {(disponibles.find((q) => q.calc === bloqueada)?.nombre ?? bloqueada).toLowerCase()}
                        </span>
                      )}
                    </span>
                    {a && <Delta v={combinar(e, [{ id: a.calc, valor: a.valor }]).deltaTotal} sufijo=" pts" className="shrink-0" />}
                  </label>

                  {a && (p.calc === "pronto_pago" ? (
                    /* El descuento se firma: pasos exactos, no arrastre. */
                    <div className="sep mt-2.5 border-t border-[rgba(255,255,255,.08)] pt-2.5">
                      <Contador valor={a.valor} min={p.min} max={p.max} paso={0.5}
                        unidad={p.unidad} tam="compacto"
                        onCambio={(v) => cambia(p.id, v)} />
                    </div>
                  ) : (
                    <div className="sep mt-2.5 border-t border-[rgba(255,255,255,.08)] pt-2.5">
                      <div className="tnum flex items-baseline justify-between text-[11px] text-[var(--color-ink-3)]">
                        <span>{p.unidad}</span>
                        <span className="text-[13px] font-semibold text-[var(--color-ink)]">{a.valor}</span>
                      </div>
                      <div className="mt-1">
                        <Deslizador min={p.min} max={p.max} valor={a.valor}
                          etiqueta={`${p.nombre}, ${p.unidad}`}
                          onCambio={(v) => cambia(p.id, v)} />
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </Card>

        {/* ── El resultado ── */}
        <div className="columna-derecha grid h-full content-start gap-4">
          <Card className="px-6 py-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-[12px] text-[var(--color-ink-3)]">Score proyectado a 12 meses</p>
                <div className="mt-1.5 flex items-baseline gap-3">
                  <ScoreBadge score={g.conPlan} />
                  <Delta v={r.deltaTotal} sufijo=" pts" />
                </div>
              </div>
              <div className="flex gap-6">
                <Mini k="Caja liberada" v={r.caja > 0 ? eur(r.caja, true) : "—"} />
                <Mini k="Ahorro anual" v={r.eurAnio > 0 ? eur(r.eurAnio) : "—"} />
                <Mini k="Esfuerzo" v={r.esfuerzoTotal ? num(r.esfuerzoTotal) : "—"} />
              </div>
            </div>

            <svg viewBox={`0 0 ${ancho} ${alto}`} className="-mx-3 mt-3 w-[calc(100%+1.5rem)]" role="img"
              aria-label={`Proyección sin actuar ${num(g.sinActuar)} y con el plan ${num(g.conPlan)}`}>
              <defs>
                <linearGradient id="comb-gan" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={CON} stopOpacity="0.04" />
                  <stop offset="100%" stopColor={CON} stopOpacity="0.22" />
                </linearGradient>
              </defs>
              {[0.25, 0.5, 0.75].map((k) => (
                <line key={k} x1={padL} x2={xFin} y1={y(lo + (hi - lo) * k)} y2={y(lo + (hi - lo) * k)} stroke="rgba(255,255,255,.05)" />
              ))}
              {ajustes.length > 0 && (
                <path d={`M${pts(g.b).join(" L")} L${pts(g.a).reverse().join(" L")} Z`} fill="url(#comb-gan)" />
              )}
              <line x1={xHoy} y1={padT} x2={xHoy} y2={padT + h} stroke="rgba(255,255,255,.14)" strokeDasharray="3 5" />
              <path d={linea} fill="none" stroke="#b083e8" strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round" />
              <path d={`M${pts(g.a).join(" L")}`} fill="none" stroke={SIN} strokeWidth="1.8" strokeDasharray="5 5" strokeLinecap="round" />
              {ajustes.length > 0 && (
                <path d={`M${pts(g.b).join(" L")}`} fill="none" stroke={CON} strokeWidth="3" strokeLinecap="round" />
              )}
              <circle cx={xHoy} cy={y(g.hoy)} r="5.5" fill="#fff" />
              <circle cx={xFin} cy={y(g.sinActuar)} r="5" fill={SIN} />
              {ajustes.length > 0 && <circle cx={xFin} cy={y(g.conPlan)} r="6.5" fill={CON} />}
              {ajustes.length > 0 && (
                <>
                  <text x={xFin + 13} y={y(g.conPlan) - 3} fill={CON} fontSize="16" fontWeight="500">Con el plan · {num(g.conPlan)}</text>
                  <text x={xFin + 13} y={y(g.conPlan) + 17} fill={CON} fillOpacity="0.75" fontSize="14">+{num(r.deltaTotal)} pts</text>
                </>
              )}
              <text x={xFin + 13} y={y(g.sinActuar) + (Math.abs(y(g.sinActuar) - y(g.conPlan)) < 34 ? 30 : 5)} fill={SIN} fontSize="14.5">
                Sin actuar · {num(g.sinActuar)}
              </text>
              <text x={padL} y={alto - 8} fill="#787d96" fontSize="13">{mesCorto(g.hist[0].mes)}</text>
              <text x={xHoy} y={alto - 8} fill="#787d96" fontSize="13" textAnchor="middle">hoy</text>
              <text x={xFin} y={alto - 8} fill="#787d96" fontSize="13" textAnchor="middle">+12m</text>
            </svg>
          </Card>

          {/* ── De dónde sale cada punto ── */}
          {r.partes.length > 0 && (
            <Card className="flex min-h-0 flex-col px-6 py-4">
              <div className="flex flex-none flex-wrap items-baseline justify-between gap-3">
                <h2 className="text-[14.5px] font-semibold tracking-tight">De dónde salen los {num(r.deltaTotal)} puntos</h2>
                {r.perdidaPorSolape > 0 && (
                  <span className="text-[11.5px]" style={{ color: "var(--color-warning)" }}>
                    −{num(r.perdidaPorSolape)} pts por solape entre palancas
                  </span>
                )}
              </div>

              <div className="mt-3 flex h-2 w-full overflow-hidden rounded-full bg-[rgba(255,255,255,.07)]">
                {r.partes.map((p, i) => (
                  <span key={p.palanca.id} style={{
                    width: `${(p.aporte / Math.max(1e-9, r.deltaTotal)) * 100}%`,
                    background: `color-mix(in srgb, ${CON} ${100 - i * 16}%, #7b32c0)`,
                  }} />
                ))}
              </div>

              <div className="lista-desglose mt-3 flex min-h-0 flex-1 flex-col gap-2">
                {r.partes.map((p) => (
                  <div key={p.palanca.id} className="fila flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
                    <span className="text-[12.5px] font-medium">
                      {p.palanca.nombre} <span className="tnum font-normal text-[var(--color-ink-3)]">· {p.valor} {p.palanca.unidad}</span>
                    </span>
                    <span className="tnum flex flex-wrap items-center gap-x-4 text-[11.5px] text-[var(--color-ink-2)]">
                      {p.cajaLiberada > 0 && <span>{eur(p.cajaLiberada)}</span>}
                      <span className="text-[var(--color-ink-4)]">esfuerzo {num(p.esfuerzo)}</span>
                      <Delta v={p.aporte} sufijo=" pts" />
                    </span>
                  </div>
                ))}
              </div>

              <p className="mt-3 flex-none text-[11px] leading-relaxed text-[var(--color-ink-4)]">
                Los efectos no se suman: todas las palancas tiran del mismo margen de mejora, así que la
segunda rinde menos que la primera. El esfuerzo de cada palanca es orientativo: quien decide
                hasta dónde llegar eres tú.
              </p>
            </Card>
          )}

          {r.partes.length === 0 && (
            <Card className="px-6 py-10 text-center">
              <p className="text-[13.5px] font-medium">Ninguna decisión activa</p>
              <p className="mx-auto mt-1.5 max-w-sm text-[12px] leading-relaxed text-[var(--color-ink-3)]">
Marca a la izquierda las que quieras probar y ajusta cada parámetro a tu criterio.
              </p>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function Mini({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">{k}</p>
      <p className="tnum mt-1 text-[16px] font-semibold leading-none">{v}</p>
    </div>
  );
}
