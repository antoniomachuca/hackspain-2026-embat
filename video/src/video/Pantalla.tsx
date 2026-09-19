import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {Shell} from '../app/componentes/shell';
import {esperarFuentes} from './fuentes';

/** Lienzo del vídeo. */
export const ANCHO = 1920;
export const ALTO = 1080;

/**
 * Un encuadre es el trozo de la app que tiene que llenar la pantalla:
 * esquina superior izquierda en coordenadas de la app y ancho a cubrir.
 * El alto sale solo, porque la cámara no deforma.
 */
export type Encuadre = {x: number; y: number; w: number};

/** Plano general: la app entera, a tamaño real. */
export const GENERAL: Encuadre = {x: 0, y: 0, w: ANCHO};

/**
 * Interpola entre dos encuadres. El zoom va en escala logarítmica —doblar el
 * aumento cuesta lo mismo al principio que al final— y el desplazamiento se
 * engancha al zoom en vez de al tiempo. Si no, en un zoom largo el encuadre
 * llega al sitio mucho antes que el aumento y el plano parece frenar.
 */
export function mezclar(a: Encuadre, b: Encuadre, t: number): Encuadre {
  const w = Math.exp(interpolate(t, [0, 1], [Math.log(a.w), Math.log(b.w)]));
  const tramo = Math.log(b.w) - Math.log(a.w);
  const p = Math.abs(tramo) < 1e-6 ? t : (Math.log(w) - Math.log(a.w)) / tramo;
  return {x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, w};
}

function transformDe(e: Encuadre) {
  const escala = ANCHO / e.w;
  const alto = ALTO / escala;
  // Con el origen en el centro, `scale(s) translate(t)` lleva el punto p a
  // centro + s·((p − centro) + t). Se despeja t para que el centro del
  // encuadre caiga justo en el centro del lienzo.
  const tx = ANCHO / 2 - (e.x + e.w / 2);
  const ty = ALTO / 2 - (e.y + alto / 2);
  return {
    transform: `scale(${escala}) translate(${tx}px, ${ty}px)`,
    transformOrigin: 'center center' as const,
  };
}

/**
 * La app dentro del vídeo: el mismo `Shell` con su raíl, el mismo fondo de
 * halos morados y el mismo viewport de 1920×1080 que un portátil. Encima, una
 * cámara que solo escala y desplaza —nunca recompone— para que lo que se ve
 * sea la app y no una maqueta suya.
 */
export const Pantalla: React.FC<{
  children: React.ReactNode;
  encuadre?: Encuadre;
  /** Desplazamiento vertical del contenido, en píxeles. El raíl no se mueve,
   *  igual que en la app: es `position: sticky`. */
  scroll?: number;
  ruta?: string;
}> = ({children, encuadre = GENERAL, scroll = 0, ruta = '/'}) => {
  esperarFuentes();
  const {transform, transformOrigin} = transformDe(encuadre);

  return (
    <AbsoluteFill style={{background: '#08070c', overflow: 'hidden'}}>
      <AbsoluteFill style={{transform, transformOrigin}}>
        <div className="app-fondo" style={{width: ANCHO, height: ALTO}}>
          <Shell ruta={ruta}>
            <div style={{transform: `translateY(${-scroll}px)`}}>{children}</div>
          </Shell>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
