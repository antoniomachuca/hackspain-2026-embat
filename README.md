# HackSpain 2026 · Reto Embat (X-Ray)

> **¿Puede el dinero decir cómo está una empresa?**  
> Proyecto desarrollado para el track de **Embat** en **HackSpain 2026** (18–20 de septiembre, ETSIT UPM, Madrid).

---

## 🎯 Objetivo del Reto
A partir del rastro financiero de **250 empresas durante 24 meses**, construir:
1. **Motor de Score de Salud Financiera:** Capturar la trayectoria continua de la empresa (anticipando mejoras y deterioros en ambas direcciones).
2. **Explicabilidad:** Identificar con claridad los factores y señales causales del cambio de score.
3. **Producto B2B de Valor Añadido:** Solución comercializable basada en el score.
4. **Demo Interactiva:** Aplicación navegable para presentación en vivo ante jurado e inversores.

---

## 👥 Equipo
- **[@antoniomachuca](https://github.com/antoniomachuca)**
- **[@carleondel](https://github.com/carleondel)**
- **[@HugoOlivaR](https://github.com/HugoOlivaR)**
- **[@agustmun-web](https://github.com/agustmun-web)**
- **[@Pedrojonfg](https://github.com/Pedrojonfg)**

---

## 📂 Estructura del Proyecto
```text
.
├── .agents/                    # Enunciado y requerimientos del track
├── research/
│   └── algo_research_pedro.md  # Brief del algoritmo: features, nivel, tendencia, estados
├── PRODUCTO.md                 # Producto, comprador, arquitectura, reparto y pitch
├── REQUISITOS.md               # Requisitos por bloques de arquitectura (B0–B13) y trazabilidad
├── README.md
└── .gitignore
```

---

## 📖 Por dónde empezar
- **[`PRODUCTO.md`](PRODUCTO.md)** — qué construimos encima del score, a quién se lo
  vendemos, el reparto en 3 ejes y el contrato entre ellos. Empieza por aquí.
- **[`REQUISITOS.md`](REQUISITOS.md)** — la especificación ejecutable: qué construye cada
  bloque (B0–B13), con dueño, contrato, requisitos numerados y criterios de aceptación.
- **[`research/algo_research_pedro.md`](research/algo_research_pedro.md)** — el motor:
  features, percentiles por peer group, nivel, tendencia, estados y explicación.

`PRODUCTO.md` §0 resuelve las discrepancias entre ambos documentos. Ante una duda sobre
el algoritmo manda el brief; sobre producto, comprador o narrativa, manda `PRODUCTO.md`.
