import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Resumen, EMPRESA_DEMO, RECOS} from '../../app/pantallas/Resumen';
import {Escenarios} from '../../app/pantallas/Escenarios';
import {proyeccionCentral} from '../../app/componentes/prevision';
import {simular, PALANCAS as CATALOGO_PALANCAS} from '../../app/lib/data';
import {eur, num} from '../../app/lib/format';
import {Pantalla} from '../Pantalla';
import {Marca, Rotulo, Vineta} from '../Rotulo';
import {Clave, finDe, planoEn, rampa, rotulo, tramo} from '../plano';
import {PALANCAS as ENC_PALANCAS, PREVISION as ENC_PREVISION, SCROLL_ABAJO} from './ActoMotor';

/**
 * Acto 2 · Las palancas. Es el corazón del vídeo y va en dos mitades:
 *
 *   1. La app ya ha simulado las ocho del catálogo y deja arriba las que más
 *      mueven. Se elige una y la página sube sola de la lista al gráfico
 *      mientras la proyección se desplaza. Ese scroll es el que cuenta la
 *      causa: pulsas abajo, reacciona arriba. Un corte no lo diría.
 *   2. El simulador, para enseñar que detrás no hay una regla de tres: el
 *      mando se mueve y las cuatro cifras se recalculan a cada fotograma.
 *
 * El plano del desplazamiento va SIN rótulo a propósito. Es lo único que hay
 * que mirar en todo el vídeo, y el texto llega antes —prometiendo lo que va a
 * pasar— y después —con el número—, nunca encima.
 *
 * Toda la aritmética sale de `simular()` y de `proyeccionCentral()`, las
 * mismas que alimentan la pantalla, así que los rótulos no pueden desmentir
 * al dibujo: leen del mismo sitio.
 */

/** Una sola palanca de punta a punta del acto: la que recomienda el motor.
 *  Es además la única que enciende los cuatro indicadores y deja coherente
 *  el borrador de la propuesta; con otra, el documento habla de días que no
 *  vienen a cuento. */
const PALANCA = 'reducir_dso';
const RECO = RECOS.find((r) => r.palanca.id === PALANCA)!;
/** Hasta dónde se empuja el mando en el simulador, más allá de lo sugerido. */
const TOPE = 24;

// ── Encuadres sobre la pantalla de escenarios ─────────────────────────
const CATALOGO = {x: 280, y: 90, w: 980};
const MANDO = {x: 630, y: 85, w: 1270};
const DOCUMENTO = {x: 630, y: 175, w: 1270};

/**
 * Los beats, encadenados con `finDe`: ningún viaje de cámara arranca hasta
 * que el rótulo anterior se ha ido. Los dos planos sin rótulo —el
 * desplazamiento de la proyección y la tarjeta «La frase», que ya cabe dentro
 * del encuadre del mando— son deliberados: ahí hay que mirar, no leer.
 */
const R_LISTA = rotulo(0, 13);
const R_PROMESA = rotulo(finDe(R_LISTA), 9);

/** El plano: 96 frames de scroll y desplazamiento de la proyección, sin texto. */
const MUEVE_WHATIF = finDe(R_PROMESA);
const PARA_RESULTADO = MUEVE_WHATIF + 96;
const R_RESULTADO = rotulo(PARA_RESULTADO, 8);

const CORTE_CATALOGO = finDe(R_RESULTADO);
const R_CATALOGO = rotulo(CORTE_CATALOGO, 5);

const CORTE_MANDO = finDe(R_CATALOGO);
const MANDO_DESDE = CORTE_MANDO + 10;
const MANDO_HASTA = MANDO_DESDE + 72;
const R_MANDO = rotulo(MANDO_HASTA, 17);

const CORTE_DOCUMENTO = finDe(R_MANDO);
const R_DOCUMENTO = rotulo(CORTE_DOCUMENTO, 12);
export const FIN_PALANCAS = finDe(R_DOCUMENTO) + 6;

/** A partir de aquí la pantalla ya no es el resumen, sino el simulador. */
const CORTE = CORTE_CATALOGO;

const CLAVES: Clave[] = [
  // La lista de palancas, ya ordenada. La cámara llega quieta del capítulo.
  {f: 0, enc: ENC_PALANCAS, scroll: SCROLL_ABAJO},
  {f: MUEVE_WHATIF, enc: ENC_PALANCAS, scroll: SCROLL_ABAJO},
  // El plano: la página sube al gráfico mientras la proyección se desplaza.
  {f: PARA_RESULTADO, enc: ENC_PREVISION, scroll: 0},
  {f: CORTE - 1, enc: ENC_PREVISION, scroll: 0},
  // Corte al simulador.
  {f: CORTE, enc: CATALOGO, scroll: 0},
  {f: CORTE_MANDO - 1, enc: CATALOGO, scroll: 0},
  {f: CORTE_MANDO, enc: MANDO, scroll: 0},
  {f: CORTE_DOCUMENTO - 1, enc: MANDO, scroll: 0},
  {f: CORTE_DOCUMENTO, enc: DOCUMENTO, scroll: 250},
  {f: FIN_PALANCAS, enc: DOCUMENTO, scroll: 250},
];

export const ActoPalancas: React.FC = () => {
  const f = useCurrentFrame();
  const {enc, scroll} = planoEn(f, CLAVES);

  const mezcla = rampa(f, MUEVE_WHATIF + 6, PARA_RESULTADO - 5);
  const e = EMPRESA_DEMO;
  const base = proyeccionCentral(e.score, e.momentum);
  const conPalanca = proyeccionCentral(e.score, e.momentum, RECO.deltaScore);

  // El mando se mueve con la cámara ya quieta, y termina antes de que entre
  // el rótulo que canta las cifras: primero se ve, después se lee.
  const valor = Math.max(1, Math.round(1 + (TOPE - 1) * rampa(f, MANDO_DESDE, MANDO_HASTA)));
  const sim = simular(e, PALANCA, TOPE);

  return (
    <AbsoluteFill>
      {f < CORTE ? (
        <Pantalla encuadre={enc} scroll={scroll} ruta="/">
          <Resumen
            p={{
              anillo: 1,
              prevision: 1,
              waterfall: 1,
              filas: 1,
              destacada: tramo(f, 18, 34) > 0.5 ? PALANCA : undefined,
              palanca: {nombre: RECO.palanca.nombre, delta: RECO.deltaScore, mezcla},
            }}
          />
        </Pantalla>
      ) : (
        <Pantalla encuadre={enc} scroll={scroll} ruta="/comparar">
          <Escenarios palancaId={PALANCA} valor={valor} generado={f >= CORTE_DOCUMENTO - 12} />
        </Pantalla>
      )}

      <Vineta fuerza={0.9} />
      <Marca />

      <Rotulo
        etiqueta="02 · Las palancas"
        frase={<>Ya ha simulado las {CATALOGO_PALANCAS.length} del catálogo.<br />Arriba deja las que más mueven.</>}
        {...R_LISTA}
      />
      <Rotulo
        etiqueta="Eliges una"
        frase="Y tu proyección de score se mueve con ella."
        color="#80efa2"
        {...R_PROMESA}
      />
      {/* Aquí, nada. El desplazamiento se mira. */}
      <Rotulo
        etiqueta={`${RECO.palanca.nombre} · ${RECO.valor} ${RECO.palanca.unidad}`}
        frase={<>El escenario central pasa de {num(base)} a {num(conPalanca)}.</>}
        color="#80efa2"
        {...R_RESULTADO}
      />
      <Rotulo
        etiqueta="El catálogo completo"
        frase="Cobros, deuda, gasto, concentración."
        {...R_CATALOGO}
      />
      <Rotulo
        etiqueta="Contrafactual, no extrapolación"
        frase={
          <>
            Mueves el mando y el motor vuelve a correr entero:{' '}
            <span style={{whiteSpace: 'nowrap'}}>
              +{num(sim.deltaScore)} pts · {eur(sim.cajaLiberada)} · {eur(sim.eurAnio)}/año
            </span>
          </>
        }
        {...R_MANDO}
      />
      <Rotulo
        etiqueta="El pack bancario"
        frase={<>Siete bancos de media.<br />El dossier se monta una vez, no siete.</>}
        {...R_DOCUMENTO}
      />
    </AbsoluteFill>
  );
};
