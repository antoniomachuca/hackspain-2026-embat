import {Composition, Folder} from 'remotion';
import './styles.css';
import {XRay, DURACION, TIEMPOS} from './video/XRay';
import {Apertura} from './video/escenas/Apertura';
import {ActoMotor} from './video/escenas/ActoMotor';
import {ActoPalancas} from './video/escenas/ActoPalancas';
import {ActoNegocio} from './video/escenas/ActoNegocio';
import {Cierre} from './video/escenas/Cierre';
import {MedidaResumen, MedidaEscenarios} from './video/Medida';

const HD = {fps: 30, width: 1920, height: 1080} as const;

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="XRay" component={XRay} durationInFrames={DURACION} {...HD} />

    {/* Cada acto suelto, para poder repasar su ritmo sin recorrer el vídeo
        entero. Son las mismas escenas que monta `XRay`, no copias. */}
    <Folder name="Escenas">
      <Composition id="Apertura" component={Apertura} durationInFrames={TIEMPOS.apertura} {...HD} />
      <Composition id="Acto1-Motor" component={ActoMotor} durationInFrames={TIEMPOS.motor} {...HD} />
      <Composition id="Acto2-Palancas" component={ActoPalancas} durationInFrames={TIEMPOS.palancas} {...HD} />
      <Composition id="Acto3-Negocio" component={ActoNegocio} durationInFrames={TIEMPOS.negocio} {...HD} />
      <Composition id="Cierre" component={Cierre} durationInFrames={TIEMPOS.cierre} {...HD} />
    </Folder>

    {/* Andamios de medición: no entran en el vídeo, sirven para leer
        coordenadas cuando cambia el layout del front. */}
    <Folder name="Medicion">
      <Composition id="MedidaResumen" component={MedidaResumen} durationInFrames={1} fps={30} width={1920} height={2150} />
      <Composition id="MedidaEscenarios" component={MedidaEscenarios} durationInFrames={1} fps={30} width={1920} height={1500} />
    </Folder>
  </>
);
