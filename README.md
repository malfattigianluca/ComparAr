# 🛒 ComparAr

**Comparador de precios de supermercados argentinos.**

ComparAr scrapea precios de los principales supermercados online de Argentina, los almacena en una base de datos PostgreSQL y expone una API + interfaz web para buscar y comparar productos en tiempo real.

## Supermercados soportados

| Supermercado | Método de scraping |
|---|---|
| **Carrefour** | GraphQL (VTEX) |
| **Día** | GraphQL (VTEX) |
| **Coto Digital** | HTML scraping (BeautifulSoup) |

## Arquitectura

```
ComparAr/
├── main.py                  # Orquestador principal de scraping
├── scrapers/                # Scrapers por supermercado
│   ├── carrefour_dia_scraper.py   # Scraper compartido VTEX (Carrefour y Día)
│   └── coto_scraper.py            # Scraper HTML para Coto Digital
├── api/                     # API REST (FastAPI)
│   ├── main.py              # Configuración FastAPI + CORS
│   └── routes/
│       ├── products.py      # Búsqueda y detalle de productos
│       ├── compare.py       # Comparación entre supermercados
│       └── cba.py           # Canasta Básica Alimentaria
├── web/                     # Frontend (React + TypeScript + Vite)
├── data/
│   ├── db.py                # Capa de persistencia PostgreSQL
│   ├── schema.sql           # Esquema de base de datos
│   └── cba_definition.json  # Definición de Canasta Básica
├── utils/                   # Normalización y utilidades
│   ├── normalizador.py      # Normalización de nombres de productos
│   └── pricing.py           # Cálculos de precios
├── scripts/                 # Scripts de mantenimiento y migración
│   └── import_to_neon.py    # Importar histórico JSON → PostgreSQL
├── migrate.py               # Migraciones de base de datos
└── requirements.txt         # Dependencias Python
```

## Requisitos previos

- **Python** 3.10+
- **Node.js** 18+ (para el frontend)
- **PostgreSQL** (opcional — sin DB se guardan solo JSON locales)

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/malfattigianluca/ComparAr.git
cd ComparAr
```

### 2. Instalar dependencias de Python

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Instalar dependencias del frontend

```bash
cd web
npm install
cd ..
```

## Uso

### Ejecutar scraping

```bash
python main.py
```

Esto scrapea los tres supermercados en secuencia y guarda los resultados en `data/results/<supermercado>/`.

Si tenés configurada una base de datos, los datos también se persisten automáticamente (ver sección de [Base de datos](#base-de-datos)).

### Levantar la API

```bash
uvicorn api.main:app --reload
```

La API estará disponible en `http://localhost:8000`. Documentación interactiva en `/docs`.

#### Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/products/search?q=leche` | Buscar productos por nombre o EAN |
| `GET` | `/products/{id}/detail` | Detalle de producto + precios en todos los supermercados |
| `GET` | `/products/{id}/history` | Historial de precios de un listing |
| `GET` | `/compare/...` | Comparación entre supermercados |
| `GET` | `/cba/...` | Canasta Básica Alimentaria |

### Levantar el frontend

```bash
cd web
npm run dev
```

El frontend estará disponible en `http://localhost:5173`.

## Base de datos

El proyecto soporta persistencia en PostgreSQL (Neon, Supabase, CockroachDB, etc.). Sin base de datos configurada, el scraping funciona igual guardando solo archivos JSON.

### Configuración rápida

1. Ejecutá el esquema sobre tu base:

```bash
psql "$DATABASE_URL" -f data/schema.sql
```

2. Configurá la variable de entorno:

```bash
# PowerShell
$env:COMPARAR_DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require"

# Bash
export COMPARAR_DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require"
```

> También se acepta `DATABASE_URL` como alternativa.

3. Ejecutá `python main.py` normalmente. Los datos se persisten automáticamente.

Para más detalles, ver [README_DB_ONLINE.md](README_DB_ONLINE.md).

### Modelo de datos

```
supermarket ─┐
             ├──→ listings ──→ price_snapshots
products ────┘        │
                      └──→ latest_prices
```

- **`supermarket`** — Supermercados registrados
- **`products`** — Productos únicos (por EAN)
- **`listings`** — Publicaciones de cada supermercado
- **`price_snapshots`** — Historial completo de precios
- **`latest_prices`** — Vista materializada del último precio por listing
- **`cba_monthly`** — Cálculo mensual de Canasta Básica por supermercado

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Scraping | `requests`, `aiohttp`, `beautifulsoup4` |
| Backend | `FastAPI`, `uvicorn` |
| Base de datos | PostgreSQL + `psycopg` |
| Frontend | React + TypeScript + Vite |

## Licencia

Este proyecto es de código abierto. Usalo, modificalo y compartilo libremente.
