import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Isotipo} from '../app/componentes/isotipo';
import {SALIDA_ROTULO} from './plano';

/** Entrada y salida de un elemento que vive entre dos frames del plano. */
export function useAparicion(entra: number, sale?: number) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const dentro = spring({frame: frame - entra, fps, config: {damping: 200}, durationInFrames: 22});
  const fuera = sale === undefined ? 0 : interpolate(frame, [sale, sale + SALIDA_ROTULO], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  return {t: dentro * (1 - fuera), dentro, fuera};
}

/**
 * El rótulo de abajo a la izquierda: una etiqueta corta y una frase. Es el
 * único texto que se superpone a la app, y por eso dice una sola cosa. El
 * criterio del deck vale igual aquí: si un rótulo no empuja el motor, las
 * palancas o el negocio, sobra.
 */
export const Rotulo: React.FC<{
  etiqueta: string;
  frase: React.ReactNode;
  entra: number;
  sale?: number;
  /** Acento, para la barra vertical y la etiqueta. */
  color?: string;
}> = ({etiqueta, frase, entra, sale, color = '#b083e8'}) => {
  const {t} = useAparicion(entra, sale);
  if (t <= 0.001) return null;

  return (
    <div
      style={{
        position: 'absolute',
        left: 118,
        bottom: 84,
        maxWidth: 1180,
        display: 'flex',
        gap: 22,
        opacity: t,
        transform: `translateY(${(1 - t) * 26}px)`,
      }}
    >
      <div style={{width: 3, borderRadius: 3, background: color, flex: 'none'}} />
      <div>
        <p
          className="mono"
          style={{
            margin: 0,
            fontSize: 17,
            letterSpacing: '.22em',
            textTransform: 'uppercase',
            color,
          }}
        >
          {etiqueta}
        </p>
        <p
          style={{
            margin: '10px 0 0',
            fontSize: 44,
            lineHeight: 1.16,
            fontWeight: 500,
            color: '#fff',
            letterSpacing: '-.015em',
            textShadow: '0 4px 28px rgba(0,0,0,.72)',
          }}
        >
          {frase}
        </p>
      </div>
    </div>
  );
};

/** La marca, fija abajo a la derecha. Ahí la viñeta ya ha oscurecido el
 *  fondo, así que se lee sin caja; arriba chocaba con los controles del
 *  gráfico, que viven en esa misma esquina. */
export const Marca: React.FC<{opacidad?: number}> = ({opacidad = 1}) => (
  <div
    style={{
      position: 'absolute',
      right: 60,
      bottom: 54,
      display: 'flex',
      alignItems: 'center',
      gap: 11,
      opacity: 0.72 * opacidad,
    }}
  >
    <Isotipo size={19} />
    <span style={{fontSize: 19, fontWeight: 600, letterSpacing: '-.01em', color: '#fff'}}>
      X-Ray
    </span>
  </div>
);

/**
 * Viñeta: oscurece los bordes para que el rótulo se lea sobre cualquier
 * parte de la app sin tener que ponerle una caja detrás.
 */
export const Vineta: React.FC<{fuerza?: number}> = ({fuerza = 1}) => (
  <div
    style={{
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      background:
        'radial-gradient(130% 92% at 50% 34%, transparent 42%, rgba(4,3,8,.62) 100%),' +
        'linear-gradient(to top, rgba(4,3,8,.80) 0%, transparent 34%)',
      opacity: fuerza,
    }}
  />
);
