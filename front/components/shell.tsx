"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Isotipo } from "@/components/isotipo";
import { Cuenta } from "@/components/cuenta";

const Icono = ({ trazo, ...r }: { trazo: React.ReactNode } & React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden {...r}>{trazo}</svg>
);

const I = {
  caja:   <><path d="M3 7h18v12H3z" /><path d="M3 11h18" /><path d="M8 7V5h8v2" /></>,
  nodos:  <><circle cx="6" cy="6" r="2.4" /><circle cx="18" cy="6" r="2.4" /><circle cx="12" cy="18" r="2.4" />
            <path d="M7.6 7.7 11 15.8M16.4 7.7 13 15.8M8.4 6h7.2" /></>,
  rayos:  <><path d="M3 17l4.5-8 3.5 5 3-7L21 17" /><path d="M3 21h18" /></>,
  escudo: <><path d="M12 3l7 3v6c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6z" /></>,
  deuda:  <><path d="M4 19V9M10 19V5M16 19v-6M22 19H2" /></>,
  check:  <><rect x="3" y="4" width="18" height="16" rx="2.5" /><path d="m8 12 2.6 2.6L16 9" /></>,
  flecha: <><path d="M4 12h13" /><path d="m13 7 5 5-5 5" /><path d="M21 5v14" /></>,
  enchufe:<><path d="M9 3v6M15 3v6" /><rect x="6" y="9" width="12" height="6" rx="2" /><path d="M12 15v6" /></>,
  panel:  <><rect x="3" y="3" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="3" width="7.5" height="7.5" rx="2" />
            <rect x="3" y="13.5" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" /></>,
  grupo:  <><circle cx="12" cy="6" r="2.6" /><circle cx="5.5" cy="17" r="2.6" /><circle cx="18.5" cy="17" r="2.6" />
            <path d="M12 8.6v3.2M10 13.5 7.4 15.4M14 13.5l2.6 1.9" /></>,
  chispa: <><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="M19 16l.7 1.8 1.8.7-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7z" /></>,
};

type Modulo = { label: string; nota: string; icono: React.ReactNode; href?: string; hijos?: { href: string; label: string; icono: React.ReactNode }[] };
type Seccion = { titulo: string; modulos: Modulo[] };

/** Dos maneras de entrar a X Ray: Embat mirando su cartera, o una empresa mirándose a sí misma. */
type Modo = "embat" | "empresa";

function modoDe(path: string): Modo | null {
  if (path === "/" || path.startsWith("/embat") || path.startsWith("/agente")) return "embat";
  if (/^\/(COMP_)?\d{1,4}(\/|$)/i.test(path) || path.startsWith("/empresa/")) return "empresa";
  return null;   // /grupos, /comparar… valen para los dos
}

function empresaDe(path: string): string | null {
  const m = path.match(/^\/(?:empresa\/)?((?:COMP_)?\d{1,4})(?:\/|$)/i);
  if (!m) return null;
  const n = m[1].toUpperCase().replace("COMP_", "").padStart(4, "0");
  return `COMP_${n}`;
}

/** El catálogo de Embat. X Ray entra en riesgos financieros, que es su sitio. */
const seccionesDe = (modo: Modo, empresa: string): Seccion[] => [
  {
    titulo: "Gestión de tesorería",
    modulos: [
      { label: "Flujos de caja", nota: "Tesorería a tiempo real, previsión y análisis", icono: I.caja },
      { label: "Operaciones intercompañía", nota: "Centraliza tus operaciones internas", icono: I.nodos },
    ],
  },
  {
    titulo: "Gestión de riesgos financieros",
    modulos: [
      modo === "embat"
        ? {
            label: "X Ray", nota: "Salud financiera de la cartera", icono: I.rayos, href: "/",
            hijos: [
              { href: "/", label: "Cartera", icono: I.panel },
              { href: "/grupos", label: "Grupos", icono: I.grupo },
              { href: "/agente", label: "Asistente", icono: I.chispa },
            ],
          }
        : {
            label: "X Ray", nota: "Salud financiera y anticipación", icono: I.rayos, href: `/${empresa}`,
            hijos: [
              { href: `/${empresa}`, label: "Resumen", icono: I.panel },
              { href: `/${empresa}/grupo`, label: "Mi grupo", icono: I.grupo },
            ],
          },
      { label: "Gestión de contrapartes", nota: "Gestiona tus relaciones financieras", icono: I.escudo },
      { label: "Gestión de la deuda", nota: "Gestiona y optimiza la deuda", icono: I.deuda },
    ],
  },
  {
    titulo: "Contabilidad y conciliación",
    modulos: [
      { label: "Conciliación bancaria", nota: "Emparejamiento con IA que ahorra horas", icono: I.check },
    ],
  },
  {
    titulo: "Pagos corporativos",
    modulos: [
      { label: "Flujos y ejecución de pagos", nota: "Ejecuta y rastrea tus pagos", icono: I.flecha },
    ],
  },
  {
    titulo: "Conectividad financiera",
    modulos: [
      { label: "Conectividad bancaria", nota: "Conexión con más de 15.000 bancos", icono: I.enchufe },
    ],
  },
];

/** Qué entrada del submenú se enciende. Las raíces ("/" y "/COMP_xxxx") solo en exacto o en sus fichas. */
function activoHijo(href: string, path: string, empresa: string): boolean {
  if (href === "/") return path === "/" || path.startsWith("/embat");
  if (href === "/agente") return path.startsWith("/agente");
  if (href === `/${empresa}`) return path === href || path.startsWith("/empresa/");
  return path.startsWith(href);
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [abierto, setAbierto] = useState(true);
  const [movilAbierto, setMovilAbierto] = useState(false);

  // El modo se deduce de la ruta; en las compartidas (/grupos, /comparar) se
  // conserva el último conocido para que el menú no salte.
  const [modoGuardado, setModoGuardado] = useState<Modo>("embat");
  const [empresa, setEmpresa] = useState("COMP_0773");
  const modo = modoDe(path) ?? modoGuardado;
  // sessionStorage solo existe tras hidratar; leerlo en el effect evita un desajuste con el servidor.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setMovilAbierto(false);
    const m = modoDe(path);
    const id = empresaDe(path);
    try {
      if (m) { sessionStorage.setItem("xray:modo", m); setModoGuardado(m); }
      else { const v = sessionStorage.getItem("xray:modo"); if (v === "embat" || v === "empresa") setModoGuardado(v); }
      if (id) { sessionStorage.setItem("xray:empresa", id); setEmpresa(id); }
      else { const v = sessionStorage.getItem("xray:empresa"); if (v) setEmpresa(v); }
    } catch {}
  }, [path]);
  /* eslint-enable react-hooks/set-state-in-effect */
  const SECCIONES = seccionesDe(modo, empresa);

  // Se recuerda entre visitas; si el navegador no deja, se queda abierto.
  useEffect(() => {
    try { const v = localStorage.getItem("xray:panel"); if (v !== null) queueMicrotask(() => setAbierto(v === "1")); } catch {}
  }, []);
  const alternar = () => {
    setAbierto((a) => { try { localStorage.setItem("xray:panel", a ? "0" : "1"); } catch {} return !a; });
  };

  const abrirMovil = () => { setAbierto(true); setMovilAbierto(true); };
  const cerrarMovil = () => setMovilAbierto(false);

  return (
    <div className="flex min-h-screen">
      {movilAbierto && (
        <button type="button" className="fixed inset-0 z-40 bg-black/60 sm:hidden" aria-label="Cerrar menú" onClick={cerrarMovil} />
      )}
      <aside className={`panel-lat ${abierto ? "abierto" : "cerrado"} ${movilAbierto ? "movil" : "hidden"} sm:flex`}>
        <div className="pl-cab">
          <button onClick={() => { alternar(); cerrarMovil(); }} className="rail-marca" title={abierto ? "Plegar el menú" : "Desplegar el menú"}
            aria-label={abierto ? "Plegar el menú" : "Desplegar el menú"} aria-expanded={abierto}>
            <Isotipo size={19} />
          </button>
          <div className="pl-etiqueta min-w-0 leading-tight">
            <p className="truncate text-[13.5px] font-semibold">Embat</p>
            <p className="truncate text-[11px] text-[var(--color-ink-4)]">
              {modo === "embat" ? "Cartera de clientes" : empresa.replace("COMP_", "Sociedad ")}
            </p>
          </div>
        </div>

        <nav className="pl-cuerpo">
          {SECCIONES.map((sec) => (
            <div key={sec.titulo} className="pl-seccion">
              <p className="pl-titulo">{sec.titulo}</p>
              {sec.modulos.map((m) => {
                // X Ray es el único módulo con ruta: está activo en todo lo que no sea catálogo.
                const activo = !!m.href;
                const contenido = (
                  <>
                    <Icono width="17" height="17" trazo={m.icono} />
                    <span className="pl-etiqueta min-w-0">
                      <span className="block truncate text-[13px]">{m.label}</span>
                      <span className="block truncate text-[10.5px] text-[var(--color-ink-4)]">{m.nota}</span>
                    </span>
                    <span className="tip">{m.label}</span>
                  </>
                );
                return m.href ? (
                  <div key={m.label}>
                    <Link href={m.href} className={`pl-modulo ${activo ? "on" : ""}`}>{contenido}</Link>
                    {abierto && activo && m.hijos && (
                      <div className="pl-hijos">
                        {m.hijos.map((h) => (
                          <Link key={h.href} href={h.href}
                            className={`pl-hijo ${activoHijo(h.href, path, empresa) ? "on" : ""}`}>
                            <Icono width="14" height="14" trazo={h.icono} />
                            {h.label}
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  /* Módulos del catálogo que aquí no existen: se ven, no se entra. */
                  <span key={m.label} className="pl-modulo vacio" aria-disabled="true" title="Módulo no incluido en esta maqueta">
                    {contenido}
                  </span>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="pl-pie">
          <Cuenta abierto={abierto} />
        </div>
      </aside>

      <button type="button" onClick={abrirMovil} className="fixed left-4 top-3 z-30 flex h-10 items-center gap-2 rounded-full bg-[rgba(8,6,14,.88)] px-4 text-[12px] font-medium text-[var(--color-ink-2)] shadow-lg ring-1 ring-white/10 sm:hidden" aria-label="Abrir menú">
        <Isotipo size={16} /> Menú
      </button>
      <main className="min-w-0 flex-1 px-5 pb-5 pt-16 sm:px-7 sm:py-5">{children}</main>
    </div>
  );
}

export function Cabecera({ titulo, sub, extra }: { titulo: string; sub?: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <header className="mb-5 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-[26px] font-semibold tracking-tight">{titulo}</h1>
        {sub && <div className="mt-1 text-[12.5px] text-[var(--color-ink-3)]">{sub}</div>}
      </div>
      <div className="flex items-center gap-2.5">{extra}</div>
    </header>
  );
}
