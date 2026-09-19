import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {esperarFuentes} from '../fuentes';
import {Marca} from '../Rotulo';
import {rampa, tramo} from '../plano';

/**
 * Acto 3 · El negocio. Aquí no hay pantalla que enseñar, así que las cifras
 * se montan con el mismo cristal y los mismos tokens que la app: el vídeo no
 * cambia de idioma visual al hablar de dinero.
 *
 * Las tres cifras son las del deck (`slides/producto-maestro.html`). El pie
 * va en el plano a propósito: son estimaciones sobre la base declarada de
 * Embat, y enseñarlas sin decirlo sería venderlas como medidas.
 */

const CIFRAS = [
  {
    valor: '250 €',
    sufijo: '/mes',
    titulo: 'Por sociedad',
    nota: 'La unidad con la que Embat ya factura.',
  },
  {
    valor: '1,7–4,2',
    sufijo: ' M€',
    titulo: 'ARR sin un logo nuevo',
    nota: '400 grupos, 5,1 sociedades de media.',
  },
  {
    valor: '× 4,7',
    sufijo: '',
    titulo: 'Lo que devuelve una palanca',
    nota: '3.000 € de módulo, 14.000 € de caja.',
  },
];

export const ActoNegocio: React.FC = () => {
  esperarFuentes();
  const f = useCurrentFrame();

  const titulo = tramo(f, 5, 30);
  const foso = tramo(f, 186, 215);
  const pie = tramo(f, 220, 243);
  const salida = 1 - tramo(f, 268, 290);

  return (
    <AbsoluteFill className="app-fondo" style={{alignItems: 'center', justifyContent: 'center'}}>
      <Marca />
      <div style={{width: 1560, opacity: salida}}>
        <p
          className="mono"
          style={{
            margin: 0,
            fontSize: 17,
            letterSpacing: '.22em',
            textTransform: 'uppercase',
            color: '#b083e8',
            opacity: titulo,
          }}
        >
          03 · El negocio
        </p>
        <h2
          style={{
            margin: '20px 0 0',
            fontSize: 62,
            lineHeight: 1.12,
            fontWeight: 600,
            letterSpacing: '-.032em',
            color: '#fff',
            opacity: titulo,
            transform: `translateY(${(1 - titulo) * 20}px)`,
          }}
        >
          Se lo vendemos a la empresa,
          <br />
          <em style={{fontStyle: 'normal', color: '#afafbb', fontWeight: 400}}>
            no al que presta.
          </em>
        </h2>

        <div style={{display: 'flex', gap: 22, marginTop: 66}}>
          {CIFRAS.map((c, i) => {
            const p = tramo(f, 57 + i * 26, 96 + i * 26);
            // El número entra recortado por abajo, como un contador de cinta.
            const sube = rampa(f, 63 + i * 26, 105 + i * 26);
            return (
              <div
                key={c.titulo}
                className="panel"
                style={{
                  flex: 1,
                  padding: '38px 34px 34px',
                  opacity: p,
                  transform: `translateY(${(1 - p) * 26}px)`,
                }}
              >
                <div style={{overflow: 'hidden', height: 92}}>
                  <div style={{transform: `translateY(${(1 - sube) * 92}px)`}}>
                    <span
                      className="tnum"
                      style={{
                        fontSize: 76,
                        fontWeight: 600,
                        lineHeight: '92px',
                        letterSpacing: '-.04em',
                        color: '#fff',
                      }}
                    >
                      {c.valor}
                    </span>
                    <span style={{fontSize: 34, fontWeight: 500, color: '#b083e8'}}>{c.sufijo}</span>
                  </div>
                </div>
                <p style={{margin: '18px 0 0', fontSize: 25, fontWeight: 500, color: '#d2d2db'}}>
                  {c.titulo}
                </p>
                <p style={{margin: '8px 0 0', fontSize: 19, lineHeight: 1.45, color: '#787d96'}}>
                  {c.nota}
                </p>
              </div>
            );
          })}
        </div>

        <p
          style={{
            margin: '52px 0 0',
            fontSize: 30,
            color: '#d2d2db',
            opacity: foso,
            transform: `translateY(${(1 - foso) * 14}px)`,
          }}
        >
          Y el foso: el score se copia ·{' '}
          <strong style={{fontWeight: 500, color: '#b083e8'}}>
            el peer set de 400 grupos, no
          </strong>
        </p>

        <p style={{margin: '26px 0 0', fontSize: 16, color: '#696d80', opacity: pie}}>
          Precio y ARR son una estimación sobre la base de clientes y el ICP que Embat declara.
        </p>
      </div>
    </AbsoluteFill>
  );
};
