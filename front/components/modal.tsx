"use client";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

/**
 * Diálogo con cristal. Se cierra con Escape, con el fondo y con el aspa.
 *
 * Va por portal a <body> y no ahí donde se escribe. Cualquier ancestro con
 * `backdrop-filter`, `filter`, `transform` o `contain: layout` se convierte en
 * bloque contenedor de los elementos `position: fixed`, y el diálogo acababa
 * confinado dentro de la tarjeta que lo abría. Las tarjetas son de cristal y
 * `main` lleva `contain`, así que aquí pasaban las dos cosas a la vez.
 */
export function Modal({ abierto, onCerrar, titulo, sub, children, compacto }:
  { abierto: boolean; onCerrar: () => void; titulo: string; sub?: string; children: React.ReactNode; compacto?: boolean }) {
  const caja = useRef<HTMLDivElement>(null);
  const desdeElFondo = useRef(false);
  const focoAnterior = useRef<HTMLElement | null>(null);
  const cerrarRef = useRef(onCerrar);

  useEffect(() => { cerrarRef.current = onCerrar; }, [onCerrar]);

  useEffect(() => {
    if (!abierto) return;
    focoAnterior.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") cerrarRef.current(); };
    document.addEventListener("keydown", tecla);
    // Sin esto la página de detrás sigue desplazándose con la rueda.
    const previo = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    caja.current?.focus();
    return () => {
      document.removeEventListener("keydown", tecla);
      document.body.style.overflow = previo;
      focoAnterior.current?.focus();
      focoAnterior.current = null;
    };
  }, [abierto]);

  // `abierto` solo se pone a true desde un clic, así que aquí ya hay DOM.
  if (!abierto) return null;

  return createPortal(
    <div
      className="modal-fondo" role="presentation"
      /* Solo cierra si el gesto EMPIEZA en el fondo. Al arrastrar un
         deslizador se suelta a menudo fuera de la caja, y el clic resultante
         cerraba el diálogo: parecía que el mando no respondía. */
      onPointerDown={(e) => { desdeElFondo.current = e.target === e.currentTarget; }}
      onClick={(e) => { if (desdeElFondo.current && e.target === e.currentTarget) onCerrar(); }}
    >
      <div ref={caja} tabIndex={-1} role="dialog" aria-modal="true" aria-label={titulo}
        className={`modal-caja panel ${compacto ? "modal-compacto" : ""}`}>
        <div className="flex items-start justify-between gap-4 px-4 pt-4 sm:px-7 sm:pt-5">
          <div>
            <h2 className="text-[17px] font-semibold tracking-tight">{titulo}</h2>
            {sub && <p className="mt-1 text-[12.5px] text-[var(--color-ink-3)]">{sub}</p>}
          </div>
          <button onClick={onCerrar} aria-label="Cerrar"
            className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-[rgba(255,255,255,.07)] text-[var(--color-ink-3)] transition-colors hover:bg-[rgba(255,255,255,.14)] hover:text-[var(--color-ink)]">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden>
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
