import pandas as pd
import json
import os
import math
from datetime import datetime

ARCHIVO_DATOS = 'data/data.ods'
ARCHIVO_HISTORIAL = 'data/historial.json'
ARCHIVO_TENDENCIA = 'data/tendencia.json'
DIRECTORIO_SALIDA = 'public/'

def manejar_json(ruta, modo='leer', datos=None):
    if modo == 'leer':
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    else:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

def parsear_fecha(fecha_str):
    try:
        d_str = str(fecha_str).strip().split(' ')[0]
        if '/' in d_str:
            parts = d_str.split('/')
            y = int(parts[2])
            if y < 100: y += 2000
            return datetime(y, int(parts[1]) - 1, int(parts[0]))
        elif '-' in d_str:
            parts = d_str.split('-')
            return datetime(int(parts[0]), int(parts[1]) - 1, int(parts[2]))
    except:
        pass
    return None

def procesar_datos():
    df = pd.read_excel(ARCHIVO_DATOS, engine='odf')
    df.columns = df.columns.str.strip()
    
    historial = manejar_json(ARCHIVO_HISTORIAL, 'leer')
    tendencia = manejar_json(ARCHIVO_TENDENCIA, 'leer')
    datos_frontend = []
    
    col_lat = next((c for c in df.columns if 'lat' in str(c).lower()), None)
    col_lon = next((c for c in df.columns if 'lon' in str(c).lower() or 'lng' in str(c).lower()), None)

    # 1. Encontrar "Hoy" (La fecha máxima del Excel para cálculos)
    fechas_validas = [parsear_fecha(row.get('LastVariable', '')) for _, row in df.iterrows()]
    fechas_validas = [f for f in fechas_validas if f is not None]
    hoy = max(fechas_validas) if fechas_validas else datetime.now()
    hoy_str = hoy.strftime('%Y-%m-%d')

    conteo_tendencia = {"GLOBAL": {"online": 0, "offline": 0, "total": 0}}

    for index, row in df.iterrows():
        maquina_id = str(row.get('Identification', ''))
        if maquina_id == 'nan' or not maquina_id:
            continue
            
        cliente = str(row.get('Customer', '')).strip()
        
        try:
            horometro_actual = float(row.get('HorometerValues', 0.0))
            if math.isnan(horometro_actual): horometro_actual = 0.0
        except:
            horometro_actual = 0.0
            
        fecha_actual = str(row.get('LastVariable', ''))
        f_ultima = parsear_fecha(fecha_actual)
        
        # --- CORRECCIÓN: Migración de Libro Contable ---
        if maquina_id not in historial:
            historial[maquina_id] = {"lecturas": {}}
            
        # Si la máquina existe pero tiene el formato viejo de días pasados, le creamos el nuevo
        if "lecturas" not in historial[maquina_id]:
            historial[maquina_id]["lecturas"] = {}
            
        if f_ultima:
            fecha_str = f_ultima.strftime('%Y-%m-%d')
            # Guarda la lectura en la fecha específica (o la actualiza si es el mismo día)
            historial[maquina_id]["lecturas"][fecha_str] = horometro_actual
        
        # Calcular estado para la bitácora
        estado = "Fuera de cobertura"
        if f_ultima and (hoy - f_ultima).days <= 0:
            estado = "Operando"
        
        # Llenar bitácora GLOBAL
        conteo_tendencia["GLOBAL"]["total"] += 1
        if estado == "Operando": conteo_tendencia["GLOBAL"]["online"] += 1
        else: conteo_tendencia["GLOBAL"]["offline"] += 1
            
        # Llenar bitácora del CLIENTE específico
        if cliente not in conteo_tendencia:
            conteo_tendencia[cliente] = {"online": 0, "offline": 0, "total": 0}
        conteo_tendencia[cliente]["total"] += 1
        if estado == "Operando": conteo_tendencia[cliente]["online"] += 1
        else: conteo_tendencia[cliente]["offline"] += 1
        
        datos_frontend.append({
            'identificacion': maquina_id,
            'cliente': cliente,
            'canal': str(row.get('Channel', '')).strip(),
            'tecnologia': str(row.get('Type', '')).strip(),
            'modelo': str(row.get('Script', '')).strip(),
            'latitud': str(row[col_lat]) if col_lat and pd.notna(row[col_lat]) else '',
            'longitud': str(row[col_lon]) if col_lon and pd.notna(row[col_lon]) else '',
            'horometro_total': horometro_actual,
            'lecturas_historicas': historial[maquina_id].get("lecturas", {}),
            'ultima_conexion': fecha_actual
        })

    manejar_json(ARCHIVO_HISTORIAL, 'escribir', historial)

    # 2. Guardar la Bitácora de conectividad
    for clave, conteos in conteo_tendencia.items():
        if clave not in tendencia: tendencia[clave] = []
        registro_existente = next((item for item in tendencia[clave] if item["fecha"] == hoy_str), None)
        if registro_existente:
            registro_existente.update(conteos)
        else:
            tendencia[clave].append({"fecha": hoy_str, **conteos})
            
    manejar_json(ARCHIVO_TENDENCIA, 'escribir', tendencia)
    manejar_json(f"{DIRECTORIO_SALIDA}tendencia.json", 'escribir', tendencia)

    # 3. Exportar JSONs
    df_limpio = pd.DataFrame(datos_frontend)
    for c in df_limpio['cliente'].unique():
        if pd.isna(c) or c == 'nan': continue
        df_cliente = df_limpio[df_limpio['cliente'] == c]
        df_cliente.to_json(f"{DIRECTORIO_SALIDA}{c.replace(' ', '_').replace('/', '_').lower()}.json", orient='records', force_ascii=False)
    
    df_limpio.to_json(f"{DIRECTORIO_SALIDA}consolidado_general.json", orient='records', force_ascii=False)

if __name__ == '__main__':
    procesar_datos()
