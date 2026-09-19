import React from 'react';
import {AbsoluteFill} from 'remotion';
import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {Apertura} from './escenas/Apertura';
import {Capitulo} from './escenas/Capitulo';
import {ActoMotor, FIN_MOTOR} from './escenas/ActoMotor';
import {ActoPalancas, FIN_PALANCAS} from './escenas/ActoPalancas';
import {ActoNegocio} from './escenas/ActoNegocio';
import {Cierre} from './escenas/Cierre';

/** Duraciones, en frames a 30 fps. En un solo sitio para poder repasarlas. */
export const TIEMPOS = {
  apertura: 150,
  capitulo: 55,
  // Los dos actos de pantalla se miden solos: encadenan sus beats a partir de
  // las ventanas de lectura de sus rótulos, así que la duración es un
  // resultado, no un número que haya que mantener a mano.
  motor: FIN_MOTOR,
  palancas: FIN_PALANCAS,
  negocio: 295,
  cierre: 135,
};

/** Encadenado entre escenas. `TransitionSeries` lo solapa, así que cada
 *  transición descuenta sus frames del total en vez de sumarlos: se gana
 *  fluidez sin alargar el vídeo. */
const TRANSICION = 14;
const UNIONES = 6;

export const DURACION =
  Object.values(TIEMPOS).reduce((a, b) => a + b, 0) +
  TIEMPOS.capitulo + // la cortinilla aparece dos veces
  -TRANSICION * UNIONES;

const encadenado = (
  <TransitionSeries.Transition
    presentation={fade()}
    timing={linearTiming({durationInFrames: TRANSICION})}
  />
);

/**
 * Presenting X-Ray. Tres actos, los mismos tres que ordenan el deck y los
 * mismos tres factores por los que se juzga el reto: qué hace el motor, qué
 * se le entrega al cliente y quién lo paga.
 */
export const XRay: React.FC = () => (
  <AbsoluteFill style={{background: '#08070c'}}>
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={TIEMPOS.apertura} name="Apertura">
        <Apertura />
      </TransitionSeries.Sequence>
      {encadenado}
      <TransitionSeries.Sequence durationInFrames={TIEMPOS.capitulo} name="01 · El motor">
        <Capitulo numero="01" titulo="El motor" linea="Un score que se puede explicar entero." />
      </TransitionSeries.Sequence>
      {encadenado}
      <TransitionSeries.Sequence durationInFrames={TIEMPOS.motor} name="Acto 1">
        <ActoMotor />
      </TransitionSeries.Sequence>
      {encadenado}
      <TransitionSeries.Sequence durationInFrames={TIEMPOS.capitulo} name="02 · Las palancas">
        <Capitulo numero="02" titulo="Las palancas" linea="Lo que separa un diagnóstico de una receta." />
      </TransitionSeries.Sequence>
      {encadenado}
      <TransitionSeries.Sequence durationInFrames={TIEMPOS.palancas} name="Acto 2">
        <ActoPalancas />
      </TransitionSeries.Sequence>
      {encadenado}
      <TransitionSeries.Sequence durationInFrames={TIEMPOS.negocio} name="Acto 3">
        <ActoNegocio />
      </TransitionSeries.Sequence>
      {encadenado}
      <TransitionSeries.Sequence durationInFrames={TIEMPOS.cierre} name="Cierre">
        <Cierre />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  </AbsoluteFill>
);
