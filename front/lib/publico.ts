/** Origen público del front, para el QR de la demo. */
export const ORIGEN_DEMO = "https://web-production-27da6.up.railway.app";

export function esOrigenLocal(origen: string): boolean {
  try {
    const host = new URL(origen).hostname;
    return host === "localhost" || host === "127.0.0.1";
  } catch {
    return false;
  }
}

/** En local el QR apunta a Railway; en producción, a la propia origen. */
export function urlPublica(
  ruta: string,
  origenActual?: string,
  origenEnv = process.env.NEXT_PUBLIC_APP_URL,
): string {
  const path = ruta.startsWith("/") ? ruta : `/${ruta}`;
  const env = origenEnv?.replace(/\/$/, "");
  if (env) return `${env}${path}`;
  const actual = origenActual?.replace(/\/$/, "");
  if (actual && !esOrigenLocal(actual)) return `${actual}${path}`;
  return `${ORIGEN_DEMO}${path}`;
}
