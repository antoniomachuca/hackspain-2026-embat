# `video/` · Presenting X-Ray

Vídeo de producto en horizontal (1920×1080, 30 fps, ~62 s) hecho con
[Remotion](https://remotion.dev). No es una maqueta del front: **es el front**.
Los componentes de [`front/`](../front) se ejecutan dentro de la composición con
su CSS, sus tokens y sus datos, y la cámara se limita a escalar y desplazar. Lo
que se ve en el vídeo es lo que se ve en la app.

## Cómo se usa

```bash
cd video
npm install
npm run dev              # estudio interactivo, con scrub por frames
npm run render           # → out/xray-presentacion.mp4
npm run render:rapido    # borrador a media resolución, para iterar
npm run medir            # re-mide las coordenadas de cámara
```

## Qué cuenta

Los tres actos son los tres del deck (`slides/producto-maestro.html`), que a su
vez son los tres factores por los que se juzga el reto:

| Acto | Factor | Qué enseña |
|---|---|---|
| **01 · El motor** | Algoritmo y solución técnica | Anillo del score, trayectoria con proyección y mediana del cuartil, alerta temprana, desglose aditivo |
| **02 · Las palancas** | Producto y usabilidad | El ranking automático de las ocho, **eliges una y la proyección se mueve**, el simulador recomputando, la frase y el dossier |
| **03 · El negocio** | Monetización | Precio por sociedad, ARR estimado y retorno de una sola palanca |

El plano central del acto 2 es el scroll que va de la lista de palancas al
gráfico mientras la proyección se desplaza: ese movimiento es el que cuenta la
causa. Un corte diría lo mismo con palabras; el scroll lo enseña.

Las cifras del acto 2 **no están escritas a mano**: salen de `simular()` y de
`proyeccionCentral()`, las mismas funciones que alimentan la pantalla, así que
un rótulo no puede desmentir al dibujo. Las del acto 3 son las del deck, con su
pie de estimación.

### Lo único que el vídeo enseña y la app todavía no hace

La capa `palanca` de `componentes/prevision.tsx`: elegir una palanca y ver
desplazarse la proyección. Las dos mitades existen por separado en el front
—`recomendar()` ya simula las ocho y las ordena, `Prevision` ya proyecta— pero
nadie las ha enlazado. El cálculo del vídeo es honesto (el delta sale de
`simular()`), pero **si alguien abre la app no lo va a encontrar**. En cuanto
el front lo enlace, esa capa se sube tal cual y deja de ser del vídeo.

## Cómo está montado

```
src/
  styles.css              copia de front/app/globals.css
  app/                    el front, con lo mínimo cambiado
    lib/                  data.ts y format.ts, copia literal
    componentes/          los de front/components
    pantallas/            page.tsx y simulador.tsx, con el estado sacado a props
  video/
    Pantalla.tsx          la app + la cámara (escala y desplaza, no recompone)
    plano.ts              claves de cámara e interpolación
    Rotulo.tsx            rótulos, marca y viñeta
    Medida.tsx            andamio para medir coordenadas (no entra en el vídeo)
    escenas/              apertura, cortinillas, los tres actos y el cierre
    XRay.tsx              el montaje y las duraciones
```

### Lo que hubo que cambiar del front, y por qué

Todo obligado por que un render es **una foto por fotograma**:

1. **`next/link` → `componentes/enlace.tsx`.** Sigue emitiendo un `<a>`: media
   hoja del CSS cuelga de selectores como `.rail a .tip`, y con un `<span>` el
   panel lateral enseña sus tooltips.
2. **`usePathname()` y el `useState` del panel → props.** No hay router ni
   `localStorage`.
3. **`app/page.tsx` es `async` y consulta al motor; aquí se usa la vía de
   demostración**, que es a la que cae el front cuando el motor no responde y
   la única que deja todos los paneles completos (ver más abajo).
4. **Las animaciones y transiciones CSS están desactivadas** dentro de
   `.app-fondo`: van por reloj y saldrían congeladas en un punto arbitrario.
5. **Los gráficos de recharts van sin `ResponsiveContainer` y sin su
   animación.** El contenedor mide con un `ResizeObserver` que llega tarde y
   deja el primer fotograma en blanco; el ancho se pasa a mano, que además es
   constante en todo el vídeo.

### Por qué se graba con datos de demostración

Con el motor levantado, `front/lib/motor.ts` deja `dso`, `dpo`, `diasCaja` y
`utilizacionLinea` a `0` (marcados FALTA), no rellena `peer` ni `reparto`, y
`front/app/page.tsx` pide las recomendaciones con
`empresa(MI_EMPRESA) ?? EMPRESAS_CON_SCORE[1]` — y `COMP_0773` no está en los
datos de demostración, así que las palancas y el grupo salen de otra empresa.
En cámara eso son cuatro ceros, una tarjeta de grupo vacía y un gráfico sin la
línea del cuartil. La vía de demostración es la que enseña el producto entero.

El panel lateral dice «Motor v1.0 · datos de demostración» en su pie, igual que
en la app, así que el vídeo no finge lo contrario.

### Si cambia el layout del front

Las coordenadas de cámara están medidas sobre un render de la pantalla entera:

```bash
npm run medir     # → out/medida-resumen.png y out/medida-escenarios.png
```

Son las pantallas sin recortar, a 1920 de ancho. Se miden ahí las cajas y se
actualizan las constantes de `escenas/ActoMotor.tsx` y `escenas/ActoPalancas.tsx`.
Un encuadre es `{x, y, w}` en coordenadas de la app; el alto sale solo, porque
la cámara no deforma. Con `scroll` se sube la página por detrás del panel
lateral, que es `sticky` igual que en la app.

### El ritmo

Tres reglas, y de ahí sale el ritmo sin que haya que elegir entre leer el
rótulo y mirar la app:

1. **El rótulo entra cuando la cámara ya ha parado**, nunca durante el viaje.
   Si el texto llega con el plano en movimiento hay que elegir, y se pierden
   las dos cosas.
2. **La ventana de cada rótulo la calcula `rotulo()`** a partir de sus
   palabras, con un suelo de segundo y medio de lectura limpia. No se ajusta a
   ojo.
3. **Ningún viaje arranca hasta que el rótulo anterior se ha ido** (`finDe`).
   Los beats se encadenan en código, así que cambiar un texto reajusta solo
   todo lo que viene detrás.

Dos planos van **sin rótulo a propósito**: el desplazamiento de la proyección
en el acto 2 —es lo único que hay que mirar en todo el vídeo, y el texto llega
antes y después, nunca encima— y el primer plano del anillo, donde el número
contando ya es el contenido.

La pantalla se llena en cascada durante el plano de apertura, no panel a panel
en su propio beat: así el plano general no enseña tres tarjetas vacías.

`TIEMPOS`, en `video/XRay.tsx`, tiene las duraciones. Las de los dos actos de
pantalla **no se escriben a mano**: salen de encadenar sus beats.

### Revisar el ritmo acto por acto

Cada acto está registrado como composición propia, así que en el estudio se
puede repasar uno sin recorrer el vídeo entero:

```
npm run dev     # y elegir Acto1-Motor, Acto2-Palancas, Acto3-Negocio…
```

### Skills oficiales de Remotion

El proyecto tiene instalado el [plugin oficial de
Remotion](https://www.remotion.dev/docs/ai/claude-code-plugin) para Claude
Code (`claude plugin install remotion@remotion`). De ahí salen dos cosas que
usa este montaje: `TransitionSeries` con `fade()` para encadenar escenas —los
frames de la transición se descuentan del total en vez de sumarse— y registrar
cada escena como composición suelta.
