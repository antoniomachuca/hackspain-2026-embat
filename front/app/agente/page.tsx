/**
 * Asistente de cartera: Embat conversa con el motor.
 * Acepta ?empresa=COMP_0773 para arrancar con una empresa en foco.
 */
import { Cabecera } from "@/components/shell";
import { Chat } from "@/components/agente/chat";
import { apiPortfolio } from "@/lib/api";
import { mesCorto, num } from "@/lib/format";

export const metadata = { title: "Asistente · X Ray" };

function normalizar(v: string | string[] | undefined): string | null {
  const s = Array.isArray(v) ? v[0] : v;
  const m = (s ?? "").trim().toUpperCase().match(/^(?:COMP_)?(\d{1,4})$/);
  return m ? `COMP_${m[1].padStart(4, "0")}` : null;
}

export default async function AgentePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const empresa = normalizar(sp.empresa);
  const pf = await apiPortfolio(1, 1);

  return (
    <div className="flex min-h-[calc(100vh-80px)] flex-col sm:h-[calc(100vh-40px)] sm:min-h-0">
      <Cabecera
        titulo="Asistente de cartera"
        sub={
          pf
            ? <>{num(pf.total_companies, 0)} clientes · corte {mesCorto(pf.as_of.slice(0, 7))}{empresa ? <> · en foco <span className="text-[var(--color-ink-2)]">{empresa.replace("COMP_", "Sociedad ")}</span></> : null}</>
            : <span className="text-[var(--color-warm)]">El motor no responde. Arranca el backend para que el asistente tenga datos.</span>
        }
      />
      <Chat empresa={empresa} />
    </div>
  );
}
