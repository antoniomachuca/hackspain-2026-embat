import {Encuadre, mezclar} from './Pantalla';

/**
 * Un plano se describe con claves: en el frame `f`, la cámara mira `enc` con
 * la página desplazada `scroll`. Entre dos claves se interpola; con dos claves
 * iguales seguidas, el plano se sostiene. Es la misma idea que una timeline de
 * edición, y evita repartir `interpolate` por todo el componente.
 */
export type Clave = {f: number; enc: Encuadre; scroll: number};

/** Suavizado en las dos puntas: la cámara arranca y frena, nunca da un tirón. */
const suave = (t: number) => t * t * (3 - 2 * t);

export function planoEn(frame: number, claves: Clave[]): {enc: Encuadre; scroll: number} {
  if (frame <= claves[0].f) return {enc: claves[0].enc, scroll: claves[0].scroll};
  const ultima = claves[claves.length - 1];
  if (frame >= ultima.f) return {enc: ultima.enc, scroll: ultima.scroll};

  let i = 0;
  while (i < claves.length - 2 && claves[i + 1].f <= frame) i++;
  const a = claves[i];
  const b = claves[i + 1];
  const t = suave((frame - a.f) / (b.f - a.f));
  return {
    enc: mezclar(a.enc, b.enc, t),
    scroll: a.scroll + (b.scroll - a.scroll) * t,
  };
}

/**
 * Cuántos frames tarda el rótulo en aparecer después de que la cámara pare.
 * No entra durante el viaje: si el texto llega mientras el plano se mueve,
 * hay que elegir entre leer o mirar la app, y se pierden las dos cosas.
 */
export const ESPERA_ROTULO = 7;

/**
 * Ventana de un rótulo a partir del frame en que la cámara se queda quieta.
 * La entrada y la salida se comen unos 20 frames entre las dos, así que a la
 * lectura se le suma ese margen. El suelo de 44 frames —segundo y medio de
 * lectura limpia— es lo que cuesta saltar del texto a la pantalla y volver;
 * por debajo, un rótulo corto se lee, pero ya no da tiempo a mirar lo que
 * está señalando.
 */
export function rotulo(paraF: number, palabras: number) {
  const lectura = Math.max(44, Math.round(palabras * 3.4));
  return {entra: paraF + ESPERA_ROTULO, sale: paraF + ESPERA_ROTULO + lectura + 20};
}

/** Frames que tarda un rótulo en desvanecerse. Tiene que coincidir con el
 *  desvanecido de `useAparicion` en `Rotulo.tsx`. */
export const SALIDA_ROTULO = 12;

/**
 * Frame en el que el rótulo ya no está en pantalla. Es el que manda cuándo
 * puede arrancar el siguiente movimiento de cámara: encadenando los beats con
 * esto en vez de a mano, un rótulo no puede quedarse encima de un viaje.
 */
export const finDe = (r: {sale: number}) => r.sale + SALIDA_ROTULO;

/** Progreso 0→1 entre dos frames, con las dos puntas suavizadas. */
export function tramo(frame: number, desde: number, hasta: number) {
  if (frame <= desde) return 0;
  if (frame >= hasta) return 1;
  return suave((frame - desde) / (hasta - desde));
}

/** Igual, pero con salida lineal: para contadores y barridos, donde el
 *  frenazo final del suavizado se lee como un error de cálculo. */
export function rampa(frame: number, desde: number, hasta: number) {
  if (frame <= desde) return 0;
  if (frame >= hasta) return 1;
  const t = (frame - desde) / (hasta - desde);
  return 1 - Math.pow(1 - t, 2.2);
}

export {type Encuadre};
