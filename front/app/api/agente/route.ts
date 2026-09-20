/**
 * Asistente de cartera: el bucle del agente.
 *
 * Recibe el historial del chat, conecta con el MCP que expone la API de X-Ray
 * (backend/mcp_server.py), deja que el modelo llame a las herramientas que
 * necesite y devuelve un único stream con texto, llamadas y resultados. El
 * front pinta cada resultado con su widget.
 *
 * La clave de OpenAI vive solo aquí, en el servidor de Next.
 */
import { openai } from "@ai-sdk/openai";
import { createMCPClient } from "@ai-sdk/mcp";
import { streamText, convertToModelMessages, stepCountIs, type UIMessage } from "ai";
import type { ModoAgente } from "@/lib/agente";
import { acotar } from "@/lib/agente-alcance";

export const maxDuration = 120;

/* En Railway el servidor de Next puede hablar con la API por otra URL que el navegador. */
const API = process.env.XRAY_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const MODELO = process.env.OPENAI_MODEL ?? "gpt-5-mini";
const MAX_PASOS = 8;

// ── Contexto de la cartera para el prompt del sistema ─────────────────────
// Se lee una vez y se guarda diez minutos: los datos son del último corte.
type Contexto = { as_of: string; total: number; con_score: number; medio: number; riesgo: number; mejora: number };
let contextoCache: { valor: Contexto; hasta: number } | null = null;

async function contextoCartera(): Promise<Contexto | null> {
  if (contextoCache && contextoCache.hasta > Date.now()) return contextoCache.valor;
  try {
    const r = await fetch(`${API}/api/portfolio?top=1&per_segment=1`, { cache: "no-store" });
    if (!r.ok) return null;
    const p = await r.json();
    const valor: Contexto = {
      as_of: String(p.as_of).slice(0, 10), total: p.total_companies, con_score: p.eligible_companies,
      medio: p.average_score, riesgo: p.risk_companies_count, mejora: p.improving_companies_count,
    };
    contextoCache = { valor, hasta: Date.now() + 10 * 60_000 };
    return valor;
  } catch {
    return null;
  }
}

function sistema(ctx: Contexto | null, empresa: string | null): string {
  const lineas = [
    "Eres el asistente de cartera de X Ray, el módulo de salud financiera de Embat. Hablas con un analista de Embat que mira toda su cartera de clientes. Respondes en español, con precisión y sin relleno.",
    "",
    "Qué es X Ray: un score de 0 a 100 por empresa y mes, calculado del rastro bancario y de facturación. Tres pilares de salud base (liquidez 50 %, cobros 30 %, servicio de la deuda 20 %) más ajustes de momentum, crecimiento y fragilidad. El desglose es aditivo: los bloques suman el score.",
    "Estados del monitor: MEJORANDO, RECUPERACION, ESTABLE, BACHE (tensión puntual), TORCIENDOSE (alerta temprana con score aún aceptable), DETERIORO (caída estructural), EVALUACION_PENDIENTE (historia insuficiente).",
    "Bandas del score: <25 Crítico, 25–45 Frágil, 45–60 Atención, 60–80 Estable, ≥80 Sólido.",
    "Segmentos de acción para Embat: APOSTAR (elegible, score ≥ 60 y mejorando o Δ3m ≥ 10: sana y creciendo, candidata a línea de crédito o módulo sin coste), VIGILAR (torciéndose o deterioro: retención, ofrecer ayuda antes de perder al cliente), ACOMPANAR (bache: seguimiento cercano).",
    "",
    "Identificadores: empresas COMP_0001…COMP_1286, grupos GROUP_0001…GROUP_0250. Al usuario nómbralas como 'Sociedad 0773' o 'Grupo 0055', y añade el identificador entre paréntesis la primera vez. Si el usuario da un número suelto, es una empresa.",
    "",
    "Cómo trabajar:",
    "- Usa las herramientas para cualquier dato. No inventes cifras ni empresas. Si una herramienta devuelve error, dilo y sugiere qué comprobar.",
    "- Para preguntas globales empieza por resumen_cartera. Para una empresa, por ficha_empresa. Para 'bache o caída' y 'cuándo se vio venir', episodios_empresa.",
    "- Cada resultado de herramienta ya se muestra al usuario como widget visual. No repitas tablas ni listas largas de números: interpreta, prioriza y recomienda. Cita solo las dos o tres cifras que sostienen la conclusión.",
    "- Cuando compares empresas o pidas varias fichas, llama a las herramientas necesarias y luego concluye.",
    "- Cierra con una recomendación accionable para Embat cuando tenga sentido (qué producto, a quién, cuándo).",
    "- Formato: párrafos cortos y listas breves en Markdown. Sin tablas Markdown, sin títulos grandes, sin emojis.",
  ];
  if (ctx) {
    lineas.push(
      "",
      `Cartera hoy (corte ${ctx.as_of}): ${ctx.total} clientes, ${ctx.con_score} con score, score medio ${ctx.medio.toFixed(1)}, ${ctx.riesgo} en riesgo, ${ctx.mejora} en mejora.`,
    );
  }
  if (empresa) {
    lineas.push("", `Empresa en foco: ${empresa}. Si el usuario no nombra otra, las preguntas van sobre ella.`);
  }
  return lineas.join("\n");
}

function sistemaEmpresa(ctx: Contexto | null, empresa: string, grupo: string): string {
  const nombre = empresa.replace("COMP_", "Sociedad ");
  return [
    `Eres el asistente de X Ray para ${nombre} (${empresa}), que ha contratado el módulo de salud financiera dentro de Embat. Hablas con su responsable financiero en segunda persona: "tu score", "tu grupo". Respondes en español, con precisión y sin relleno.`,
    "",
    "Qué es X Ray: un score de 0 a 100 por empresa y mes, calculado del rastro bancario y de facturación. Tres pilares de salud base (liquidez 50 %, cobros 30 %, servicio de la deuda 20 %) más ajustes de momentum, crecimiento y fragilidad. El desglose es aditivo: los bloques suman el score.",
    "Estados: MEJORANDO, RECUPERACION, ESTABLE, BACHE (tensión puntual), TORCIENDOSE (alerta temprana con score aún aceptable), DETERIORO (caída estructural), EVALUACION_PENDIENTE (historia insuficiente).",
    "Bandas del score: <25 Crítico, 25–45 Frágil, 45–60 Atención, 60–80 Estable, ≥80 Sólido. El score es una palanca para negociar con bancos y proveedores: explica qué lo sube.",
    "",
    `Alcance: solo ${nombre} y su grupo (${grupo.replace("GROUP_", "Grupo ")}, ${grupo}). Las herramientas ya están fijadas a esa empresa y a ese grupo; ignoran cualquier otro identificador. Si te preguntan por otra empresa o por la cartera de Embat, di que este asistente solo ve tus datos y los de tu grupo. No hables de "clientes", de "cartera" ni de segmentos Apostar, Vigilar o Acompañar: eso es lectura interna de Embat.`,
    "",
    "Cómo trabajar:",
    "- Usa las herramientas para cualquier dato. No inventes cifras. Si una herramienta devuelve error, dilo y sugiere qué comprobar.",
    "- Para 'cómo estoy' empieza por ficha_empresa. Para 'bache o caída' y 'cuándo se vio venir', episodios_empresa. Para 'qué puedo hacer', palancas y, si procede, simular_palancas o que_pasaria_si. Para el futuro, prevision_estructural. Para el grupo, grupo y flujos_intragrupo.",
    "- Cada resultado de herramienta ya se muestra como widget visual. No repitas tablas ni listas largas de números: interpreta, prioriza y recomienda. Cita solo las dos o tres cifras que sostienen la conclusión.",
    "- Cierra con la acción concreta que más subiría el score cuando tenga sentido.",
    "- Formato: párrafos cortos y listas breves en Markdown. Sin tablas Markdown, sin títulos grandes, sin emojis.",
    ctx ? `\nCorte de datos: ${ctx.as_of}.` : "",
  ].join("\n");
}

async function grupoDe(empresa: string): Promise<string | null> {
  try {
    const r = await fetch(`${API}/api/companies/${empresa}`, { cache: "no-store" });
    if (!r.ok) return null;
    return String((await r.json()).group_id);
  } catch {
    return null;
  }
}

function normalizarEmpresa(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const m = v.trim().toUpperCase().match(/^(?:COMP_)?(\d{1,4})$/);
  return m ? `COMP_${m[1].padStart(4, "0")}` : null;
}

export async function POST(req: Request) {
  if (!process.env.OPENAI_API_KEY) {
    return Response.json({ error: "Falta OPENAI_API_KEY en el servidor del front." }, { status: 500 });
  }

  let cuerpo: { messages?: UIMessage[]; empresa?: unknown; modo?: unknown };
  try {
    cuerpo = await req.json();
  } catch {
    return Response.json({ error: "Petición mal formada." }, { status: 400 });
  }
  const mensajes = Array.isArray(cuerpo.messages) ? cuerpo.messages : [];
  const empresa = normalizarEmpresa(cuerpo.empresa);
  const modo: ModoAgente = cuerpo.modo === "empresa" ? "empresa" : "embat";
  if (modo === "empresa" && !empresa) {
    return Response.json({ error: "El asistente de empresa necesita saber qué empresa eres." }, { status: 400 });
  }

  // Un cliente MCP por turno: el transporte es sin sesión y así no hay estado que se pudra.
  let mcp: Awaited<ReturnType<typeof createMCPClient>>;
  try {
    mcp = await createMCPClient({
      transport: { type: "http", url: `${API}/mcp/` },
      clientName: "xray-asistente",
    });
  } catch {
    return Response.json(
      { error: "El motor no responde. Arranca el backend (uvicorn backend.main:app) y vuelve a intentarlo." },
      { status: 503 },
    );
  }

  const [todas, ctx, grupo] = await Promise.all([
    mcp.tools(), contextoCartera(), modo === "empresa" && empresa ? grupoDe(empresa) : Promise.resolve(null),
  ]);
  if (modo === "empresa" && !grupo) {
    await mcp.close().catch(() => {});
    return Response.json({ error: `No encuentro la empresa ${empresa} en el motor.` }, { status: 404 });
  }
  const tools = modo === "empresa" && empresa && grupo ? acotar(todas, empresa, grupo) : todas;

  const result = streamText({
    model: openai(MODELO),
    system: modo === "empresa" && empresa && grupo ? sistemaEmpresa(ctx, empresa, grupo) : sistema(ctx, empresa),
    messages: await convertToModelMessages(mensajes),
    tools,
    stopWhen: stepCountIs(MAX_PASOS),
    onFinish: async () => { await mcp.close().catch(() => {}); },
    onAbort: async () => { await mcp.close().catch(() => {}); },
  });

  return result.toUIMessageStreamResponse({
    onError: (e) => {
      const msg = e instanceof Error ? e.message : String(e);
      // Que el error llegue legible al usuario, sin volcar detalles del proveedor.
      if (/api key|401|unauthorized/i.test(msg)) return "La clave de OpenAI no es válida o ha caducado.";
      if (/rate|429/i.test(msg)) return "OpenAI ha limitado las peticiones. Espera unos segundos y reintenta.";
      return `El asistente se ha interrumpido: ${msg.slice(0, 200)}`;
    },
  });
}
