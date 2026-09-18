# Guía de producto — Reto X Ray (Embat · HackSpain 2026)

Investigación sobre la parte de producto: estética, usuario, demo y construcción.

---

## 1. El sistema de diseño real de Embat

Extraído directamente del CSS de embat.io (no de reseñas ni de estimaciones).

### Tipografía
**Haffer SQXH** (`HafferSQXH`), de la fundición Displaay. Solo cargan **dos pesos: 400 y 500**. No usan Inter.

Es tipografía de pago. Alternativas gratuitas con el mismo aire geométrico-neogrotesco:
- **General Sans** o **Switzer** (Fontshare, gratis) — las más parecidas
- **Inter Tight** como último recurso

Lección aplicable: **dos pesos, no cinco**. La contención tipográfica es parte del look.

### Paleta (tokens literales de su CSS)

Modo claro:
| Token | Hex | Uso |
|---|---|---|
| content-primary | `#050b2c` | Texto principal. Azul marino casi negro — su color de tinta |
| content-secondary | `#6e707c` | Texto secundario |
| content-tertiary | `#42444c` | Texto terciario |
| background-primary | `#ffffff` | Fondo |
| background-secondary | `#f3f4f6` | Superficies, hover |
| background-tertiary | `#fbfbfc` | Superficie sutil |
| border-primary | `#e8e8ed` | Bordes |
| border-secondary | `#d2d2db` | Bordes marcados |

Modo oscuro / secciones invertidas:
| Token | Hex |
|---|---|
| inverse-background-primary | `#050b2c` |
| inverse-background-secondary | `#232845` |
| inverse-background-tertiary | `#41465f` |
| inverse-border-primary | `#373c56` |
| inverse-content-primary | `#ffffff` |
| inverse-content-secondary | `#d2d2db` |

Acentos:
| Color | Claro | Invertido | Oscuro |
|---|---|---|---|
| Aguamarina (principal) | `#c5f8fc` | `#5ed3e5` | `#007b93` |
| Rosa | — | `#e05a8a` | `#920036` |
| Morado | `#a154e9` | `#7b32c0` | `#400192` |

**El ADN visual de Embat**: azul marino profundo `#050b2c` + aguamarina + blancos. Si la demo usa esos tres colores y dos pesos de una geométrica, el jurado la verá como suya.

### Estructura de su web
Topbar (no sidebar), hero oscuro a todo el ancho con texto blanco, resto claro. Comunican el producto con **ilustraciones SVG limpias, no capturas de UI**. Destacan métricas en grande como prueba social: "85–90%" de reducción de tareas manuales, "~90%" de auto-conciliación, "10 min → segundos".

---

## 2. El argumento de venta

**El 71% de los responsables financieros rechazaría un sistema de IA que no pueda explicar sus resultados, por preciso que sea.**
https://erp.today/finance-ai-trust-gap-critical-as-explainability-becomes-non-negotiable/

Los equipos financieros pierden **12,9 h/semana** reconstruyendo y validando salidas de IA — el 26% del tiempo que ahorran.

> "Si no puedes explicar un número, no puedes defenderlo, compartirlo ni confiar en él; esa falta de transparencia erosiona la confianza, ralentiza decisiones y devuelve a los equipos a las hojas de cálculo." — Planful

La explicabilidad no es un requisito del reto. Es **la razón de compra**.

Contexto macro (Deloitte CFO Survey 2026): control de caja es prioridad para el 43%; el 51% se centra en mejorar la precisión de la previsión.

---

## 3. Huecos de la competencia (reseñas reales)

- **Kyriba**: "difícil de implementar y muy difícil de personalizar", "el diseño interno es rígido y confuso", "el servicio al cliente no responde", "no enlaza las transacciones de caja con los asientos contables".
- **Trovata**: "el módulo de previsión todavía necesita trabajo", "menos funcionalidades que la competencia".
- **Agicap** (4,4/5, 322 reseñas): elogian facilidad de uso; critican funcionalidades ausentes y falta de personalización.
- **Embat** (4,3/5, solo 7 reseñas): su nota más baja es **soporte, 3,5**; features 4,6. Integraciones bancarias aún en desarrollo.

**Patrón**: el dolor no es la falta de analítica, es la fiabilidad de la integración y la rigidez.

**Hueco no cubierto por nadie**: ninguna reseña de ningún competidor menciona el riesgo de crédito de clientes. Nadie avisa a la pyme de que su mayor cliente se deteriora. Sin validar la disposición a pagar — **preguntárselo a los mentores de Embat en el aula**.

**Ajuste de usuario**: en pymes pequeñas no hay tesorero. La tarea cae en el gerente y la herramienta por defecto sigue siendo Excel. Debe ser usable sin formación financiera.

---

## 4. Cómo presentan el score los productos reales

- **Moody's EDF-X**: score 0-100 (más alto = más riesgo), comparado contra el mismo score 6 meses atrás. Historial del score **junto al de un grupo de comparables** en una línea temporal. Además una **vista de cuadrantes** (2 ejes) para ver cómo una empresa se mueve entre cubos de alerta y situar toda la cartera a la vez.
- **D&B Paydex**: 0-100, siendo 0-49 riesgo máximo.
- **Creditsafe**: presume de predecir "hasta el 70% de las insolvencias con 12 meses de antelación" — buen tono a imitar.

**Patrón consistente**: número grande + banda de color + **línea temporal de evolución**. Nunca solo un gauge estático.

### Explicaciones
Los "loan officer workspaces" reales usan: badge de decisión, gauge de probabilidad, **reason codes** y **gráfico waterfall de SHAP**. Para la demo: lista de 3-5 factores con signo y barra de peso + waterfall simplificado + frase generada ("el score bajó 8 puntos por deterioro en días de cobro"). No SHAP crudo.

### Alertas
Cada alerta = empresa + severidad + **disparador concreto** ("caída de 12 puntos en 30 días") + fecha + acción sugerida. Ordenadas por severidad × recencia. El canal de interrupción se reserva para movimiento de dinero y riesgo; mezclarlo con otra cosa destruye su credibilidad.

Umbral de fatiga: por analogía con SOC, más de 10 alertas al día y se ignoran todas. En tesorería de pyme el ritmo tolerable es semanal o mensual, no diario.

---

## 5. Color con datos financieros

- El rojo/verde puro falla para el ~8% de los hombres (daltonismo rojo-verde).
- Alternativa recomendada: pares **azul/naranja** o **azul/amarillo**.
- **Nunca codificar significado solo con color**: añadir flecha, signo, o texto.
- Verde/rojo solo para ganancia/pérdida; tonos apagados para datos sin carga direccional; **un único color de acento** reservado a la acción primaria.
- Cifras con **tabular figures** para que se alineen en las tablas.

Para un score 0-100: barra o gauge con **gradiente continuo sobre un mismo eje de color** (ámbar → aguamarina, usando el acento de Embat) + etiqueta textual del nivel. Nunca tres círculos de semáforo.

---

## 6. Patrones de dashboard B2B

- Sidebar de 240–280 px + tira de 4–6 tarjetas KPI + grid flexible.
- Una **métrica héroe** grande arriba, con drill-down progresivo por capas.
- Variación con **flecha + porcentaje**, casi siempre junto a un **sparkline**.
- Estados como etiqueta de texto, no solo color.
- Framework útil: **rol → métrica → densidad → acción**. Definir quién mira, liderar con el número que vino a buscar, calibrar densidad al rol, anclar la acción siguiente.
- Densidad alta (Ramp, Brex) para profesionales; mínima (Mercury) para no especialistas. Dado que el usuario aquí es un gerente sin perfil financiero, **densidad media-baja**.

---

## 7. Stack para 48 horas

**Recomendado: Next.js + shadcn/ui + Tremor, desplegado en Vercel.** Da el mejor ratio "pinta de producto" / tiempo, y sale código React propio, no un envoltorio. v0.dev acelera la generación de componentes.

- **Tremor** para KPIs, gauges y tarjetas: preestilizado y combina con shadcn de fábrica. Por debajo usa Recharts (2,4 M descargas/semana, estándar de facto en dashboards SaaS).
- **Streamlit**: red de seguridad si nadie domina React. Rápido y con enlace público gratis, pero su estética por defecto se lee como "notebook con botones".
- **Gradio**: pensado para demos de modelos, encaja mal con un dashboard multi-panel.
- **Retool**: rapidísimo pero se percibe como herramienta interna, sin marca propia.
- **Observable / Evidence.dev**: buenos para reporting con SQL, flojos para interactividad tipo "clic en empresa → panel".

### Datos de ejemplo creíbles
Faker con locale `es_ES`, 40–80 pymes con nombres verosímiles ("Suministros Hidráulicos del Ebro S.L.", no "Empresa 1"). Asegurar que **todos** los estados de la UI tengan contenido: varias sanas, varias en alerta, y alguna en "datos insuficientes" para demostrar robustez. 24 meses con estacionalidad y uno o dos choques visibles, para que al hacer clic la serie **cuente una historia**.

---

## 8. La demo y el pitch

### Reparto de los 5 minutos
- **~1 min problema**, con una pyme concreta y nombrada
- **~3 min demo en vivo** del flujo completo sobre esa empresa
- **~1 min** a quién se vende y por qué le sale a cuenta

Error más citado por jueces de Devpost: los equipos dedican el 5% del tiempo al problema y el 95% a la solución, y luego puntúan bajo en impacto. La proporción recomendada es **30/70**.

### Demo en vivo
Un demo en vivo que funciona gana casi siempre a un proyecto más ambicioso enseñado en diapositivas. Mitigación del riesgo:
- **Congelar el código 4 horas antes** de la entrega
- Ensayar el camino feliz **5 veces**, buscando dónde se rompe
- Datos precargados, sin depender de conexiones en vivo
- Vídeo de respaldo grabado dos veces, y capturas como último recurso

> "Los jueces puntúan lo que ven en pantalla, no lo que casi ocurrió por detrás."

### Storytelling
Una persona concreta gana a una categoría genérica. Enseñar **una** pyme ficticia con nombre recorriendo el flujo completo funciona mejor que un dashboard agregado de "10.000 empresas analizadas".

### Detalles que hacen que parezca producto
Dominio propio (que no se vea localhost), cero placeholders, estados vacíos cuidados, hover states, espaciado consistente, y al menos un caso de error manejado ("empresa sin datos suficientes → scoring pendiente"). Los jueces usan "polish" como categoría explícita.

### Qué busca un sponsor
No evalúan como un VC. Usan su track para reclutar (el 40% de las empresas usa hackathons como proceso de contratación), validar roadmap y marca. Como Embat dice explícitamente que en 5 minutos hay que ver a quién se le vende, su criterio real pesa en **claridad de cliente + ejecución visible**, no en arquitectura de backend.

### Precedente
El ganador del Allied Bank Fintech Hackathon 2024 fue "Kestrl": scoring de crédito alternativo basado en comportamiento, integrado con apps bancarias. Estructuralmente muy cercano a este reto.

HackSpain 2026 parece ser la primera edición (sin confirmar): 5 tracks liderados por startups, premio de 5.000 €, jurado de firmas de VC españolas.
