# Piezas de TikTok e Instagram — Zone Digital

Paquetes diarios listos para subir a TikTok (**@zone_digital25**) e Instagram Reels (**@zone-digital25**) y vender los libros de [zone-digital.com](https://zone-digital.com) en Amazon.

## Tu rutina diaria (≈5 minutos)

1. Abre **[HOY.md](HOY.md)**: dice qué subir hoy, a qué hora y trae el copy listo para copiar.
2. Descarga los videos desde el celular (o el `.zip` del día en la computadora).
3. En TikTok: **+ › Subir › video › pega el copy de TikTok › Contenido comercial: Tu marca › Publicar** (o **Programar**).
4. En Instagram: **+ › Reel › el mismo video › pega el copy de Instagram › Compartir** (o prográmalo en Meta Business Suite).

Cada mañana te llega un aviso con la lista del día y los enlaces.

## Cuántas piezas por día

| Período | Metricool (gratis, automático) | Tú subes a mano | Total |
|---|---|---|---|
| 29–31 oct | 10:00 · 12:00 · 18:00 | 15:00 · 20:00 | 5 |
| 1–20 nov y 1–20 dic | 18:00 | 10:00 · 12:00 · 15:00 · 20:00 | 5 |
| 21–30 nov y 21–31 dic | — | 10:00 · 12:00 · 15:00 · 18:00 · 20:00 | 5 |

El plan gratis de Metricool publica 20 piezas al mes. Si activas Starter (~€16/mes) todo pasa a ser automático y el tiempo manual baja a cero.

## Automático y gratis (sin que hagas nada)

- **TikTok vía Metricool:** las publicaciones de las 18:00 de la tabla de arriba (20 al mes).
- **YouTube Shorts (@Zone-Digital):** 1 Short diario a las 19:00, días 1–20 de cada mes (20 al mes), con el mejor reel del día. Lo programa la tarea del domingo (`scripts/youtube_plan.py`, registro en `content/youtube.json`).
- **Instagram / Facebook:** si los conectas en Metricool, la tarea del domingo también programa sus 20 gratis al mes con los mismos videos y te descuenta ese trabajo manual.

## Dónde está cada cosa

| Carpeta | Contenido |
|---|---|
| `HOY.md` | Lo de hoy (se actualiza cada mañana) |
| `dias/AAAA-MM-DD/` | Plan del día + copys de TikTok e Instagram (`.txt`) |
| rama **`media`** › `dias/AAAA-MM-DD/` | Los videos `.mp4` y el `.zip` del día (solo las 2 semanas vigentes) |
| `content/pool.json` | Banco de piezas por publicar (hooks, puntos, diapositivas, copy) |
| `content/plan.json` | Qué pieza va en qué día y hora |
| `content/config.json` | Horas, total diario y franjas de Metricool |
| `engine/` | Motor de diseño (reels 9:16 y carruseles en video, música original) |
| `scripts/build_days.py` | Diseña y publica una semana de paquetes |
| `scripts/hoy.py` | Actualiza `HOY.md` y arma el aviso diario |

## Cómo se genera

- **Cada domingo** se diseñan las **35 piezas de la semana siguiente** (5 por día) con lo mejor de cada libro: los temas que mejor convierten (certificaciones PMP, AWS, CFA, IA) y rotación del resto del catálogo.
- **Cada mañana** se actualiza `HOY.md` y te llega el aviso.

Por qué semanal y no mensual: el contenido sale fresco, se puede ajustar según lo que funcione en TikTok y cada descarga pesa menos.
