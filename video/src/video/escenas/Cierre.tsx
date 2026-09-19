import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Isotipo} from '../../app/componentes/isotipo';
import {esperarFuentes} from '../fuentes';
import {tramo} from '../plano';

/** El cierre del deck, palabra por palabra. */
export const Cierre: React.FC = () => {
  esperarFuentes();
  const f = useCurrentFrame();

  const marca = tramo(f, 3, 27);
  const frase = tramo(f, 22, 55);
  const pie = tramo(f, 69, 98);

  return (
    <AbsoluteFill className="app-fondo" style={{alignItems: 'center', justifyContent: 'center'}}>
      <div style={{textAlign: 'center'}}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 20,
            opacity: marca,
            transform: `scale(${0.94 + marca * 0.06})`,
          }}
        >
          <Isotipo size={52} />
          <span style={{fontSize: 84, fontWeight: 600, letterSpacing: '-.04em', color: '#fff'}}>
            X-Ray
          </span>
        </div>

        <p
          style={{
            margin: '44px auto 0',
            maxWidth: 1260,
            fontSize: 52,
            lineHeight: 1.22,
            fontWeight: 400,
            letterSpacing: '-.02em',
            color: '#d2d2db',
            opacity: frase,
            transform: `translateY(${(1 - frase) * 18}px)`,
          }}
        >
          El departamento de Embat
          <br />
          <em style={{fontStyle: 'normal', color: '#b083e8', fontWeight: 500}}>
            que te vende tu plan de acción.
          </em>
        </p>

        <p
          className="mono"
          style={{
            margin: '76px 0 0',
            fontSize: 17,
            letterSpacing: '.24em',
            textTransform: 'uppercase',
            color: '#696d80',
            opacity: pie,
          }}
        >
          HackSpain 2026 · Reto Embat · 250 grupos · 24 meses
        </p>
      </div>
    </AbsoluteFill>
  );
};
