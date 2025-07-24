# Monitor ALG ANMAT

Este repositorio mantiene actualizado automáticamente el listado de Alimentos Libres de Gluten (ALG) de ANMAT.

## Archivos principales

- **`data/alg-listado.xlsx`**: Archivo Excel actual (actualizado semanalmente)
- **`data/alg-listado.csv`**: Versión CSV del listado actual
- **`data/alg-historico.csv`**: Histórico completo con fechas de alta y baja

## Funcionamiento

- **Frecuencia**: Se actualiza automáticamente todos los lunes a las 9:00 AM UTC
- **Proceso**: 
  1. Descarga el archivo Excel más reciente de ANMAT
  2. Lo guarda como `alg-listado.xlsx` (sobreescribiendo el anterior)
  3. Genera un CSV equivalente
  4. Actualiza el histórico agregando fechas de alta/baja

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