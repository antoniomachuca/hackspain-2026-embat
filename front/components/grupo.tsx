"use client";
import { useState } from "react";
import Link from "next/link";
import { Sparkline } from "@/components/charts";
import { ScoreBadge, Delta } from "@/components/ui";
import type { Punto } from "@/lib/data";

export type Filial = {
  id: string; nombre: string; score: number; momentum: number;
  evaluable: boolean; trayectoria: Punto[];
};

const VISIBLES = 4;

/** Las filiales del grupo. Se enseñan unas pocas y el resto se despliega. */
/** `base` es el prefijo de ruta de la vista: "" para la empresa, "/embat" para Embat. */
export function ListaGrupo({ filiales, base = "", visibles = VISIBLES }: { filiales: Filial[]; base?: string; visibles?: number }) {
  const [todas, setTodas] = useState(false);
  const lista = todas ? filiales : filiales.slice(0, visibles);

  return (
    <div>
      <div className="flex flex-col">
        {lista.map((m) => (
          <Link key={m.id} href={`${base}/${m.id}`}
            className="flex items-center gap-4 border-b border-[var(--color-line)] py-2.5 last:border-0 transition-colors hover:bg-[rgba(255,255,255,.03)]">
            <span className="min-w-0 flex-1 truncate text-[13px]">{m.nombre}</span>

            {m.evaluable ? (
              <>
                <span className="w-[86px] flex-none"><Sparkline datos={m.trayectoria} /></span>
                <span className="w-[44px] flex-none text-right"><Delta v={m.momentum} /></span>
                <span className="w-[38px] flex-none text-right"><ScoreBadge score={m.score} size="sm" /></span>
              </>
            ) : (
              <span className="w-[168px] flex-none text-right text-[11.5px] text-[var(--color-ink-4)]">
                sin score
              </span>
            )}
          </Link>
        ))}
      </div>

      {filiales.length > visibles && (
        <button onClick={() => setTodas((v) => !v)}
          className="mt-3 w-full rounded-lg py-2 text-[12px] text-[var(--color-ink-3)] transition-colors hover:bg-[rgba(255,255,255,.05)] hover:text-[var(--color-ink)]">
          {todas ? "Ver menos" : `Ver las ${filiales.length} sociedades`}
        </button>
      )}
    </div>
  );
}
