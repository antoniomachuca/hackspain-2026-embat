/**
 * Payload que entiende POST /api/simulate. El id es el del catálogo del motor.
 * No traduce confirming a opex ni inventa tipos de acuerdo.
 */
export function payloadPalanca(id: string, valor: number): Record<string, unknown> {
  switch (id) {
    case "reducir_dso":
    case "adelantar_cobros":
      return { id, days: valor, agreement_type: "presion_comercial" };
    case "pronto_pago":
    case "descuento_pronto_pago":
      return {
        id: "descuento_pronto_pago",
        days: 15,
        haircut: valor / 100,
        agreement_type: "descuento_pronto_pago",
      };
    case "recortar_opex":
      return { id: "recortar_opex", pct: valor / 100 };
    case "refinanciar":
    case "renegociar_interes":
    case "leasing_a_cuota_menor":
      return { id, pct: valor / 100 };
    case "ampliar_dpo":
      return { id: "ampliar_dpo", pct: valor / 100, agreement_type: "acuerdo_negociado" };
    case "usar_confirming":
      return { id: "usar_confirming", pct: valor / 100 };
    case "ofrecer_pronto_pago_proveedor":
      return {
        id: "ofrecer_pronto_pago_proveedor",
        pct: valor / 100,
        agreement_type: "acuerdo_negociado",
        proposed_cost_pct: 0.02,
      };
    case "bajar_linea":
    case "bajar_utilizacion_linea":
      return { id: "bajar_utilizacion_linea", pct: valor / 100 };
    case "reducir_concent":
    case "reducir_concentracion":
      return { id: "reducir_concentracion", pct: valor / 100 };
    case "sustituir_fact":
    case "sustituir_factoring":
      return { id: "sustituir_factoring", pct: valor / 100 };
    default:
      return { id, pct: valor / 100 };
  }
}
