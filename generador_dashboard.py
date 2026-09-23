import pandas as pd
import json
import os
import math

ARCHIVO_DATOS = 'data/data.ods'
ARCHIVO_HISTORIAL = 'data/historial.json'
DIRECTORIO_SALIDA = 'public/'

def cargar_historial():
    if os.path.exists(ARCHIVO_HISTORIAL):
        with open(ARCHIVO_HISTORIAL, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_historial(historial):
    with open(ARCHIVO_HISTORIAL, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=4)

def procesar_datos():
    df = pd.read_excel(ARCHIVO_DATOS, engine='odf')
    df.columns = df.columns.str.strip()
    
    historial = cargar_historial()
    datos_frontend = []

    # Buscar columnas de coordenadas flexiblemente (Latitud, Longitude, Lng, etc.)
    col_lat = next((c for c in df.columns if c.lower() in ['latitude', 'latitud', 'lat']), None)
    col_lon = next((c for c in df.columns if c.lower() in ['longitude', 'longitud', 'lon', 'lng']), None)

    for index, row in df.iterrows():
        maquina_id = str(row.get('Identification', ''))
        if maquina_id == 'nan' or not maquina_id:
            continue
            
        try:
            horometro_actual = float(row.get('HorometerValues', 0.0))
            if math.isnan(horometro_actual):
                horometro_actual = 0.0
        except:
            horometro_actual = 0.0
            
        fecha_actual = str(row.get('LastVariable', ''))
        horas_operadas = 0.0
        
        if maquina_id in historial:
            horometro_anterior = historial[maquina_id]['ultimo_horometro']
            if horometro_actual > horometro_anterior:
                horas_operadas = horometro_actual - horometro_anterior
        
        historial[maquina_id] = {
            'ultimo_horometro': horometro_actual,
            'ultima_fecha': fecha_actual
        }
        
        # Extracción segura de coordenadas
        lat_val = str(row[col_lat]) if col_lat else ''
        lon_val = str(row[col_lon]) if col_lon else ''
        
        datos_frontend.append({
            'identificacion': maquina_id,
            'cliente': str(row.get('Customer', '')).strip(),
            'canal': str(row.get('Channel', '')).strip(),
            'tecnologia': str(row.get('Type', '')).strip(),
            'modelo': str(row.get('Script', '')).strip(),
            'latitud': lat_val,
            'longitud': lon_val,
            'horometro_total': horometro_actual,
            'horas_recientes': horas_operadas,
            'ultima_conexion': fecha_actual
        })

    guardar_historial(historial)

    df_limpio = pd.DataFrame(datos_frontend)
    clientes = df_limpio['cliente'].unique()
    
    for cliente in clientes:
        if pd.isna(cliente) or cliente == 'nan':
            continue
        df_cliente = df_limpio[df_limpio['cliente'] == cliente]
        nombre_archivo = f"{DIRECTORIO_SALIDA}{cliente.replace(' ', '_').replace('/', '_').lower()}.json"
        df_cliente.to_json(nombre_archivo, orient='records', force_ascii=False)

    df_limpio.to_json(f"{DIRECTORIO_SALIDA}consolidado_general.json", orient='records', force_ascii=False)

if __name__ == '__main__':
    procesar_datos()
