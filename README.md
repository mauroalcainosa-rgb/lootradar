# LootRadar

Recolector de precios de juegos y gift cards para Chile. Corre gratis en GitHub Actions cada 4 horas y publica los datos en GitHub Pages para que la app los lea.

## Qué hay aquí

- `collector/collect.py`: consulta Steam (ofertas en Chile) y Epic (juegos gratis), guarda `data/deals.json` y el historial en `data/history/`, y avisa por Firebase cuando un precio baja.
- `.github/workflows/collect.yml`: programa el recolector cada 4 horas.
- `data/`: lo que lee la app, publicado en `https://mauroalcainosa-rgb.github.io/lootradar/data/deals.json`.

## Puesta en marcha

1. En **Settings → Pages**, elegir la rama `main` y la carpeta `/ (root)`.
2. En **Actions**, abrir "Recolectar precios" y pulsar **Run workflow** para la primera carga.
3. Cuando exista el proyecto de Firebase, guardar su cuenta de servicio (JSON) en **Settings → Secrets and variables → Actions** con el nombre `FIREBASE_SERVICE_ACCOUNT`. Sin ese secreto todo funciona, pero no se envían notificaciones.
