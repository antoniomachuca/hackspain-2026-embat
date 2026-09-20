/**
 * Alcance del asistente en modo empresa: qué herramientas ve y con qué
 * identificadores. Solo servidor (lo usa app/api/agente/route.ts).
 */
import type { Tool, ToolSet } from "ai";

/* Herramientas que hablan de una empresa o de un grupo: en modo empresa se fijan al alcance. */
const CON_EMPRESA = new Set(["ficha_empresa", "historia_empresa", "episodios_empresa", "comparables_empresa", "facturas_empresa", "alertas", "que_pasaria_si", "palancas", "simular_palancas", "prevision_estructural"]);
const CON_GRUPO = new Set(["grupo", "flujos_intragrupo"]);
const SOLO_CARTERA = new Set(["resumen_cartera", "buscar_empresas"]);

/**
 * Acota las herramientas a una empresa y su grupo. Las de cartera desaparecen
 * y en el resto el identificador lo pone el servidor, no el modelo: aunque el
 * prompt falle, no hay manera de leer datos de otro cliente.
 */
export function acotar(tools: ToolSet, empresa: string, grupo: string): ToolSet {
  const out: ToolSet = {};
  for (const [nombre, t] of Object.entries(tools)) {
    if (SOLO_CARTERA.has(nombre) || !t.execute) continue;
    const ejecutar = t.execute as (args: unknown, opts: Parameters<NonNullable<Tool["execute"]>>[1]) => unknown;
    out[nombre] = {
      ...t,
      execute: (args: unknown, opts) => {
        const a = { ...((args ?? {}) as Record<string, unknown>) };
        if (CON_EMPRESA.has(nombre)) a.empresa = empresa;
        if (CON_GRUPO.has(nombre)) a.grupo = grupo;
        return ejecutar(a, opts);
      },
    } as Tool;
  }
  return out;
}

