import requests
import re
import pandas as pd
from datetime import datetime
import os

def descargar_excel_alg():
    """Descarga el archivo Excel más reciente de ALG ANMAT"""
    
    session = requests.Session()
    
    # Headers para simular navegador
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        print("Obteniendo página inicial...")
        response = session.get("https://listadoalg.anmat.gob.ar/Home")
        response.raise_for_status()
        html = response.text
        
        # Extraer valores del formulario
        viewstate = re.search(r'name="__VIEWSTATE".*?value="([^"]*)"', html, re.DOTALL).group(1)
        viewstate_gen = re.search(r'name="__VIEWSTATEGENERATOR".*?value="([^"]*)"', html).group(1)
        event_validation = re.search(r'name="__EVENTVALIDATION".*?value="([^"]*)"', html, re.DOTALL).group(1)
        
        # Datos del formulario
        data = {
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstate_gen,
            '__EVENTVALIDATION': event_validation,
            'ctl00$ContentPlaceHolder1$txtRNPA': '',
            'ctl00$ContentPlaceHolder1$txtMarcaFantasia': '',
            'ctl00$ContentPlaceHolder1$ddEstado': '-1',
            'ctl00$ContentPlaceHolder1$txtDenominacion': '',
            'ctl00$ContentPlaceHolder1$cmdExportar': 'Exportar a Excel'
        }
        
        print("Descargando archivo Excel...")
        excel_response = session.post("https://listadoalg.anmat.gob.ar/Home/ExportarExcel", data=data)
        excel_response.raise_for_status()
        
        # Crear directorio si no existe
        os.makedirs('data', exist_ok=True)
        
        # Guardar archivo sin fecha
        filename = 'data/alg-listado.xlsx'
        
        with open(filename, 'wb') as f:
            f.write(excel_response.content)
        
        print(f"✅ Archivo descargado: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

def crear_key_producto(row):
    """Usa solo la columna 'id' como clave única de producto"""
    return str(row['id'])

def actualizar_historico(df_actual):
    """Actualiza el archivo histórico con fechas de alta/baja"""
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    archivo_historico = 'data/alg-historico.csv'
    archivo_altas_bajas = 'data/altas_bajas.csv'
    
    # Agregar columnas de fecha si no existen
    if 'fecha_alta' not in df_actual.columns:
        df_actual['fecha_alta'] = None
    if 'fecha_baja' not in df_actual.columns:
        df_actual['fecha_baja'] = None

    # Listas para almacenar altas y bajas de esta corrida
    altas_corrida = []
    bajas_corrida = []
    
    # Crear clave única para cada producto actual
    df_actual['_key'] = df_actual.apply(crear_key_producto, axis=1)
    
    if os.path.exists(archivo_historico):
        print("Cargando histórico existente...")
        # Si el archivo existe pero está vacío o corrupto, tratar como primera ejecución (sin recursión)
        try:
            df_historico = pd.read_csv(archivo_historico)
            if df_historico.empty:
                raise pd.errors.EmptyDataError
            # Asegurar que el histórico tenga la clave
            if '_key' not in df_historico.columns:
                df_historico['_key'] = df_historico.apply(crear_key_producto, axis=1)
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            print("Archivo histórico vacío o corrupto, iniciando desde cero...")
            os.remove(archivo_historico)
            # Crear histórico inicial sin recursión
            df_historico = df_actual.copy()
            df_historico['fecha_alta'] = fecha_hoy
            df_historico['fecha_baja'] = None
            # No registrar altas en la primera ejecución (punto de partida)
            # Remover columna auxiliar antes de guardar
            df_historico = df_historico.drop('_key', axis=1)
            df_actual = df_actual.drop('_key', axis=1)
            df_historico.to_csv(archivo_historico, index=False)
            print(f"✅ Histórico actualizado: {archivo_historico}")
            return df_historico
        
        # Encontrar productos nuevos y eliminados
        keys_actual = set(df_actual['_key'])
        keys_historico = set(df_historico['_key'])
        
        productos_nuevos = keys_actual - keys_historico
        productos_eliminados = keys_historico - keys_actual
        productos_reactivados = set()

        # Verificar productos reactivados (dados de alta nuevamente)
        if productos_nuevos:
            for key in list(productos_nuevos):  # Usar list para poder modificar el set durante la iteración
                historico_producto = df_historico[df_historico['_key'] == key]
                if not historico_producto.empty and not historico_producto['fecha_baja'].isna().all():
                    # Si el producto ya existía y estaba dado de baja, moverlo a reactivados
                    productos_nuevos.remove(key)
                    productos_reactivados.add(key)

        print(f"Productos nuevos: {len(productos_nuevos)}")
        print(f"Productos reactivados: {len(productos_reactivados)}")
        print(f"Productos eliminados: {len(productos_eliminados)}")

        # Marcar productos eliminados con fecha de baja y registrar bajas
        if productos_eliminados:
            mask_eliminados = df_historico['_key'].isin(productos_eliminados) & df_historico['fecha_baja'].isna()
            df_historico.loc[mask_eliminados, 'fecha_baja'] = fecha_hoy
            # Registrar bajas
            bajas_df = df_historico[mask_eliminados].copy()
            if not bajas_df.empty:
                bajas_df['tipo_cambio'] = 'baja'
                bajas_df['fecha_cambio'] = fecha_hoy
                bajas_corrida.append(bajas_df)

        # Agregar productos nuevos y registrar altas
        if productos_nuevos:
            productos_nuevos_df = df_actual[df_actual['_key'].isin(productos_nuevos)].copy()
            productos_nuevos_df['fecha_alta'] = fecha_hoy
            productos_nuevos_df['fecha_baja'] = None
            # Registrar altas nuevas
            if not productos_nuevos_df.empty:
                productos_nuevos_df['tipo_cambio'] = 'alta_nuevo'
                productos_nuevos_df['fecha_cambio'] = fecha_hoy
                altas_corrida.append(productos_nuevos_df)
            # Combinar con histórico
            df_historico = pd.concat([df_historico, productos_nuevos_df], ignore_index=True)

        # Procesar productos reactivados
        if productos_reactivados:
            productos_reactivados_df = df_actual[df_actual['_key'].isin(productos_reactivados)].copy()
            productos_reactivados_df['fecha_alta'] = fecha_hoy
            productos_reactivados_df['fecha_baja'] = None
            # Registrar reactivaciones
            if not productos_reactivados_df.empty:
                productos_reactivados_df['tipo_cambio'] = 'alta_reactivado'
                productos_reactivados_df['fecha_cambio'] = fecha_hoy
                altas_corrida.append(productos_reactivados_df)
            # Actualizar en histórico
            for key in productos_reactivados:
                df_historico.loc[df_historico['_key'] == key, 'fecha_alta'] = fecha_hoy
                df_historico.loc[df_historico['_key'] == key, 'fecha_baja'] = None
        
        # Actualizar información de productos existentes (mantener fechas originales)
        productos_existentes = list(keys_actual & keys_historico)
        if productos_existentes:
            print("Actualizando información de productos existentes...")
            # Filtrar registros existentes
            df_historico_existentes = df_historico[df_historico['_key'].isin(productos_existentes)]
            df_actual_existentes = df_actual[df_actual['_key'].isin(productos_existentes)]
            
            # Crear un mapping de fechas originales
            fechas_mapping = df_historico_existentes.set_index('_key')[['fecha_alta', 'fecha_baja']]
            
            # Actualizar datos manteniendo fechas originales
            df_actual_existentes = df_actual_existentes.set_index('_key')
            df_actual_existentes[['fecha_alta', 'fecha_baja']] = fechas_mapping
            df_actual_existentes = df_actual_existentes.reset_index()
            
            # Reemplazar en histórico
            df_historico = df_historico[~df_historico['_key'].isin(productos_existentes)]
            df_historico = pd.concat([df_historico, df_actual_existentes], ignore_index=True)
        
    else:
        print("Creando histórico inicial...")
        # Primer ejecución: todos los productos son nuevos
        df_historico = df_actual.copy()
        df_historico['fecha_alta'] = fecha_hoy
        df_historico['fecha_baja'] = None
        # No registrar altas en la primera ejecución (punto de partida)
    
    # Remover columna auxiliar antes de guardar
    df_historico = df_historico.drop('_key', axis=1)
    df_actual = df_actual.drop('_key', axis=1)

    # Guardar histórico actualizado
    df_historico.to_csv(archivo_historico, index=False)
    print(f"✅ Histórico actualizado: {archivo_historico}")

    # Guardar/Acumular archivo de altas y bajas
    if altas_corrida or bajas_corrida:
        # Concatenar todas las altas y bajas de esta corrida
        cambios_corrida = []
        if altas_corrida:
            cambios_corrida.append(pd.concat(altas_corrida, ignore_index=True))
        if bajas_corrida:
            cambios_corrida.append(pd.concat(bajas_corrida, ignore_index=True))
        cambios_corrida_df = pd.concat(cambios_corrida, ignore_index=True) if cambios_corrida else None

        if cambios_corrida_df is not None:
            # Si ya existe el archivo, acumular
            if os.path.exists(archivo_altas_bajas):
                df_altas_bajas = pd.read_csv(archivo_altas_bajas)
                df_altas_bajas = pd.concat([df_altas_bajas, cambios_corrida_df], ignore_index=True)
            else:
                df_altas_bajas = cambios_corrida_df
            # Guardar
            df_altas_bajas.to_csv(archivo_altas_bajas, index=False)
            print(f"✅ Altas y bajas acumuladas: {archivo_altas_bajas}")

    return df_historico

def limpiar_dataframe(df):
    """Limpia el DataFrame de saltos de línea innecesarios"""
    # Copia para no modificar el original
    df = df.copy()
    
    # Reemplazar saltos de línea por espacios en todas las columnas string
    for columna in df.select_dtypes(include=['object']).columns:
        df[columna] = df[columna].astype(str).apply(lambda x: ' '.join(x.split()))
    
    return df

def actualizar_estadisticas_readme(df_historico):
    """Actualiza la sección de estadísticas en el README"""
    # Calcular estadísticas
    stats = {}
    
    # Fecha de primera ejecución (primer alta registrada)
    stats['fecha_inicio'] = df_historico['fecha_alta'].min()
    
    # Productos activos y dados de baja
    stats['productos_activos'] = len(df_historico[df_historico['fecha_baja'].isna()])
    stats['productos_dados_baja'] = len(df_historico[df_historico['fecha_baja'].notna()])
    stats['total_historico'] = len(df_historico)
    
    # Estadísticas semanales
    stats['stats_semanales'] = []
    
    # Si existe el archivo de altas y bajas, procesar estadísticas semanales
    if os.path.exists('data/altas_bajas.csv'):
        df_ab = pd.read_csv('data/altas_bajas.csv')
        if not df_ab.empty:
            df_ab['fecha_cambio'] = pd.to_datetime(df_ab['fecha_cambio'])
            df_ab = df_ab.sort_values('fecha_cambio')
            
            # Agrupar por semana
            weekly_stats = df_ab.groupby([pd.Grouper(key='fecha_cambio', freq='W'), 'tipo_cambio']).size().unstack(fill_value=0)
            for idx, row in weekly_stats.iterrows():
                # Sumar las altas nuevas y reactivaciones
                altas_total = int(row.get('alta_nuevo', 0)) + int(row.get('alta_reactivado', 0))
                stats['stats_semanales'].append({
                    'semana': idx.strftime('%Y-%m-%d'),
                    'altas': altas_total,
                    'bajas': int(row.get('baja', 0)),
                    'altas_nuevas': int(row.get('alta_nuevo', 0)),
                    'altas_reactivadas': int(row.get('alta_reactivado', 0))
                })
    
    # Si no hay estadísticas semanales, agregar la fecha actual con 0,0
    if not stats['stats_semanales']:
        stats['stats_semanales'].append({
            'semana': datetime.now().strftime('%Y-%m-%d'),
            'altas': 0,
            'bajas': 0
        })
    
    # Actualizar README
    with open('README.md', 'r') as f:
        content = f.read()
    
    # Preparar la sección de estadísticas
    estado_actual = """## Estado actual

_Esta sección se actualiza automáticamente en cada ejecución_

| Métrica | Valor |
|---------|-------|
| 📅 Inicio del monitoreo | {} |
| ✅ Productos activos | {:,} |
| ❌ Productos dados de baja | {:,} |
| 📊 Total histórico | {:,} |

### Últimas actualizaciones

| Semana | Altas (Nuevos/Reactivados) | Bajas |
|--------|------------------------|-------|
{}

""".format(
        stats['fecha_inicio'],
        stats['productos_activos'],
        stats['productos_dados_baja'],
        stats['total_historico'],
        '\n'.join([f"| {s['semana']} | {s['altas']} ({s.get('altas_nuevas', 0)}/{s.get('altas_reactivadas', 0)}) | {s['bajas']} |" for s in reversed(stats['stats_semanales'][-4:])])  # Mostrar solo las últimas 4 semanas
    )
    
    if "## Estadísticas" in content:
        # Reemplazar sección existente
        content = re.sub(r"## Estadísticas.*?(?=##|$)", estado_actual, content, flags=re.DOTALL)
    else:
        # Agregar nueva sección antes de "## Consultas útiles"
        content = content.replace("## Consultas útiles", estado_actual + "## Consultas útiles")
    
    with open('README.md', 'w') as f:
        f.write(content)

def migrar_datos_historicos():
    """Migra los datos históricos para recategorizar las altas"""
    print("Iniciando migración de datos históricos...")
    
    archivo_historico = 'data/alg-historico.csv'
    archivo_altas_bajas = 'data/altas_bajas.csv'
    archivo_historico_backup = 'data/alg-historico.csv.bak'
    archivo_altas_bajas_backup = 'data/altas_bajas.csv.bak'
    
    # Crear backups
    if os.path.exists(archivo_historico):
        import shutil
        shutil.copy2(archivo_historico, archivo_historico_backup)
        print(f"Backup creado: {archivo_historico_backup}")
    
    if os.path.exists(archivo_altas_bajas):
        import shutil
        shutil.copy2(archivo_altas_bajas, archivo_altas_bajas_backup)
        print(f"Backup creado: {archivo_altas_bajas_backup}")
        
        # Leer archivo histórico y altas_bajas existente
        df_historico = pd.read_csv(archivo_historico)
        df_altas_bajas = pd.read_csv(archivo_altas_bajas)
        
        # Ordenar por fecha para procesar cronológicamente
        df_altas_bajas = df_altas_bajas.sort_values('fecha_cambio')
        
        # Crear un nuevo DataFrame para las altas_bajas recategorizadas
        nuevas_altas_bajas = []
        productos_historico = set()  # Conjunto para trackear productos ya vistos
        
        # Procesar cada cambio cronológicamente
        for _, row in df_altas_bajas.iterrows():
            if row['tipo_cambio'] == 'alta':
                # Verificar si el producto ya existía antes
                if row['id'] in productos_historico:
                    # Era una reactivación
                    row['tipo_cambio'] = 'alta_reactivado'
                else:
                    # Era un alta nueva
                    row['tipo_cambio'] = 'alta_nuevo'
                    productos_historico.add(row['id'])
            elif row['tipo_cambio'] == 'baja':
                # Mantener el registro de baja como está
                pass
            
            nuevas_altas_bajas.append(row)
        
        # Convertir a DataFrame y guardar
        df_nuevas_altas_bajas = pd.DataFrame(nuevas_altas_bajas)
        df_nuevas_altas_bajas.to_csv(archivo_altas_bajas, index=False)
        print(f"✅ Archivo de altas y bajas migrado: {archivo_altas_bajas}")
    
    print("✅ Migración completada")
    return True

def main():
    """Función principal"""
    
    try:
        # 1. Descargar archivo Excel actual
        archivo_excel = descargar_excel_alg()
        
        # 2. Leer archivo Excel
        print("Procesando archivo Excel...")
        df_actual = pd.read_excel(archivo_excel)
        print(f"Productos en archivo actual: {len(df_actual)}")
        
        # 3. Limpiar datos y crear/actualizar CSV equivalente
        archivo_csv = 'data/alg-listado.csv'
        df_actual_limpio = limpiar_dataframe(df_actual)
        df_actual_limpio.to_csv(archivo_csv, index=False)
        print(f"✅ CSV creado: {archivo_csv}")
        
        # 4. Actualizar histórico con fechas de alta/baja usando datos limpios
        df_historico = actualizar_historico(df_actual_limpio)
        
        # 5. Actualizar estadísticas en README
        actualizar_estadisticas_readme(df_historico)
        print("✅ README actualizado con estadísticas")

        # 6. Generar estadisticas.json con tablas pivot de productos activos
        df_activos = df_historico[df_historico['fecha_baja'].isna()]
        estadisticas = {
            "por_marca": df_activos['marca'].value_counts().to_dict() if 'marca' in df_activos.columns else {},
            "por_tipo_producto": df_activos['TipoProducto'].value_counts().to_dict() if 'TipoProducto' in df_activos.columns else {},
            "por_denominacion_venta": df_activos['denominacionventa'].value_counts().to_dict() if 'denominacionventa' in df_activos.columns else {}
        }
        import json
        with open('data/estadisticas.json', 'w') as f:
            json.dump(estadisticas, f, ensure_ascii=False, indent=2)
        print("✅ Archivo data/estadisticas.json generado")

        print("✅ Proceso completado exitosamente")
        
        # Mostrar estadísticas
        productos_activos = len(df_historico[df_historico['fecha_baja'].isna()])
        productos_dados_baja = len(df_historico[df_historico['fecha_baja'].notna()])
        print(f"📊 Estadísticas:")
        print(f"   - Productos activos: {productos_activos}")
        print(f"   - Productos dados de baja: {productos_dados_baja}")
        print(f"   - Total histórico: {len(df_historico)}")
        
    except Exception as e:
        print(f"❌ Error en el proceso: {e}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--migrar':
        migrar_datos_historicos()
    else:
        main()