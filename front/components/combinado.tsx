"use client";
import { useEffect, useMemo, useState } from "react";
import { PALANCAS, type Empresa } from "@/lib/data";
import { apiSimular, type ApiPalanca, type ApiSugerencia, type ApiSimulateResponse } from "@/lib/api";
import { choca } from "@/lib/combinacion";
import { payloadPalanca } from "@/lib/palanca-payload";
import { senda, acota, volatilidad } from "@/lib/proyeccion";
import { LAST_CLOSED_MONTH } from "@/lib/calendar";
import { eur, num, mesCorto } from "@/lib/format";
import { Card, Delta, ScoreBadge } from "@/components/ui";
import { Deslizador } from "@/components/deslizador";
import { Contador } from "@/components/contador";

const SIN = "#787d96";
const CON = "#80efa2";

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
  usar_confirming: "Pagar a proveedores con confirming, sin tocar el gasto",
  ofrecer_pronto_pago_proveedor: "Pagar antes a cambio de descuento",
  refinanciar: "Sustituir deuda cara por deuda a plazo",
  bajar_utilizacion_linea: "Reducir el dispuesto de la póliza",
  sustituir_factoring: "Cambiar factoring por línea de crédito",
};

const RANGO: Record<string, { min: number; max: number; defecto: number; unidad: string }> = {
  usar_confirming: { min: 10, max: 40, defecto: 20, unidad: "% del AP" },
  adelantar_cobros: { min: 7, max: 30, defecto: 15, unidad: "días antes" },
  disponer_linea: { min: 10, max: 80, defecto: 20, unidad: "%" },
  amortizar_linea_con_caja: { min: 10, max: 80, defecto: 20, unidad: "%" },
  vender_inversiones: { min: 10, max: 100, defecto: 50, unidad: "%" },
};

const RANGO_POR_DEFECTO = { min: 1, max: 20, defecto: 10, unidad: "%" };

const DEL_MOTOR: Record<string, string> = {
  adelantar_cobros: "reducir_dso", descuento_pronto_pago: "pronto_pago",
  recortar_opex: "recortar_opex", ampliar_dpo: "ampliar_dpo",
  ofrecer_pronto_pago_proveedor: "ampliar_dpo", refinanciar: "refinanciar",
  bajar_utilizacion_linea: "bajar_linea", sustituir_factoring: "sustituir_fact",
  reducir_concentracion: "reducir_concent",
};

type Ajuste = { id: string; calc: string; valor: number };

type LecturaMotor = {
  caja: number;
  eurAnio: number | null;
  deltaScore: number | null;
  scoreProyectado: number | null;
  eurosPorPalanca: Record<string, number>;
  error: string | null;
};

const MOTIVO: Record<string, string> = {
  sin_confirming: "Esta empresa no tiene confirming",
  inaplicable: "Esta palanca no aplica a la empresa",
  missing_agreement_type: "Falta el tipo de acuerdo",
  mutuamente_excluyentes: "Palancas incompatibles",
  sin_evidencia_score: "Sin historia suficiente para simular",
};

function leerSimulate(res: ApiSimulateResponse | null): LecturaMotor {
  if (!res) {
    return { caja: 0, eurAnio: null, deltaScore: null, scoreProyectado: null, eurosPorPalanca: {}, error: "El motor no responde" };
  }
  if (res.detail && !res.projected) {
    const d = res.detail;
    const crudo = d.motivo_rechazo ?? d.error ?? "Inaplicable";
    return {
      caja: 0, eurAnio: null, deltaScore: null, scoreProyectado: null, eurosPorPalanca: {},
      error: MOTIVO[crudo] ?? crudo.replace(/_/g, " "),
    };
  }
  const delta = res.delta_score;
  const eurosPorPalanca: Record<string, number> = {};
  for (const effect of res.effects ?? []) {
    eurosPorPalanca[effect.lever_id] = Math.round(effect.euros);
  }
  return {
    caja: Math.round(res.caja_liberada_eur ?? 0),
    eurAnio: res.eur_año == null ? null : Math.round(res.eur_año),
    deltaScore: delta == null ? null : Math.round(delta * 10) / 10,
    scoreProyectado: delta == null || !res.projected ? null : Math.round(res.projected.score * 10) / 10,
    eurosPorPalanca,
    error: null,
  };
}

function valorDe(s: ApiSugerencia, p: { min: number; max: number; defecto: number }) {
  const bruto = s.days ?? (s.pct != null ? s.pct * 100 : s.haircut != null ? s.haircut * 100 : null);
  if (bruto == null) return p.defecto;
  return Math.round(Math.min(p.max, Math.max(p.min, bruto)) * 10) / 10;
}

export function Combinado({ empresa: e, aplicables, palancas, inicial }:
  { empresa: Empresa; aplicables?: string[]; palancas?: ApiPalanca[]; inicial?: ApiSugerencia | null; producto?: string | null }) {
  const disponibles = useMemo(() => {
    const delMotor = (palancas ?? []).filter((p) => p.es_aplicable);
    const lista = delMotor.length
      ? delMotor.map((p) => p.id)
      : (aplicables ?? PALANCAS.map((x) => x.id));
    return lista.map((id) => {
      const local = PALANCAS.find((x) => x.id === (DEL_MOTOR[id] ?? id));
      const rango = RANGO[id] ?? local ?? RANGO_POR_DEFECTO;
      return {
        id,
        calc: local?.id ?? id,
        nombre: NOMBRES[id] ?? id.replace(/_/g, " "),
        descripcion: DESCRIPCIONES[id] ?? local?.descripcion ?? "Palanca del catálogo del motor",
        unidad: rango.unidad,
        min: rango.min,
        max: rango.max,
        defecto: rango.defecto,
        familia: palancas?.find((p) => p.id === id)?.familia ?? (id === "usar_confirming" ? "circulante" : "salud"),
      };
    });
  }, [palancas, aplicables]);

  const [ajustes, setAjustes] = useState<Ajuste[]>(() => {
    if (!inicial) return [];
    const calc = DEL_MOTOR[inicial.id] ?? inicial.id;
    const p = disponibles.find((x) => x.id === inicial.id)
      ?? PALANCAS.find((x) => x.id === calc);
    return p ? [{ id: inicial.id, calc, valor: valorDe(inicial, p) }] : [];
  });
  const [lectura, setLectura] = useState<LecturaMotor | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (!ajustes.length) {
      setLectura(null);
      setCargando(false);
      return;
    }
    let vivo = true;
    const espera = window.setTimeout(() => {
      setCargando(true);
      apiSimular(e.id, ajustes.map((a) => payloadPalanca(a.id, a.valor))).then((res) => {
        if (!vivo) return;
        setLectura(leerSimulate(res));
        setCargando(false);
      });
    }, 180);
    return () => {
      vivo = false;
      window.clearTimeout(espera);
    };
  }, [ajustes, e.id]);

  const alterna = (id: string) => {
    setAjustes((prev) => {
      if (prev.some((a) => a.id === id)) return prev.filter((a) => a.id !== id);
      const d = disponibles.find((x) => x.id === id)!;
      const enConflicto = prev.filter((a) => !choca(a.calc, [d.calc]));
      return [...enConflicto, { id, calc: d.calc, valor: d.defecto }];
    });
  };

  const cambia = (id: string, valor: number) => {
    setAjustes((prev) => prev.map((a) => (a.id === id ? { ...a, valor } : a)));
  };

  const g = useMemo(() => {
    const MESES = 12;
    const hist = e.trayectoria.length
      ? e.trayectoria.slice(-12)
      : [{ mes: LAST_CLOSED_MONTH.slice(0, 7), score: e.score, nivel: e.nivelBase }];
    const hoy = hist[hist.length - 1].score;
    const vol = volatilidad(hist.map((p) => p.score));
    const sinActuar = acota(hoy + e.momentum * 14);
    const lift = lectura?.deltaScore ?? 0;
    const conPlan = lectura?.scoreProyectado != null
      ? acota(sinActuar + (lectura.scoreProyectado - hoy))
      : acota(sinActuar + lift);
    return {
      hist, hoy, MESES, sinActuar, conPlan,
      a: senda(hoy, sinActuar, MESES, 0.95, vol, 4101),
      b: senda(hoy, conPlan, MESES, 0.7, vol, 4102),
      mueveScore: lectura?.deltaScore != null,
    };
  }, [e, lectura]);

  const ancho = 1000, alto = 232, padL = 14, padR = 150, padT = 16, padB = 26;
  const w = ancho - padL - padR, h = alto - padT - padB;
  const n = g.hist.length, total = n - 1 + g.MESES;
  const vals = [...g.hist.map((p) => p.score), ...g.a, ...(g.mueveScore ? g.b : [])];
  const lo = Math.max(0, Math.min(...vals) - 6), hi = Math.min(100, Math.max(...vals) + 6);
  const x = (i: number) => padL + (i / total) * w;
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * h;
  const xHoy = x(n - 1), xFin = x(total);
  const pts = (vs: number[]) => vs.map((v, k) => `${x(n - 1 + k).toFixed(1)},${y(v).toFixed(1)}`);
  const linea = g.hist.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.score).toFixed(1)}`).join(" ");

  return (
    <>
      <div className="flex min-h-0 flex-1 flex-col items-stretch gap-4 lg:grid lg:grid-cols-[320px_1fr] lg:grid-rows-[minmax(0,1fr)]">
        <Card className="caja-decisiones px-5 py-4">
          <h2 className="flex-none text-[14.5px] font-semibold tracking-tight">Decisiones</h2>
          <p className="mt-0.5 flex-none text-[11.5px] text-[var(--color-ink-3)]">
            {disponibles.length} aplicables a tu empresa · {ajustes.length} activas
          </p>

          <div className="columna-scroll mt-3 flex min-h-0 flex-1 flex-col gap-2 pb-1">
            {disponibles.map((p) => {
              const a = ajustes.find((x) => x.id === p.id);
              const bloqueada = !a && choca(p.calc, ajustes.map((x) => x.calc));
              const euros = a ? lectura?.eurosPorPalanca[p.id] : undefined;
              return (
                <div key={p.id} className={`accion ${a ? "on" : ""}`}>
                  <label className="flex cursor-pointer items-start gap-3">
                    <input type="checkbox" checked={!!a} onChange={() => alterna(p.id)}
                      className="marca mt-0.5 flex-none" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="text-[13px] font-medium">{p.nombre}</span>
                        {inicial && inicial.id === p.id && (
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
                    {a && euros != null && euros > 0 && (
                      <span className="tnum shrink-0 text-[12px] font-medium text-[var(--color-ink)]">{eur(euros, true)}</span>
                    )}
                  </label>

                  {a && (p.calc === "pronto_pago" ? (
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

        <div className="columna-derecha grid h-auto content-start gap-4 lg:h-full">
          <Card className={`px-4 py-4 sm:px-6 ${cargando ? "opacity-70" : ""}`}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-[12px] text-[var(--color-ink-3)]">
                  {g.mueveScore ? "Score en el corte, con estas decisiones" : "Impacto en el corte actual"}
                </p>
                <div className="mt-1.5 flex items-baseline gap-3">
                  {g.mueveScore && lectura?.scoreProyectado != null ? (
                    <>
                      <ScoreBadge score={lectura.scoreProyectado} />
                      <Delta v={lectura.deltaScore ?? 0} sufijo=" pts" />
                    </>
                  ) : (
                    <p className="tnum text-[28px] font-semibold leading-none" style={{ color: "var(--color-purple)" }}>
                      {lectura && lectura.caja > 0 ? eur(lectura.caja, true) : "—"}
                    </p>
                  )}
                </div>
                {!g.mueveScore && ajustes.length > 0 && !lectura?.error && (
                  <p className="mt-1.5 text-[11.5px] text-[var(--color-ink-4)]">
                    Circulante: libera caja, no reescribe el score
                  </p>
                )}
              </div>
              <div className="flex gap-6">
                <Mini k="Caja neta liberada" v={lectura && lectura.caja > 0 ? eur(lectura.caja) : "—"} />
                {lectura?.eurAnio != null && lectura.eurAnio > 0 && (
                  <Mini k="Ahorro anual" v={eur(lectura.eurAnio)} />
                )}
              </div>
            </div>
            {lectura?.error && (
              <p className="mt-3 text-[12px]" style={{ color: "var(--color-warning)" }}>{lectura.error}</p>
            )}

            <svg viewBox={`0 0 ${ancho} ${alto}`} className="-mx-3 mt-3 w-[calc(100%+1.5rem)]" role="img"
              aria-label={g.mueveScore
                ? `Proyección sin actuar ${num(g.sinActuar)} y con el plan ${num(g.conPlan)}`
                : `Trayectoria actual, score ${num(g.hoy)}`}>
              <defs>
                <linearGradient id="comb-gan" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={CON} stopOpacity="0.04" />
                  <stop offset="100%" stopColor={CON} stopOpacity="0.22" />
                </linearGradient>
              </defs>
              {[0.25, 0.5, 0.75].map((k) => (
                <line key={k} x1={padL} x2={xFin} y1={y(lo + (hi - lo) * k)} y2={y(lo + (hi - lo) * k)} stroke="rgba(255,255,255,.05)" />
              ))}
              {ajustes.length > 0 && g.mueveScore && (
                <path d={`M${pts(g.b).join(" L")} L${pts(g.a).reverse().join(" L")} Z`} fill="url(#comb-gan)" />
              )}
              <line x1={xHoy} y1={padT} x2={xHoy} y2={padT + h} stroke="rgba(255,255,255,.14)" strokeDasharray="3 5" />
              <path d={linea} fill="none" stroke="#b083e8" strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round" />
              <path d={`M${pts(g.a).join(" L")}`} fill="none" stroke={SIN} strokeWidth="1.8" strokeDasharray="5 5" strokeLinecap="round" />
              {ajustes.length > 0 && g.mueveScore && (
                <path d={`M${pts(g.b).join(" L")}`} fill="none" stroke={CON} strokeWidth="3" strokeLinecap="round" />
              )}
              <circle cx={xHoy} cy={y(g.hoy)} r="5.5" fill="#fff" />
              <circle cx={xFin} cy={y(g.sinActuar)} r="5" fill={SIN} />
              {ajustes.length > 0 && g.mueveScore && <circle cx={xFin} cy={y(g.conPlan)} r="6.5" fill={CON} />}
              {ajustes.length > 0 && g.mueveScore && (
                <>
                  <text x={xFin + 13} y={y(g.conPlan) - 3} fill={CON} fontSize="16" fontWeight="500">Con el plan · {num(g.conPlan)}</text>
                  <text x={xFin + 13} y={y(g.conPlan) + 17} fill={CON} fillOpacity="0.75" fontSize="14">+{num(lectura?.deltaScore ?? 0)} pts</text>
                </>
              )}
              <text x={xFin + 13} y={y(g.sinActuar) + (g.mueveScore && Math.abs(y(g.sinActuar) - y(g.conPlan)) < 34 ? 30 : 5)} fill={SIN} fontSize="14.5">
                Sin actuar · {num(g.sinActuar)}
              </text>
              <text x={padL} y={alto - 8} fill="#787d96" fontSize="13">{mesCorto(g.hist[0].mes)}</text>
              <text x={xHoy} y={alto - 8} fill="#787d96" fontSize="13" textAnchor="middle">hoy</text>
              <text x={xFin} y={alto - 8} fill="#787d96" fontSize="13" textAnchor="middle">+12m</text>
            </svg>
          </Card>

          {ajustes.length > 0 && (
            <Card className="flex min-h-0 flex-col px-6 py-4">
              <h2 className="text-[14.5px] font-semibold tracking-tight">
                {lectura && lectura.caja > 0 ? "De dónde sale la caja" : "Decisiones activas"}
              </h2>
              <div className="lista-desglose mt-3 flex min-h-0 flex-1 flex-col gap-2">
                {ajustes.map((a) => {
                  const p = disponibles.find((x) => x.id === a.id);
                  const euros = lectura?.eurosPorPalanca[a.id] ?? 0;
                  return (
                    <div key={a.id} className="fila flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
                      <span className="text-[12.5px] font-medium">
                        {p?.nombre ?? a.id}{" "}
                        <span className="tnum font-normal text-[var(--color-ink-3)]">· {a.valor} {p?.unidad}</span>
                      </span>
                      <span className="tnum text-[12px] text-[var(--color-ink-2)]">
                        {euros > 0 ? eur(euros) : p?.familia === "circulante" || a.id === "usar_confirming" ? "circulante" : "—"}
                      </span>
                    </div>
                  );
                })}
              </div>
              <p className="mt-3 flex-none text-[11px] leading-relaxed text-[var(--color-ink-4)]">
                Los euros salen del motor sobre el AR/AP de esta empresa. El score solo se mueve
                si el motor lo autoriza; confirming y el resto de circulante no inventan puntos.
              </p>
            </Card>
          )}

          {ajustes.length === 0 && (
            <Card className="px-6 py-10 text-center">
              <p className="text-[13.5px] font-medium">Ninguna decisión activa</p>
              <p className="mx-auto mt-1.5 max-w-sm text-[12px] leading-relaxed text-[var(--color-ink-3)]">
                Marca a la izquierda las que quieras probar. Confirming enseña caja; el anticipo, caja y score si el motor los calcula.
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
