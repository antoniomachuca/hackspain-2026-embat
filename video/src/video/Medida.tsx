// Andamio de medición: las pantallas enteras, sin recortar, para leer dónde
// cae cada panel y escribir las coordenadas de cámara con un número exacto
// en vez de a ojo. No entra en el vídeo.
import {AbsoluteFill} from 'remotion';
import {Shell} from '../app/componentes/shell';
import {Resumen} from '../app/pantallas/Resumen';
import {Escenarios} from '../app/pantallas/Escenarios';
import {esperarFuentes} from './fuentes';

const Lienzo: React.FC<{alto: number; ruta: string; children: React.ReactNode}> = ({alto, ruta, children}) => {
  esperarFuentes();
  return (
    <AbsoluteFill style={{background: '#08070c'}}>
      <div className="app-fondo" style={{width: 1920, minHeight: alto}}>
        <Shell ruta={ruta}>{children}</Shell>
      </div>
    </AbsoluteFill>
  );
};

export const MedidaResumen: React.FC = () => (
  <Lienzo alto={2150} ruta="/">
    <Resumen p={{anillo: 1, prevision: 1, waterfall: 1, filas: 1}} />
  </Lienzo>
);

export const MedidaEscenarios: React.FC = () => (
  <Lienzo alto={1500} ruta="/comparar">
    <Escenarios palancaId="bajar_linea" valor={38} generado />
  </Lienzo>
);
