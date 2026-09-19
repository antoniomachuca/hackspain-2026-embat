import {continueRender, delayRender} from 'remotion';

/**
 * General Sans y JetBrains Mono llegan de Fontshare por `@import` en el CSS.
 * Un `@import` no bloquea el render: sin esperar a que la fuente esté lista,
 * los primeros fotogramas salen con la de respaldo y el vídeo cambia de
 * tipografía a mitad de plano. `delayRender` sujeta cada fotograma hasta que
 * el navegador confirma que las tiene.
 */
const CARAS = [
  '400 16px "General Sans"',
  '500 16px "General Sans"',
  '600 16px "General Sans"',
  '700 16px "General Sans"',
  '400 16px "JetBrains Mono"',
  '700 16px "JetBrains Mono"',
];

let promesa: Promise<void> | null = null;

export function esperarFuentes() {
  if (!promesa) {
    promesa = (async () => {
      const espera = delayRender('Cargando General Sans desde Fontshare');
      try {
        await Promise.all(CARAS.map((c) => document.fonts.load(c)));
        await document.fonts.ready;
      } finally {
        continueRender(espera);
      }
    })();
  }
  return promesa;
}
