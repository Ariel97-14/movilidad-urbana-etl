# Movilidad Urbana ETL

Programa de consola en Python para importar viajes de bicicletas desde CSV, validarlos, guardarlos en SQLite y generar un resumen en JSON. **Todos los viajes y estaciones del archivo de muestra son ficticios.** Es un proyecto independiente para portfolio; no necesita claves ni servicios externos.

## Qué demuestra

- Lectura y validación de CSV, fechas ISO 8601 con zona horaria y duraciones.
- Importaciones idempotentes mediante un identificador único por viaje.
- Persistencia SQLite y consultas agregadas para producir métricas.
- Comandos reproducibles, pruebas automatizadas y CI en Python 3.11 y 3.12.

## Uso

Requiere Python 3.11 o superior. Desde la raíz de este repositorio:

```bash
python -m movilidad import data/viajes_ejemplo.csv --db movilidad.sqlite3
python -m movilidad report --db movilidad.sqlite3
```

La primera importación del ejemplo devuelve `5` insertados, `1` duplicado y `1` rechazado. Repetirla devuelve `0` insertados y `6` duplicados; el registro inválido sigue rechazado. El reporte incluye cantidad de viajes, minutos totales, estación de salida con más viajes y viajes por mes.

El programa normaliza las fechas a UTC antes de guardarlas; los meses del reporte también se calculan en UTC. Una duración debe tener segundos enteros y estar entre 1 segundo y 24 horas. En caso de empate entre estaciones, se elige la primera en orden alfabético. Las filas inválidas se cuentan sin volcar su contenido en la salida.

## Formato del CSV

Columnas obligatorias: `trip_id`, `started_at`, `ended_at`, `start_station`, `end_station`. Las fechas deben tener zona horaria, por ejemplo `2026-01-05T08:00:00-03:00` o `2026-01-05T11:00:00Z`. Los identificadores y nombres de estación no pueden estar vacíos.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

La base `.sqlite3` se excluye de Git. Este proyecto es una demostración local: no incluye descarga de datos reales, interfaz web ni despliegue de producción.

