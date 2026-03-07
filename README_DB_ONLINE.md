# Base de datos online (PostgreSQL)

El scraper ahora puede guardar cada producto en JSON local y, en paralelo, persistir snapshots en una base PostgreSQL online.

## 1) Crear la base online

Podés usar Supabase, Neon, Render, Railway o cualquier PostgreSQL administrado.

## 2) Ejecutar el esquema

Ejecutá el archivo `data/schema.sql` sobre tu base:

```powershell
psql "postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require" -f data/schema.sql
```

## 3) Configurar variable de entorno

```powershell
$env:COMPARAR_DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require"
```

También podés usar `DATABASE_URL`.

## 4) Instalar dependencias

```powershell
pip install -r requirements.txt
```

## 5) Ejecutar scraping normal

```powershell
python main.py
```

Si la variable está configurada, al final de cada mercado vas a ver logs tipo:

`DB COTO: X snapshots inserted (Y errors).`

Si no está configurada, el scraping sigue funcionando y solo guarda JSON local.

## Importar historico (estructura + datos ya recolectados)

Este comando toma todos los JSON en `data/results/*/*.json` y los carga en Neon.
El esquema (`data/schema.sql`) se crea automaticamente si no existe.

### Prueba rapida (1 archivo)

```powershell
python .\scripts\import_to_neon.py --limit-files 1
```

### Import completo

```powershell
python .\scripts\import_to_neon.py
```

### Import por mercado

```powershell
python .\scripts\import_to_neon.py --market coto --market dia
```
