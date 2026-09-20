"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * La cuenta, en el pie del panel.
 *
 * Es un conmutador de punto de vista, no una sesión: la misma aplicación se
 * mira desde la empresa —su ficha y su grupo— o desde Embat —la cartera
 * entera—. No hay usuarios ni permisos detrás; ambas vistas son públicas por
 * su dirección y siempre lo fueron.
 */
export function Cuenta({ abierto }: { abierto: boolean }) {
  const router = useRouter();
  const [menu, setMenu] = useState(false);
  const [admin, setAdmin] = useState(false);
  const caja = useRef<HTMLDivElement>(null);

  useEffect(() => {
    /* eslint-disable-next-line react-hooks/set-state-in-effect */
    try { setAdmin(sessionStorage.getItem("xray:admin") === "1"); } catch {}
  }, []);

  useEffect(() => {
    if (!menu) return;
    const fuera = (e: MouseEvent) => {
      if (caja.current && !caja.current.contains(e.target as Node)) setMenu(false);
    };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [menu]);

  const verComo = (comoAdmin: boolean) => {
    try {
      if (comoAdmin) sessionStorage.setItem("xray:admin", "1");
      else sessionStorage.removeItem("xray:admin");
      sessionStorage.setItem("xray:modo", comoAdmin ? "embat" : "empresa");
    } catch {}
    setAdmin(comoAdmin);
    setMenu(false);
    router.push(comoAdmin ? "/" : "/COMP_0773");
  };

  return (
    <div ref={caja} className="relative">
      <button onClick={() => setMenu((v) => !v)}
        className="cuenta-boton" aria-haspopup="menu" aria-expanded={menu}
        title={admin ? "Embat · toda la cartera" : "Sociedad 0773"}>
        <span className="cuenta-avatar" aria-hidden>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="8" r="3.2" /><path d="M5 20c.8-3.2 3.1-5 7-5s6.2 1.8 7 5" />
          </svg>
        </span>
        {abierto && (
          <span className="pl-etiqueta min-w-0 text-left">
            <span className="block truncate text-[12.5px] font-medium">
              {admin ? "Administrador" : "Sociedad 0773"}
            </span>
            <span className="block truncate text-[10.5px] text-[var(--color-ink-4)]">
              {admin ? "Embat · toda la cartera" : "Su propia ficha"}
            </span>
          </span>
        )}
      </button>

      {menu && (
        <div className="cuenta-menu" role="menu">
          <button role="menuitem" className={`cuenta-opcion ${admin ? "" : "on"}`} onClick={() => verComo(false)}>
            Ver como empresa
            <span>su ficha y su grupo</span>
          </button>
          <button role="menuitem" className={`cuenta-opcion ${admin ? "on" : ""}`} onClick={() => verComo(true)}>
            Ver como administrador
            <span>la cartera completa de Embat</span>
          </button>
        </div>
      )}
    </div>
  );
}
