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
    """Crea una clave única para identificar un producto"""
    # Usar las columnas más importantes para crear la clave
    key_parts = []
    
    # Lista de posibles nombres de columnas (el Excel puede variar)
    possible_columns = ['RNPA', 'SENASA', 'INV', 'Marca', 'Denominación', 'Denominacion']
    
    for col in possible_columns:
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            key_parts.append(str(row[col]).strip())
    
    # Si no encontramos columnas conocidas, usar todas las no-nulas
    if not key_parts:
        for col, val in row.items():
            if pd.notna(val) and str(val).strip():
                key_parts.append(str(val).strip())
    
    return '|'.join(key_parts) if key_parts else str(hash(tuple(row.values)))

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
        df_historico = pd.read_csv(archivo_historico)
        
        # Asegurar que el histórico tenga la clave
        if '_key' not in df_historico.columns:
            df_historico['_key'] = df_historico.apply(crear_key_producto, axis=1)
        
        # Encontrar productos nuevos y eliminados
        keys_actual = set(df_actual['_key'])
        keys_historico = set(df_historico['_key'])
        
        productos_nuevos = keys_actual - keys_historico
        productos_eliminados = keys_historico - keys_actual

        print(f"Productos nuevos: {len(productos_nuevos)}")
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
            # Registrar altas
            if not productos_nuevos_df.empty:
                productos_nuevos_df['tipo_cambio'] = 'alta'
                productos_nuevos_df['fecha_cambio'] = fecha_hoy
                altas_corrida.append(productos_nuevos_df)
            # Combinar con histórico
            df_historico = pd.concat([df_historico, productos_nuevos_df], ignore_index=True)
        
        # Actualizar información de productos existentes (mantener fechas originales)
        for key in keys_actual & keys_historico:
            mask_historico = df_historico['_key'] == key
            mask_actual = df_actual['_key'] == key
            
            if mask_historico.any() and mask_actual.any():
                # Mantener fecha_alta y fecha_baja del histórico
                fecha_alta_original = df_historico.loc[mask_historico, 'fecha_alta'].iloc[0]
                fecha_baja_original = df_historico.loc[mask_historico, 'fecha_baja'].iloc[0]
                
                # Actualizar con datos actuales pero mantener fechas
                fila_actual = df_actual[mask_actual].iloc[0].copy()
                fila_actual['fecha_alta'] = fecha_alta_original
                fila_actual['fecha_baja'] = fecha_baja_original
                
                # Reemplazar en histórico
                df_historico = df_historico[~mask_historico]
                df_historico = pd.concat([df_historico, fila_actual.to_frame().T], ignore_index=True)
        
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

def main():
    """Función principal"""
    
    try:
        # 1. Descargar archivo Excel actual
        archivo_excel = descargar_excel_alg()
        
        # 2. Leer archivo Excel
        print("Procesando archivo Excel...")
        df_actual = pd.read_excel(archivo_excel)
        print(f"Productos en archivo actual: {len(df_actual)}")
        
        # 3. Crear/actualizar CSV equivalente
        archivo_csv = 'data/alg-listado.csv'
        df_actual.to_csv(archivo_csv, index=False)
        print(f"✅ CSV creado: {archivo_csv}")
        
        # 4. Actualizar histórico con fechas de alta/baja
        df_historico = actualizar_historico(df_actual)
        
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
    main()