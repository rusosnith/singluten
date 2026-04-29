# Monitor ALG ANMAT

Este repositorio mantiene actualizado automáticamente el listado de Alimentos Libres de Gluten (ALG) de ANMAT.

## Archivos principales

- **`data/alg-listado.xlsx`**: Archivo Excel actual (actualizado semanalmente)
- **`data/alg-listado.csv`**: Versión CSV del listado actual
- **`data/alg-historico.csv`**: Histórico completo con fechas de alta y baja
- **`data/altas_bajas.csv`**: Registro acumulativo de todas las altas y bajas detectadas en cada ejecución

## Funcionamiento

- **Frecuencia**: Se actualiza automáticamente todos los lunes a las 9:00 AM UTC
- **Proceso**: 
  1. Descarga el archivo Excel más reciente de ANMAT
  2. Lo guarda como `alg-listado.xlsx` (sobreescribiendo el anterior)
  3. Genera un CSV equivalente
  4. Actualiza el histórico agregando fechas de alta/baja
  5. Registra en `altas_bajas.csv` todas las altas y bajas detectadas en cada ejecución

## Archivo de altas y bajas

El archivo `altas_bajas.csv` contiene todos los cambios detectados en cada ejecución del script. Incluye todas las columnas originales del producto, más:

- **`tipo_cambio`**: Puede ser:
  - **`alta_nuevo`**: Producto que aparece por primera vez en el listado
  - **`alta_reactivado`**: Producto que existía antes, fue dado de baja y vuelve a aparecer
  - **`baja`**: Producto que desaparece del listado
- **`fecha_cambio`**: Fecha en que se detectó el cambio

Esto permite analizar fácilmente cuándo y qué tipo de cambio ocurrió en el listado.

## Archivo histórico

El archivo `alg-historico.csv` contiene:
- **Todos los productos** que alguna vez estuvieron en el listado
- **`fecha_alta`**: Cuándo apareció el producto por primera vez (o fue reactivado)
- **`fecha_baja`**: Cuándo fue eliminado del listado (vacío si está activo)

---

## Estado actual

_Esta sección se actualiza automáticamente en cada ejecución_

| Métrica | Valor |
|---------|-------|
| 📅 Inicio del monitoreo | 2025-07-26 |
| 🔄 Última actualización | 2026-04-29 |
| 🕒 Último cambio detectado | 2026-04-27 |
| ✅ Productos activos | 25,531 |
| ❌ Productos dados de baja | 1,106 |
| 📊 Total histórico | 26,637 |

### Últimas actualizaciones

| Semana | Altas (Nuevos/Reactivados) | Bajas |
|--------|------------------------|-------|
| 2026-05-03 | 126 (126/0) | 0 |
| 2026-04-26 | 262 (262/0) | 145 |
| 2026-04-19 | 63 (63/0) | 8 |
| 2026-04-12 | 3 (3/0) | 0 |

## Consultas útiles

Para analizar los datos puedes usar pandas:

```python
import pandas as pd

# Cargar datos
df = pd.read_csv('data/alg-historico.csv')

# Productos activos
activos = df[df['fecha_baja'].isna()]

# Productos agregados en el último mes
import datetime
hace_un_mes = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
nuevos = df[df['fecha_alta'] >= hace_un_mes]

# Productos dados de baja en el último mes
bajas = df[(df['fecha_baja'] >= hace_un_mes) & df['fecha_baja'].notna()]

# Altas y bajas detectadas en el último mes
df_ab = pd.read_csv('data/altas_bajas.csv')
altas_ult_mes = df_ab[(df_ab['tipo_cambio'] == 'alta') & (df_ab['fecha_cambio'] >= hace_un_mes)]
bajas_ult_mes = df_ab[(df_ab['tipo_cambio'] == 'baja') & (df_ab['fecha_cambio'] >= hace_un_mes)]
```
