"use client";

/**
 * Contador con flechas, para los parámetros que se firman.
 *
 * Un deslizador va bien para "cuántos días antes cobro", donde el valor es
 * aproximado y lo que importa es la magnitud. Un descuento es un compromiso
 * que se firma: medio punto sobre una cartera grande son miles de euros, y eso
 * no se fija arrastrando el ratón.
 *
 * Verde arriba y rojo abajo: la dirección manda sobre el significado, como en
 * el resto de la interfaz.
 */
export function Contador({ valor, min, max, paso, unidad, tam = "grande", onCambio }:
  {
    valor: number; min: number; max: number; paso: number; unidad: string;
    tam?: "grande" | "compacto"; onCambio: (v: number) => void;
  }) {
  const ajusta = (d: number) =>
    onCambio(Math.round(Math.min(max, Math.max(min, valor + d * paso)) * 10) / 10);

  // Compacto: misma fila que los demás mandos —etiqueta a la izquierda, valor
  // a la derecha— con las flechas pegadas al borde. Así la columna mantiene su
  // ritmo en vez de romperlo con un bloque suelto.
  if (tam === "compacto") {
    return (
      <div className="flex items-center gap-3 py-1">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] text-[var(--color-ink-3)]">{unidad}</p>
          <p className="tnum mt-0.5 text-[10px] text-[var(--color-ink-4)]">
            {min} a {max} · pasos de {paso}
          </p>
        </div>
        {/* El valor y las flechas, separados del borde derecho: pegados al
            canto la tarjeta se leía desequilibrada. */}
        <div className="mr-6 flex items-center gap-2.5">
          <span className="tnum text-[24px] font-semibold leading-none">{valor.toFixed(1)}</span>
          <Flechas chica sube={() => ajusta(1)} baja={() => ajusta(-1)} topeArriba={valor >= max} topeAbajo={valor <= min} paso={paso} unidad={unidad} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-none items-center gap-5">
      <Flechas sube={() => ajusta(1)} baja={() => ajusta(-1)} topeArriba={valor >= max} topeAbajo={valor <= min} paso={paso} unidad={unidad} />
      <div>
        <p className="tnum text-[44px] font-semibold leading-none">
          {valor.toFixed(1)}
          <span className="ml-1.5 text-[19px] font-normal text-[var(--color-ink-3)]">
            {unidad.replace("% ", "")}
          </span>
        </p>
        <p className="tnum mt-1.5 text-[12px] text-[var(--color-ink-4)]">{min} – {max}</p>
      </div>
    </div>
  );
}

/** Fuera del componente: definida dentro, React la trataba como un tipo nuevo
 *  en cada render y remontaba los botones. */
function Flechas({ chica, sube, baja, topeArriba, topeAbajo, paso, unidad }:
  {
    chica?: boolean; sube: () => void; baja: () => void;
    topeArriba: boolean; topeAbajo: boolean; paso: number; unidad: string;
  }) {
  const w = chica ? 17 : 34, h = chica ? 11 : 22;
  return (
    <div className="flex flex-col">
      <button onClick={sube} disabled={topeArriba}
        className={`flecha subir ${chica ? "chica" : ""}`} aria-label={`Subir ${paso} ${unidad}`}>
        <svg viewBox="0 0 14 9" width={w} height={h} aria-hidden><path d="M7 0 14 9H0z" fill="currentColor" /></svg>
      </button>
      <button onClick={baja} disabled={topeAbajo}
        className={`flecha bajar ${chica ? "chica" : ""}`} aria-label={`Bajar ${paso} ${unidad}`}>
        <svg viewBox="0 0 14 9" width={w} height={h} aria-hidden><path d="M7 9 0 0h14z" fill="currentColor" /></svg>
      </button>
    </div>
  );
}
