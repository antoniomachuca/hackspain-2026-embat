# Aviso por correo a la empresa (Mailpit en local)

Cuando el monitor detecta que una empresa entra en **Torciéndose** o
**Deterioro**, `email_notifier.py` le manda un correo a su responsable
financiero: score actual, caída frente al trimestre anterior, los dos factores
que más pesan, una acción sugerida, la gráfica de 24 meses incrustada y un
enlace a su ficha en el front. Es el canal hermano del bot de Telegram, pero
con otro destinatario: Telegram avisa al analista de Embat de toda la cartera;
el correo avisa solo a la empresa a la que le va mal, y solo de lo suyo.

Está pensado para la demo en local. Nada de esto se despliega en Railway.

## 1. Levantar Mailpit

Mailpit es un servidor SMTP de pruebas con bandeja web. Acepta cualquier
remitente y destinatario sin autenticación.

```bash
# Homebrew (ya instalado en el portátil de Hugo)
mailpit --smtp 0.0.0.0:1025 --listen 0.0.0.0:8025

# o con Docker
docker run -d --name xray-mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit
```

Bandeja: <http://localhost:8025>. SMTP: `localhost:1025`.

## 2. Probar el envío

```bash
# Alerta ficticia de ejemplo (COMP_0010, números inventados)
.venv/bin/python algorythm/email_notifier.py --test

# Alerta REAL de una empresa: mismos números que su ficha en el front
# (score, delta a 3 meses, factores). Solo envía si hoy está en deterioro.
.venv/bin/python algorythm/email_notifier.py --test --company COMP_0176

# Empresa que hoy no está en deterioro: --force la envía igualmente
.venv/bin/python algorythm/email_notifier.py --test --company COMP_0001 --force

# La última alerta de deterioro real del feed del monitor
.venv/bin/python algorythm/email_notifier.py --send-latest

# Destinatario explícito y sin gráfica
.venv/bin/python algorythm/email_notifier.py --test --company COMP_0176 --to hugo@ejemplo.es --no-chart
```

Empresas que hoy están en Deterioro o Torciéndose y sirven para la demo:
`COMP_0176` (caída de 77 puntos, score 5,1), `COMP_0059`, `COMP_0455`, `COMP_0094`
(Torciéndose). La lista completa sale con `--send-latest` o mirando el feed.

## 3. Modo monitor: que avise solo

Igual que `--telegram`, el monitor acepta `--email`. Vigila el snapshot del
scoring y, cuando aparece una alerta nueva de deterioro, la manda a la empresa.

```bash
.venv/bin/python algorythm/score_monitor.py --watch --email
# ambos canales a la vez:
.venv/bin/python algorythm/score_monitor.py --watch --telegram --email
```

Para provocar una alerta en la demo hay que publicar un snapshot nuevo del
scoring (`calc_score.py`); el monitor solo emite cuando cambia el estado de una
empresa entre snapshots. Para el vídeo es más fiable `--test` o `--send-latest`.

## 4. Destinatarios

Las empresas del dataset no tienen correo, así que la dirección se deriva del
identificador: `COMP_0010` recibe en `finanzas@comp-0010.xray.local`. En Mailpit
se ve una entrada por empresa, y todas las alertas de una misma empresa llevan
las cabeceras de hilo (`In-Reply-To` / `References`) para agruparse en un
cliente de correo real.

Para fijar una dirección concreta (por ejemplo, la tuya para la empresa de la
demo):

```bash
.venv/bin/python algorythm/email_notifier.py --set-recipient COMP_0010 hugo@ejemplo.es
.venv/bin/python algorythm/email_notifier.py --recipients
```

Se guarda en `algorythm/email_recipients.json`, que está en `.gitignore`.

## 5. Configuración

Todo por variables de entorno, con valores por defecto para Mailpit en local:

| Variable | Por defecto | Qué es |
| --- | --- | --- |
| `XRAY_SMTP_HOST` | `localhost` | Servidor SMTP |
| `XRAY_SMTP_PORT` | `1025` | Puerto SMTP |
| `XRAY_MAIL_FROM` | `X-Ray Monitor <monitor@xray.local>` | Remitente |
| `XRAY_MAIL_DOMAIN` | `xray.local` | Dominio de las direcciones derivadas y de los Message-ID |
| `XRAY_FRONT_URL` | `http://localhost:3000` | Base del enlace a la ficha de la empresa |
| `XRAY_MAIL_ENABLED` | `1` | `0` apaga el canal sin quitar el flag |

Sin dependencias nuevas: SMTP y MIME salen de la librería estándar.

## 5b. Estética

El correo sigue el sistema visual del front (`front/app/globals.css`,
`components/ui.tsx`): fondo `--color-deep`, tarjeta con borde fino y radio 18,
morado Embat en el acento y el botón, el número del score y su etiqueta en el
color del estado (la regla del `Anillo` de la ficha: `ESTADOS_TELEGRAM`, no la
banda del score), el delta con flecha y signo, y el nombre de la empresa como lo pinta el front
(`Sociedad 0176`). Los translúcidos del front van resueltos a sólidos porque
los clientes de correo no siempre soportan rgba.

La gráfica la genera `telegram_charts.py` con `theme='embat'`, que imita la
`Trayectoria` de `components/charts.tsx` (línea morada, umbral 60 punteado,
punto final en el color del estado). El tema por defecto del módulo, el navy
del bot y del endpoint `/chart` del backend, no cambia. Si la gráfica no se
puede generar (sin DuckDB, sin paneles), el correo sale sin imagen.

## 6. Qué alertas salen y cuáles no

| Estado nuevo | Dirección | ¿Correo a la empresa? |
| --- | --- | --- |
| DETERIORO | deterioro | Sí |
| TORCIENDOSE | deterioro | Sí |
| MEJORANDO, RECUPERACION | mejora | No |
| BACHE, ESTABLE, EVALUACION_PENDIENTE | ninguna | No (el monitor no las emite) |

## 7. Tests

```bash
.venv/bin/python -m pytest algorythm/test_email_notifier.py -q
```

Simulan el SMTP; no necesitan Mailpit levantado.
