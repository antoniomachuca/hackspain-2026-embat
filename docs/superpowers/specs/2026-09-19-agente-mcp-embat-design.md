# Asistente de cartera con MCP · diseño

Fecha: 19-sep-2026. Rama: `feat/agente-mcp`.

## Qué es

Una quinta entrada en el sidebar del modo Embat, **Asistente** (`/agente`): un chat
donde un analista de Embat pregunta en lenguaje natural sobre la cartera o sobre
una empresa concreta. El agente usa un **servidor MCP** que expone el núcleo de
X Ray (motor, simuladores, datos de las 1.286 empresas) y sus respuestas
intercalan **widgets** hechos con los mismos componentes que el resto de la
aplicación.

Objetivo: la demo ante el jurado del 20-sep-2026. Pesa en el factor 2 del jurado
(producto y usabilidad) y abre una lectura de monetización (los datos de Embat
como herramienta conversacional). Prima que funcione y luzca sobre que escale.

## Decisiones tomadas en la conversación

| Pregunta | Decisión |
| --- | --- |
| Proveedor de LLM | OpenAI (Hugo tiene clave). Modelo por variable `OPENAI_MODEL`, por defecto `gpt-5-mini`. |
| Alcance del MCP | Solo interno, para nuestro agente. No se documenta ni se expone como producto. |
| Enfoque | A: MCP en Python dentro de la API; agente en Next con AI SDK. |
| Widgets | Catálogo cerrado: el modelo elige herramientas, el front decide cómo se ven. Nada de HTML generado. |
| Persistencia | Ninguna. La conversación vive en memoria de la página. |

Enfoques descartados: todo en Python con un protocolo SSE propio (más código de
protocolo que depurar); Responses API de OpenAI con MCP remoto (exige exponer el
MCP en internet y no funciona en local sin túnel).

## Arquitectura

```
navegador ── useChat ──▶ Next /api/agente ── @ai-sdk/mcp ──▶ FastAPI /mcp/ ── ASGI en proceso ──▶ /api/*  ──▶ DuckDB
                          │  streamText (OpenAI)                MCPServer (mcp 2.x)
                          ▼
                    stream de partes: texto · tool-call · tool-result
                          ▼
                    registro de widgets (components/agente/widgets.tsx)
```

### Backend: `backend/mcp_server.py`

- `MCPServer` del paquete `mcp>=2.2` (antes FastMCP), montado en `main.py` en
  `/mcp` con transporte HTTP **sin sesión y respuesta JSON**. El gestor de
  sesiones se arranca en el `lifespan` de la API.
- Cada herramienta llama a la propia API por `httpx.ASGITransport`, sin red:
  misma validación, misma normalización de identificadores, mismos números que
  la app. Los resultados se recortan aquí para no inflar el contexto del modelo.
- Protección contra DNS rebinding desactivada: la API corre detrás del dominio
  público de Railway y del servidor de Next.
- La URL correcta es `/mcp/` con barra final; sin ella Starlette redirige y el
  cliente del AI SDK rechaza redirecciones por defecto.

Herramientas (todas de lectura o cálculo):

| Herramienta | Envuelve | Widget |
| --- | --- | --- |
| `resumen_cartera` | `/api/portfolio` | 4 KPI + Histograma + segmentos |
| `buscar_empresas` | `/api/companies` | Lista de filas (ScoreBadge, Delta, EstadoChip, segmento) |
| `alertas` | `/api/alerts` | Lista de alertas con severidad y driver principal |
| `ficha_empresa` | `/api/companies/{id}` | Anillo + datos + Desglose del score |
| `historia_empresa` | `/history` | Trayectoria |
| `episodios_empresa` | ficha + history | EpisodiosPanel |
| `comparables_empresa` | `/peers` + history | Trayectoria con comparador |
| `facturas_empresa` | `/invoices` | Tabla |
| `grupo` | `/api/groups/{id}` | Cabecera con scores + lista de sociedades |
| `flujos_intragrupo` | `/api/graph/{group}` | Dos tablas: nodos y aristas |
| `que_pasaria_si` | `POST /api/whatif` | Hoy → proyectado + producto recomendado |
| `palancas` | `/api/simulate/rankings` | Lista de palancas con barra de ganancia |
| `simular_palancas` | `POST /api/simulate` | Hoy → proyectado + caja liberada |
| `prevision_estructural` | `/prevision-estructural` + history | Prevision con tres escenarios |

Herramienta sin widget: JSON plegado en un `details`.

### Front

- `app/api/agente/route.ts`: abre un cliente MCP por turno, convierte sus
  herramientas en tools del modelo, `streamText` con `stopWhen: stepCountIs(8)`
  y devuelve `toUIMessageStreamResponse()`. El system prompt explica X Ray,
  estados, bandas, segmentos y cómo trabajar; se le añade el contexto de la
  cartera (corte, totales) leído una vez y cacheado diez minutos, y la empresa
  en foco si viene en el cuerpo. Errores de proveedor se traducen a mensajes
  legibles. Sin `OPENAI_API_KEY` responde 500 con explicación; sin motor, 503.
- `app/agente/page.tsx`: cabecera con corte y empresa en foco; acepta
  `?empresa=COMP_0773`.
- `components/agente/chat.tsx`: `useChat` con `DefaultChatTransport` (cuerpo con
  `empresa`). Pantalla vacía con cuatro preguntas de arranque (tres sobre la
  empresa si hay foco). Burbuja del usuario a la derecha; el agente sin burbuja,
  texto en Markdown (react-markdown) y widgets intercalados en el orden real de
  las partes. Estados: "Pensando…", esqueleto por herramienta en curso, error
  inline con Reintentar, botón Detener, "Nueva conversación".
- `components/agente/widgets.tsx`: registro `nombre de herramienta → componente`.
  `lib/agente.ts`: etiquetas humanas por herramienta, `datosDe(output)`
  (structuredContent o JSON del texto; detecta errores) y las sugerencias.
- `components/shell.tsx`: entrada "Asistente" en el modo Embat; `/agente` cuenta
  como modo Embat.

## Modo empresa (añadido el 20-sep-2026)

La misma conversación, vista desde la empresa que compra X Ray: `/[id]/asistente`,
con la entrada "Asistente" en el sidebar del modo empresa. Reglas:

- **El límite lo impone el servidor, no el prompt.** El cuerpo lleva
  `modo: "empresa"` y `empresa`; el route handler resuelve el grupo con la ficha
  y pasa las herramientas por `lib/agente-alcance.ts` (`acotar`): las de cartera
  (`resumen_cartera`, `buscar_empresas`) desaparecen y en el resto el parámetro
  `empresa` o `grupo` lo sobreescribe el servidor. Aunque el modelo pida otra
  empresa, la herramienta devuelve la del alcance.
- **Prompt propio**: segunda persona, tono de "tu salud financiera", sin
  "clientes", "cartera" ni segmentos Apostar/Vigilar/Acompañar, que son lectura
  interna de Embat. Sugerencias de arranque propias.
- **Widgets**: los mismos. Un contexto (`AlcanceContext`) decide a dónde enlazan
  las filas (`/[id]` en vez de `/embat/[id]`, `/[id]/grupo` en vez de
  `/grupo/[gid]`) y oculta el chip de segmento.
- El grupo sí se ve (score de las sociedades hermanas), porque así se pidió. Si
  algún día una filial no debe ver a sus hermanas, se filtra en `acotar`.
- En la demo no hay login, así que `empresa` viene del cuerpo de la petición. En
  un producto real saldría de la sesión.

## Variables de entorno

| Servicio | Variable | Uso |
| --- | --- | --- |
| web | `OPENAI_API_KEY` | Clave del modelo. Solo servidor de Next. |
| web | `OPENAI_MODEL` | Modelo. Por defecto `gpt-5-mini`. |
| web | `XRAY_API_URL` | Base de la API vista desde el servidor de Next. Si falta, `NEXT_PUBLIC_API_URL`, y si no, `http://127.0.0.1:8000`. |

En local: `front/.env.local` con `OPENAI_API_KEY=...` (está en `.gitignore`).

## Pruebas

- `backend/test_mcp_server.py`: cliente MCP en memoria. Comprueba las catorce
  herramientas, que aceptan identificadores cortos, que `ficha_empresa`,
  `historia_empresa` y `que_pasaria_si` devuelven los mismos números que los
  endpoints REST, el error legible con empresa inexistente y que `/mcp/`
  responde al `initialize` por HTTP.
- Front: sin tests de UI (no hay infraestructura hoy). Se comprueba a mano en la
  demo. `tsc`, `eslint` y `next build` limpios.

## Fuera de alcance

Persistencia de conversaciones, login, exposición pública del MCP, botón
"Preguntar al asistente" en la ficha.
