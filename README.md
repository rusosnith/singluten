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

El archivo `altas_bajas.csv` contiene todas las altas y bajas detectadas en cada ejecución del script. Incluye todas las columnas originales del producto, más:

- **`tipo_cambio`**: "alta" o "baja"
- **`fecha_cambio`**: Fecha en que se detectó el alta o baja

Esto permite analizar fácilmente cuándo se detectó cada cambio en el listado.

## Archivo histórico

El archivo `alg-historico.csv` contiene:
- **Todos los productos** que alguna vez estuvieron en el listado
- **`fecha_alta`**: Cuándo apareció el producto por primera vez
- **`fecha_baja`**: Cuándo fue eliminado del listado (vacío si está activo)

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