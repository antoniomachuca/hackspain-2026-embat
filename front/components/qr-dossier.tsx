"use client";
import { useEffect, useState } from "react";
import { Modal } from "@/components/modal";
import { Boton } from "@/components/ui";
import { urlPublica } from "@/lib/publico";

/**
 * QR de la ficha para la demo: el proyector enseña el código, el jurado
 * abre la misma empresa en el teléfono.
 */
export function QrDossier({ ruta, nombre }: { ruta: string; nombre: string }) {
  const [abierto, setAbierto] = useState(false);
  const [url, setUrl] = useState("");
  const [img, setImg] = useState("");
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    setUrl(urlPublica(ruta, window.location.origin));
  }, [ruta]);

  useEffect(() => {
    if (!abierto || !url) return;
    let cancel = false;
    import("qrcode").then((mod) => {
      const QR = mod.default ?? mod;
      return QR.toDataURL(url, {
        width: 560,
        margin: 2,
        errorCorrectionLevel: "M",
        color: { dark: "#120d1d", light: "#ffffff" },
      });
    }).then((data) => { if (!cancel) setImg(data); }).catch(() => {});
    return () => { cancel = true; };
  }, [abierto, url]);

  const copiar = async () => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopiado(true);
      window.setTimeout(() => setCopiado(false), 1600);
    } catch {}
  };

  return (
    <>
      <Boton tono="plano" onClick={() => setAbierto(true)}>Compartir</Boton>
      <Modal
        abierto={abierto}
        onCerrar={() => { setAbierto(false); setCopiado(false); }}
        compacto
        titulo="Abrir en el móvil"
        sub={`La ficha de ${nombre}, al día.`}
      >
        <div className="flex flex-col items-center px-6 pb-6 pt-4 sm:px-7">
          <div
            className="rounded-[18px] bg-white p-3 shadow-[0_8px_28px_rgba(0,0,0,.35)]"
            style={{ outline: "1px solid oklch(0 0 0 / 0.1)" }}
          >
            {img ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={img} alt={`Código QR a ${url}`} width={220} height={220} className="block h-[220px] w-[220px]" />
            ) : (
              <div className="h-[220px] w-[220px] animate-pulse rounded-lg bg-[#eee]" />
            )}
          </div>
          <p className="mt-4 max-w-[260px] truncate text-center text-[11.5px] text-[var(--color-ink-4)]" title={url}>
            {url || "…"}
          </p>
          <button
            type="button"
            onClick={copiar}
            className="pildora mt-3 h-9 active:scale-[0.96]"
          >
            {copiado ? "Copiado" : "Copiar enlace"}
          </button>
        </div>
      </Modal>
    </>
  );
}
