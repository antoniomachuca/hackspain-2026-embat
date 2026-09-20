"use client";
import { useState } from "react";
import type { Empresa } from "@/lib/data";
import type { ApiPalanca, ApiSugerencia } from "@/lib/api";
import { Modal } from "@/components/modal";
import { Combinado } from "@/components/combinado";

/**
 * El simulador vive en un diálogo, no en una página.
 *
 * Es una herramienta de "qué pasaría si", y esas se abren sobre lo que estás
 * mirando: al cerrarla vuelves exactamente al sitio del que saliste, sin
 * navegación ni pérdida de contexto.
 */
export function DialogoSimulador({ empresa, aplicables, palancas, inicial, producto, etiqueta }:
  {
    empresa: Empresa; aplicables?: string[]; palancas?: ApiPalanca[];
    inicial?: ApiSugerencia | null; producto?: string | null; etiqueta: string;
  }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setAbierto(true)} className="boton-simulador mt-5 w-full">
        {etiqueta}
      </button>
      <Modal abierto={abierto} onCerrar={() => setAbierto(false)}
        titulo="Simulador"
        sub={producto
          ? `Parte de la solución de Embat —${producto.toLowerCase()}— y combina lo que quieras`
          : "Combina varias decisiones y mira qué pasa con tu trayectoria"}>
        <div className="flex h-full min-h-0 flex-col px-4 py-4 sm:px-7 sm:py-5">
          <Combinado empresa={empresa} aplicables={aplicables} palancas={palancas} inicial={inicial} producto={producto} />
        </div>
      </Modal>
    </>
  );
}
