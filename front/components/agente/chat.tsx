"use client";
/**
 * El chat del asistente de cartera.
 *
 * Una conversación en memoria con el route handler /api/agente. Cada mensaje
 * del agente es una secuencia de partes: texto en Markdown y llamadas a
 * herramientas, que se pintan como widgets en el orden en que llegan.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, isToolUIPart, getToolName, type UIMessage } from "ai";
import ReactMarkdown from "react-markdown";
import { sugerencias } from "@/lib/agente";
import { Widget, WidgetCargando } from "./widgets";

const Icono = ({ trazo, ...r }: { trazo: React.ReactNode } & React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden {...r}>{trazo}</svg>
);
const CHISPA = <><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="M19 16l.7 1.8 1.8.7-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7z" /></>;

export function Chat({ empresa }: { empresa: string | null }) {
  const transport = useMemo(() => new DefaultChatTransport({ api: "/api/agente", body: { empresa } }), [empresa]);
  const { messages, sendMessage, status, error, stop, setMessages, regenerate, clearError } = useChat({ transport });
  const [texto, setTexto] = useState("");
  const fin = useRef<HTMLDivElement>(null);
  const caja = useRef<HTMLTextAreaElement>(null);
  const ocupado = status === "submitted" || status === "streaming";

  useEffect(() => { fin.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages, status]);

  const enviar = (t: string) => {
    const limpio = t.trim();
    if (!limpio || ocupado) return;
    setTexto("");
    void sendMessage({ text: limpio });
  };

  const vacio = messages.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* ── Conversación ─────────────────────────────────────────────── */}
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {vacio ? (
          <Bienvenida empresa={empresa} onElegir={enviar} />
        ) : (
          <div className="mx-auto flex max-w-[980px] flex-col gap-6 pb-4">
            {messages.map((m) => <Mensaje key={m.id} m={m} />)}
            {status === "submitted" && (
              <div className="flex items-center gap-2 text-[12.5px] text-[var(--color-ink-3)]">
                <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--color-purple)]" />Pensando…
              </div>
            )}
            {error && (
              <div className="rounded-2xl border border-[rgba(229,119,91,.35)] bg-[rgba(229,119,91,.08)] px-4 py-3 text-[12.5px] text-[var(--color-ink-2)]">
                <p>{mensajeError(error)}</p>
                <div className="mt-2 flex gap-2">
                  <button type="button" className="pildora" onClick={() => { clearError(); void regenerate(); }}>Reintentar</button>
                  <button type="button" className="text-[12px] text-[var(--color-ink-3)] hover:underline" onClick={() => clearError()}>Cerrar</button>
                </div>
              </div>
            )}
            <div ref={fin} />
          </div>
        )}
      </div>

      {/* ── Caja de texto ─────────────────────────────────────────────── */}
      <form
        className="mx-auto mt-3 w-full max-w-[980px]"
        onSubmit={(e) => { e.preventDefault(); enviar(texto); }}
      >
        <div className="glass flex items-end gap-2 rounded-2xl px-3 py-2">
          <textarea
            ref={caja}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(texto); } }}
            rows={1}
            placeholder={empresa ? `Pregunta sobre ${empresa.replace("COMP_", "Sociedad ")} o sobre la cartera…` : "Pregunta sobre la cartera o sobre cualquier empresa…"}
            aria-label="Mensaje para el asistente"
            className="max-h-40 min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2 text-[13.5px] leading-snug outline-none placeholder:text-[var(--color-ink-4)]"
            onInput={(e) => { const t = e.currentTarget; t.style.height = "auto"; t.style.height = `${Math.min(t.scrollHeight, 160)}px`; }}
          />
          {ocupado ? (
            <button type="button" onClick={() => stop()} className="pildora h-10 flex-none" aria-label="Detener">Detener</button>
          ) : (
            <button type="submit" disabled={!texto.trim()} aria-label="Enviar"
              className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-white text-[#0d0416] transition-opacity disabled:opacity-30">
              <Icono width="17" height="17" trazo={<><path d="M12 19V5" /><path d="m5 12 7-7 7 7" /></>} />
            </button>
          )}
        </div>
        <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-[var(--color-ink-4)]">
          <span>Responde con datos del motor X Ray. Comprueba las cifras antes de decidir.</span>
          {!vacio && (
            <button type="button" className="hover:text-[var(--color-ink-2)] hover:underline" onClick={() => { stop(); setMessages([]); clearError(); }}>
              Nueva conversación
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

function Bienvenida({ empresa, onElegir }: { empresa: string | null; onElegir: (t: string) => void }) {
  const lista = sugerencias(empresa);
  return (
    <div className="mx-auto flex h-full max-w-[760px] flex-col items-center justify-center px-2 py-10 text-center">
      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl text-[var(--color-purple)]" style={{ background: "rgba(176,131,232,.14)" }}>
        <Icono width="24" height="24" trazo={CHISPA} />
      </span>
      <h2 className="text-[20px] font-semibold tracking-tight">Pregunta a la cartera</h2>
      <p className="mt-1.5 max-w-md text-[12.5px] leading-relaxed text-[var(--color-ink-3)]">
        El asistente consulta el motor X Ray, la cartera y cada empresa, y te enseña lo que encuentra con los mismos gráficos que el resto de la aplicación.
      </p>
      <div className="mt-6 grid w-full gap-2 sm:grid-cols-2">
        {lista.map((s) => (
          <button key={s} type="button" onClick={() => onElegir(s)}
            className="fila px-4 py-3 text-left text-[12.5px] leading-snug text-[var(--color-ink-2)] hover:bg-[rgba(255,255,255,.09)] hover:text-[var(--color-ink)]">
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function Mensaje({ m }: { m: UIMessage }) {
  if (m.role === "user") {
    const texto = m.parts.filter((p) => p.type === "text").map((p) => (p as { text: string }).text).join("\n");
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md px-4 py-2.5 text-[13.5px] leading-relaxed" style={{ background: "rgba(176,131,232,.16)", border: "1px solid rgba(176,131,232,.22)" }}>
          {texto}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-3">
      <span className="mt-1 flex h-7 w-7 flex-none items-center justify-center rounded-full text-[var(--color-purple)]" style={{ background: "rgba(176,131,232,.14)" }}>
        <Icono width="15" height="15" trazo={CHISPA} />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        {m.parts.map((p, i) => {
          if (p.type === "text") return p.text.trim() ? <Markdown key={i} texto={p.text} /> : null;
          if (isToolUIPart(p)) {
            const nombre = getToolName(p);
            if (p.state === "output-available") return <Widget key={p.toolCallId} herramienta={nombre} output={p.output} input={p.input} />;
            if (p.state === "output-error") {
              return (
                <div key={p.toolCallId} className="fila px-4 py-3 text-[12px] text-[var(--color-warm)]">
                  {nombre.replace(/_/g, " ")}: {p.errorText ?? "la herramienta ha fallado"}
                </div>
              );
            }
            return <WidgetCargando key={p.toolCallId} herramienta={nombre} />;
          }
          return null;   // step-start, reasoning y demás no se pintan
        })}
      </div>
    </div>
  );
}

function Markdown({ texto }: { texto: string }) {
  return (
    <div className="prosa text-[13.5px] leading-relaxed text-[var(--color-ink-2)]">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-2.5 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="mb-2.5 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2.5 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-[var(--color-ink)]">{children}</strong>,
          h1: ({ children }) => <p className="mb-2 text-[15px] font-semibold text-[var(--color-ink)]">{children}</p>,
          h2: ({ children }) => <p className="mb-2 text-[15px] font-semibold text-[var(--color-ink)]">{children}</p>,
          h3: ({ children }) => <p className="mb-2 text-[14px] font-semibold text-[var(--color-ink)]">{children}</p>,
          a: ({ children, href }) => <a href={href} className="text-[var(--color-purple)] underline-offset-2 hover:underline">{children}</a>,
          code: ({ children }) => <code className="rounded bg-[rgba(255,255,255,.08)] px-1 py-0.5 text-[12px]">{children}</code>,
          table: ({ children }) => <div className="mb-2.5 overflow-x-auto"><table className="w-full text-[12px]">{children}</table></div>,
          th: ({ children }) => <th className="border-b border-[var(--color-line)] px-2 py-1 text-left font-medium text-[var(--color-ink-3)]">{children}</th>,
          td: ({ children }) => <td className="tnum border-b border-[var(--color-line)] px-2 py-1">{children}</td>,
        }}
      >
        {texto}
      </ReactMarkdown>
    </div>
  );
}

function mensajeError(e: Error): string {
  // El route handler contesta JSON con `error` antes de abrir el stream.
  try {
    const j = JSON.parse(e.message);
    if (j && typeof j.error === "string") return j.error;
  } catch {}
  return e.message || "El asistente no ha podido responder.";
}
