import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {esperarFuentes} from '../fuentes';
import {tramo} from '../plano';

/**
 * Cortinilla de capítulo. Existe para una sola cosa: que quien mira sepa cuál
 * de los tres factores está viendo. Un número, un título y una línea.
 */
export const Capitulo: React.FC<{numero: string; titulo: string; linea: string}> = ({
  numero,
  titulo,
  linea,
}) => {
  esperarFuentes();
  const f = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const entra = tramo(f, 1, 17);
  const sale = 1 - tramo(f, durationInFrames - 11, durationInFrames - 1);
  const barra = tramo(f, 5, 26);

  return (
    <AbsoluteFill className="app-fondo" style={{alignItems: 'center', justifyContent: 'center'}}>
      <div style={{opacity: entra * sale, textAlign: 'center'}}>
        <span
          className="mono"
          style={{
            fontSize: 124,
            fontWeight: 700,
            color: 'transparent',
            WebkitTextStroke: '1.6px rgba(176,131,232,.55)',
            letterSpacing: '.02em',
            display: 'block',
            transform: `translateY(${(1 - entra) * 24}px)`,
          }}
        >
          {numero}
        </span>
        <h2
          style={{
            margin: '14px 0 0',
            fontSize: 96,
            fontWeight: 600,
            letterSpacing: '-.035em',
            color: '#fff',
            transform: `translateY(${(1 - entra) * 14}px)`,
          }}
        >
          {titulo}
        </h2>
        <div
          style={{
            height: 2,
            width: 300 * barra,
            margin: '32px auto 0',
            background: 'linear-gradient(90deg, transparent, #b083e8, transparent)',
          }}
        />
        <p style={{margin: '30px 0 0', fontSize: 30, color: '#afafbb', letterSpacing: '-.01em'}}>
          {linea}
        </p>
      </div>
    </AbsoluteFill>
  );
};
