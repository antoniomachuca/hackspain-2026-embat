import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Resumen} from '../../app/pantallas/Resumen';
import {Pantalla} from '../Pantalla';
import {Marca, Rotulo, Vineta} from '../Rotulo';
import {Clave, finDe, planoEn, rampa, rotulo, tramo} from '../plano';

/**
 * Acto 1 · El motor. Recorre la pantalla de resumen tal y como está en
 * `front/app/page.tsx`: el anillo, la trayectoria con su proyección, la alerta
 * temprana y el desglose aditivo. La cámara no recompone nada — solo se acerca
 * a la parte de la que se está hablando.
 *
 * Cada beat son dos tiempos y en este orden: la cámara viaja (y el dato se
 * anima por el camino, que eso sí se puede solapar), la cámara para, y solo
 * entonces entra el rótulo. Si el texto llega mientras el plano se mueve hay
 * que elegir entre leer o mirar la app, y se pierden las dos cosas. La ventana
 * de cada rótulo la calcula `rotulo()` a partir de sus palabras.
 *
 * Las coordenadas son las de la app a 1920×1080, medidas sobre un render de la
 * pantalla entera. Si cambia el layout del front, se vuelven a medir con
 * `npm run medir`.
 */

export const GENERAL = {x: 0, y: 0, w: 1920};
export const ANILLO = {x: 140, y: 96, w: 620};
export const PREVISION = {x: 600, y: 120, w: 1320};
export const ALERTA = {x: 290, y: 464, w: 1000};
export const DRIVERS = {x: 192, y: 212, w: 1008};
export const PALANCAS = {x: 1002, y: 212, w: 1008};
/** Desplazamiento que deja la fila de tarjetas de abajo a media altura. */
export const SCROLL_ABAJO = 600;

/**
 * Los beats, encadenados: cada movimiento de cámara arranca cuando el rótulo
 * del beat anterior ya se ha ido del todo (`finDe`). Escrito así, y no con
 * números sueltos, un rótulo no se puede quedar encima de un viaje aunque
 * luego se cambie el texto y crezca su ventana de lectura.
 */
const PARA_GENERAL = 36;
const R_GENERAL = rotulo(PARA_GENERAL, 10);

const PARA_ANILLO = finDe(R_GENERAL) + 52;          // el anillo no lleva rótulo
const PARA_PREVISION = PARA_ANILLO + 30 + 58;
const R_PREVISION = rotulo(PARA_PREVISION, 15);

const CORTE_ALERTA = finDe(R_PREVISION);
const R_ALERTA = rotulo(CORTE_ALERTA, 11);

const CORTE_DRIVERS = finDe(R_ALERTA);
const R_DRIVERS = rotulo(CORTE_DRIVERS, 9);

// El último plano es el puente al acto 2: se ven entrar las tres palancas
// recomendadas y se corta. El rótulo lo pone la cortinilla del capítulo.
const CORTE_PALANCAS = finDe(R_DRIVERS);
export const FIN_MOTOR = CORTE_PALANCAS + 51;

const CLAVES: Clave[] = [
  {f: 0, enc: {...GENERAL, w: 2020}, scroll: 0},
  {f: PARA_GENERAL, enc: GENERAL, scroll: 0},
  // Al anillo. El score ya va contando mientras se acerca.
  {f: finDe(R_GENERAL), enc: GENERAL, scroll: 0},
  {f: PARA_ANILLO, enc: ANILLO, scroll: 0},
  // Y a la trayectoria, que se dibuja por el camino.
  {f: PARA_ANILLO + 30, enc: ANILLO, scroll: 0},
  {f: PARA_PREVISION, enc: PREVISION, scroll: 0},
  // Corte seco: dos claves pegadas. Se lee más rápido que una panorámica y,
  // sobre todo, más claro: no hay nada que seguir con la vista.
  {f: CORTE_ALERTA - 1, enc: PREVISION, scroll: 0},
  {f: CORTE_ALERTA, enc: ALERTA, scroll: 0},
  {f: CORTE_DRIVERS - 1, enc: ALERTA, scroll: 0},
  {f: CORTE_DRIVERS, enc: DRIVERS, scroll: SCROLL_ABAJO},
  {f: CORTE_PALANCAS - 1, enc: DRIVERS, scroll: SCROLL_ABAJO},
  {f: CORTE_PALANCAS, enc: PALANCAS, scroll: SCROLL_ABAJO},
  {f: FIN_MOTOR, enc: PALANCAS, scroll: SCROLL_ABAJO},
];

export const ActoMotor: React.FC = () => {
  const f = useCurrentFrame();
  const {enc, scroll} = planoEn(f, CLAVES);

  return (
    <AbsoluteFill>
      <Pantalla encuadre={enc} scroll={scroll} ruta="/">
        <Resumen
          p={{
            // La pantalla se llena en cascada durante el plano general. Antes
            // cada panel se animaba en su propio beat, y eso dejaba el plano
            // de apertura con tres tarjetas vacías: no parecía una app
            // cargando, parecía una app rota. Al llegar el primer primer
            // plano ya está todo puesto.
            anillo: rampa(f, 6, 96),
            prevision: rampa(f, 18, 116),
            waterfall: tramo(f, 34, 128),
            filas: tramo(f, 46, 140),
          }}
        />
      </Pantalla>

      <Vineta fuerza={0.9} />
      <Marca />

      <Rotulo
        etiqueta="01 · El motor"
        frase="Tu salud financiera en un número. Y el número, explicado."
        {...R_GENERAL}
      />
      {/* El anillo no lleva rótulo: el número contando ya es el contenido. */}
      <Rotulo
        etiqueta="Trayectoria"
        frase={<>24 meses de historia, 12 de proyección<br />y la mediana de tu cuartil por detrás.</>}
        {...R_PREVISION}
      />
      <Rotulo
        etiqueta="Anticipación"
        frase="Lo vimos cinco meses antes de que el score lo reflejara."
        color="#e59f5e"
        {...R_ALERTA}
      />
      <Rotulo
        etiqueta="Aditivo por diseño"
        frase="Seis contribuciones, sin aproximaciones. Por eso se puede accionar."
        {...R_DRIVERS}
      />
    </AbsoluteFill>
  );
};
