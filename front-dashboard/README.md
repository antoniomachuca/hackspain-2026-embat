# X Ray · panel del cliente

Front en Next.js 16 + Tailwind 4. Datos mockeados con la forma del contrato de
`REQUISITOS.md` §B7: al conectar el motor solo cambia `lib/data.ts`.

```bash
npm install
npm run dev     # http://localhost:3000
```

## Enfoque

El producto es **para la empresa cliente**, no para quien la mira desde fuera:
la portada es su propio score y nunca se identifica a otra empresa. La única
comparativa es el percentil contra el conjunto anónimo de 250 grupos.

## Pantallas

| Ruta | Qué es |
| --- | --- |
| `/` | Resumen del cliente: anillo de score, histórico + proyección a 12 meses, aviso con anticipación, waterfall de los seis factores, palancas y su grupo |
| `/empresa/[id]` | Ficha con anillo, trayectoria, drivers y recomendaciones |
| `/empresa/[id]/drivers` | Descomposición aditiva exacta, factor a factor |
| `/empresa/[id]/escenarios` | Simulador de las ocho palancas y generación de documento |
| `/grupo/[id]` | Consolidado, penalización por contagio y filiales |
| `/comparar` | Split-screen bureau vs X Ray (REQ-B11.1, pieza de pitch) |

## Decisiones de diseño

- **Paleta oficial de Embat** extraída de su CSS: tinta `#050b2c`, morados
  `#b083e8` / `#a154e9` / `#c357ec` / `#7b32c0`, y los semánticos inversos
  `#80efa2`, `#dfb631`, `#e5775b`. Isotipo tomado de su `favicon.svg`.
- **Sin rojo/verde como único canal**: cada valor lleva flecha, signo o texto.
  El eje de riesgo es una rampa cálido → morado.
- **Nivel, momentum y estado van separados**, porque el reto no prioriza ninguno.
- **Seis contribuciones** que suman exactamente el score, sin SHAP ni LIME.
- Las empresas con menos de 12 meses **no publican score**: se explica por qué.

## Pendiente

- Conectar `lib/data.ts` a la API real cuando exista `/score` y `/simulate`.
- Pasaporte QR (REQ-B11.2) y modo offline con fixtures (REQ-B7.2).
- Motivo de rechazo por palanca (REQ-B8.1).
- La proyección extiende la inercia observada; sustituir por la del motor si la hay.
