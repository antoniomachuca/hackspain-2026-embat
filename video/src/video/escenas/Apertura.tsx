import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Isotipo} from '../../app/componentes/isotipo';
import {esperarFuentes} from '../fuentes';
import {tramo} from '../plano';

const CAPITULOS = [
  ['01', 'El motor'],
  ['02', 'Las palancas'],
  ['03', 'El negocio'],
];

/**
 * La portada. Dice el nombre, la frase del deck y el índice de lo que viene,
 * y se aparta. Todo sobre el mismo fondo de halos que la app, para que el
 * corte al producto no parezca un cambio de marca.
 */
export const Apertura: React.FC = () => {
  esperarFuentes();
  const f = useCurrentFrame();

  const marca = tramo(f, 5, 25);
  const nombre = tramo(f, 12, 35);
  const frase = tramo(f, 35, 60);
  const indice = tramo(f, 67, 90);
  const salida = 1 - tramo(f, 127, 148);

  return (
    <AbsoluteFill className="app-fondo" style={{alignItems: 'center', justifyContent: 'center'}}>
      <div style={{textAlign: 'center', opacity: salida, transform: `scale(${1 + (1 - salida) * 0.03})`}}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            opacity: marca,
            transform: `translateY(${(1 - marca) * 18}px)`,
          }}
        >
          <Isotipo size={30} />
          <span
            className="mono"
            style={{fontSize: 19, letterSpacing: '.3em', textTransform: 'uppercase', color: '#afafbb'}}
          >
            Un departamento dentro de Embat
          </span>
        </div>

        <h1
          style={{
            margin: '26px 0 0',
            fontSize: 188,
            lineHeight: 0.94,
            fontWeight: 600,
            letterSpacing: '-.045em',
            color: '#fff',
            opacity: nombre,
            transform: `translateY(${(1 - nombre) * 26}px)`,
          }}
        >
          X-Ray
        </h1>

        <p
          style={{
            margin: '30px auto 0',
            maxWidth: 1180,
            fontSize: 46,
            lineHeight: 1.26,
            fontWeight: 400,
            color: '#d2d2db',
            letterSpacing: '-.015em',
            opacity: frase,
            transform: `translateY(${(1 - frase) * 20}px)`,
          }}
        >
          No te damos un número.{' '}
          <em style={{fontStyle: 'normal', color: '#b083e8', fontWeight: 500}}>
            Te damos las palancas.
          </em>
        </p>

        <div
          style={{
            marginTop: 74,
            display: 'flex',
            justifyContent: 'center',
            gap: 18,
            opacity: indice,
          }}
        >
          {CAPITULOS.map(([n, t], i) => {
            const p = tramo(f, 67 + i * 7, 90 + i * 7);
            return (
              <div
                key={n}
                className="glass-soft"
                style={{
                  borderRadius: 999,
                  padding: '13px 26px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  opacity: p,
                  transform: `translateY(${(1 - p) * 14}px)`,
                }}
              >
                <span className="mono" style={{fontSize: 17, color: '#b083e8'}}>
                  {n}
                </span>
                <span style={{fontSize: 23, color: '#d2d2db'}}>{t}</span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
