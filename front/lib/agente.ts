/**
 * Lo que comparten el route handler del asistente y su interfaz: nombres
 * humanos de cada herramienta del MCP y la lectura del resultado que devuelve.
 *
 * El modelo no genera HTML: elige herramientas, y el front decide cómo se ve
 * cada resultado (components/agente/widgets.tsx).
 */

/** Cómo se anuncia cada herramienta mientras corre y en el pie del widget. */
export const HERRAMIENTAS: Record<string, { corriendo: string; titulo: string }> = {
  resumen_cartera:       { corriendo: "Leyendo la cartera",                    titulo: "Cartera Embat" },
  buscar_empresas:       { corriendo: "Buscando empresas",                     titulo: "Empresas" },
  alertas:               { corriendo: "Consultando las alertas",               titulo: "Alertas del monitor" },
  ficha_empresa:         { corriendo: "Abriendo la ficha",                     titulo: "Ficha" },
  historia_empresa:      { corriendo: "Trazando la trayectoria",               titulo: "Trayectoria" },
  episodios_empresa:     { corriendo: "Revisando los episodios",               titulo: "Episodios de cambio" },
  comparables_empresa:   { corriendo: "Comparando con sus pares",              titulo: "Frente a sus pares" },
  facturas_empresa:      { corriendo: "Repasando las facturas",                titulo: "Facturas" },
  grupo:                 { corriendo: "Abriendo el grupo",                     titulo: "Grupo" },
  flujos_intragrupo:     { corriendo: "Siguiendo el dinero dentro del grupo",  titulo: "Flujos intragrupo" },
  que_pasaria_si:        { corriendo: "Simulando la inyección",                titulo: "Qué pasaría si" },
  palancas:              { corriendo: "Buscando palancas",                     titulo: "Palancas" },
  simular_palancas:      { corriendo: "Simulando las palancas",                titulo: "Simulación de palancas" },
  prevision_estructural: { corriendo: "Proyectando doce meses",                titulo: "Previsión estructural" },
};

export function etiquetaHerramienta(nombre: string) {
  return HERRAMIENTAS[nombre] ?? { corriendo: `Consultando ${nombre.replace(/_/g, " ")}`, titulo: nombre.replace(/_/g, " ") };
}

/** Resultado crudo de una herramienta MCP tal y como lo entrega el AI SDK. */
type ResultadoMcp = {
  content?: Array<{ type: string; text?: string }>;
  structuredContent?: unknown;
  isError?: boolean;
};

/**
 * Saca los datos de un resultado MCP: structuredContent si lo hay, o el JSON
 * del primer bloque de texto. Devuelve `error` si la herramienta falló o el
 * motor contestó con error.
 */
export function datosDe<T = Record<string, unknown>>(output: unknown): { datos: T | null; error: string | null } {
  if (!output || typeof output !== "object") return { datos: null, error: "Sin resultado" };
  const r = output as ResultadoMcp;
  let datos: unknown = r.structuredContent;
  if (datos == null) {
    const texto = r.content?.find((c) => c.type === "text")?.text;
    if (texto) {
      try { datos = JSON.parse(texto); } catch { datos = { texto }; }
    }
  }
  if (r.isError) {
    const texto = r.content?.find((c) => c.type === "text")?.text;
    return { datos: null, error: texto || "La herramienta devolvió un error" };
  }
  if (datos && typeof datos === "object" && "error" in (datos as Record<string, unknown>)) {
    const e = (datos as { error: unknown }).error;
    return { datos: null, error: typeof e === "string" ? e : JSON.stringify(e) };
  }
  return { datos: (datos as T) ?? null, error: datos == null ? "Sin datos" : null };
}

/** Quién pregunta: Embat mirando su cartera, o una empresa mirándose a sí misma. */
export type ModoAgente = "embat" | "empresa";

/** A dónde lleva una empresa según quién mira: Embat abre la ficha de cliente; la empresa, la suya. */
export const hrefEmpresa = (id: string, modo: ModoAgente) => (modo === "embat" ? `/embat/${id}` : `/${id}`);
export const hrefGrupo = (gid: string, modo: ModoAgente, empresa?: string | null) =>
  modo === "embat" || !empresa ? `/grupo/${gid}` : `/${empresa}/grupo`;

/** Preguntas de arranque. Con una empresa en foco, la primera es sobre ella. */
export function sugerencias(empresa?: string | null, modo: ModoAgente = "embat"): string[] {
  if (modo === "empresa") {
    return [
      "¿Cómo estoy hoy y de dónde sale mi score?",
      "¿Estoy en un bache o en una caída? ¿Cuándo se vio venir?",
      "¿Qué palancas tengo para subir el score y cuánto aporta cada una?",
      "¿Cómo me iría en doce meses en los tres escenarios? ¿Y mi grupo?",
    ];
  }
  const base = [
    "¿Quién se está torciendo este mes y qué debería hacer Embat con cada uno?",
    "Compara la empresa que más cae con la que más crece en los últimos tres meses.",
    "¿Qué pasaría si inyectamos 25.000 € a la peor empresa del segmento Vigilar?",
    "¿Qué grupo tiene más sociedades en riesgo? Enséñame sus flujos internos.",
  ];
  if (!empresa) return base;
  const nombre = empresa.replace("COMP_", "Sociedad ");
  return [
    `Hazme un diagnóstico completo de ${nombre}: ficha, trayectoria y qué palancas tiene.`,
    `¿${nombre} está en un bache o en una caída estructural? ¿Cuándo se vio venir?`,
    `¿Cómo le iría a ${nombre} en doce meses en los tres escenarios?`,
    ...base.slice(0, 1),
  ];
}
