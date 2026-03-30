# Scripts de utilidad y diagnóstico

Scripts one-off para mantenimiento, migraciones y debugging. No forman parte del flujo principal de la app.

## Migraciones y setup

| Script | Descripción |
|---|---|
| `init_db.py` | Inicialización inicial de la base de datos |
| `add_indexes.py` | Agrega índices de performance (idempotente) |
| `import_to_neon.py` | Importa datos a una instancia de Neon PostgreSQL |
| `backfill_cba.py` | Rellena la tabla `cba_monthly` con datos históricos |
| `parse_cba.py` | Parsea la definición de CBA desde el JSON del INDEC |
| `optimize_search.py` | Aplica optimizaciones de búsqueda full-text |

## Fixes de datos

| Script | Descripción |
|---|---|
| `fix_carref_prices.py` | Fix de precios mal importados de Carrefour (v1) |
| `fix_carref_prices_chunked.py` | Idem, procesando en chunks para datasets grandes |
| `fix_carref_prices_chunked2.py` | Idem, segunda iteración del fix |
| `fix_db.py` | Fix genérico de inconsistencias en DB |
| `fix_db_prices.py` | Fix de precios nulos o incorrectos |
| `fix_null_prices.py` | Rellena precios nulos con el valor más cercano |

## Diagnóstico y debugging

| Script | Descripción |
|---|---|
| `check_coto.py` | Verifica datos scrapeados de Coto |
| `check_encoding.py` | Detecta problemas de encoding en productos almacenados |
| `check_images.py` | Verifica URLs de imágenes accesibles |
| `check_images_json.py` | Idem, desde archivos JSON locales |
| `check_imgs.py` | Versión alternativa de check_images |
| `check_supermarkets.py` | Verifica que los 3 supermercados estén activos en DB |
| `dump_anomalous.py` | Exporta productos con datos anómalos (precio 0, sin EAN, etc.) |
| `dump_detail.py` | Exporta detalle de un producto específico por EAN |
| `dump_urls.py` | Exporta URLs de listings para verificación externa |

## Tests manuales (exploratorios, no pytest)

| Script | Descripción |
|---|---|
| `test_carrefour.py` | Prueba el scraper de Carrefour en vivo |
| `test_cast.py` | Prueba cast de tipos en CockroachDB |
| `test_coto_sevenup.py` | Prueba específica del producto 7UP en Coto |
| `test_dates.py` | Prueba parseo de fechas en snapshots |
| `test_db_import.py` | Prueba el pipeline completo de importación a DB |
| `test_diagnostics.py` | Diagnóstico general de la DB |
| `test_fts.py` | Prueba búsqueda full-text |
| `test_nulls.py` | Verifica productos con campos nulos críticos |
| `test_quilmes.py` | Prueba específica del producto Quilmes |
| `test_regex.py` | Prueba regexes de parseo de contenido |
| `test_search.py` | Prueba el endpoint de búsqueda de la API |

## Uso

```bash
# Desde la raíz del proyecto:
python scripts/backfill_cba.py
python scripts/check_encoding.py
```

> **Nota:** Requieren `COMPARAR_DATABASE_URL` o `DATABASE_URL` en el entorno (`.env`).
