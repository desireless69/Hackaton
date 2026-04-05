from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd
import numpy as np
import math
import plotly.express as px
from pymavlink import mavutil
import tempfile
import os
import json

app = FastAPI(title="UAV Telemetry Analyzer API")

# --- 1. ПАРСИНГ ТЕЛЕМЕТРІЇ ---
def parse_bin_log(file_path):
    mlog = mavutil.mavlink_connection(file_path)
    gps_data = []
    imu_data = []
    
    while True:
        msg = mlog.recv_match(type=['GPS', 'IMU'], blocking=False)
        if msg is None:
            break
            
        msg_dict = msg.to_dict()
        
        if msg.get_type() == 'GPS' and msg_dict['Status'] >= 3:
            gps_data.append({
                'TimeUS': msg_dict['TimeUS'],
                'Lat': msg_dict['Lat'] / 1e7,
                'Lng': msg_dict['Lng'] / 1e7,
                'Alt': msg_dict['Alt']
            })
            
        elif msg.get_type() == 'IMU':
            imu_data.append({
                'TimeUS': msg_dict['TimeUS'],
                'AccX': msg_dict['AccX'],
                'AccY': msg_dict['AccY'],
                'AccZ': msg_dict['AccZ']
            })

    if not gps_data or not imu_data:
        raise ValueError("У файлі відсутні дані GPS або IMU.")

    df_gps = pd.DataFrame(gps_data).sort_values('TimeUS')
    df_imu = pd.DataFrame(imu_data).sort_values('TimeUS')
    
    df_merged = pd.merge_asof(df_imu, df_gps, on='TimeUS', direction='nearest')
    df_merged = df_merged.dropna(subset=['Lat', 'Lng', 'Alt']).reset_index(drop=True)
    
    t0 = df_merged['TimeUS'].iloc[0]
    df_merged['TimeSec'] = (df_merged['TimeUS'] - t0) / 1e6
    
    return df_merged

# --- 2. ЯДРО АНАЛІТИКИ ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_metrics(df):
    total_distance = sum(
        haversine(df['Lat'].iloc[i-1], df['Lng'].iloc[i-1], df['Lat'].iloc[i], df['Lng'].iloc[i])
        for i in range(1, len(df))
    )
        
    df['dt'] = df['TimeSec'].diff().fillna(0)
    df['AccHoriz'] = np.sqrt(df['AccX']**2 + df['AccY']**2)
    
    velocities = [0.0]
    for i in range(1, len(df)):
        v_curr = velocities[-1] + 0.5 * (df['AccHoriz'].iloc[i] + df['AccHoriz'].iloc[i-1]) * df['dt'].iloc[i]
        velocities.append(v_curr)
        
    df['VelHoriz_IMU'] = velocities
    
    # Збираємо метрики у словник замість print
    metrics = {
        "total_time_sec": round(df['TimeSec'].iloc[-1], 2),
        "max_accel_m_s2": round(df[['AccX', 'AccY', 'AccZ']].abs().max().max(), 2),
        "max_alt_gain_m": round(df['Alt'].max() - df['Alt'].min(), 2),
        "total_distance_m": round(total_distance, 2)
    }
    
    return df, metrics

# --- 3. КОНВЕРТАЦІЯ WGS-84 -> ENU ---
def wgs84_to_enu(df):
    lat0, lon0 = math.radians(df['Lat'].iloc[0]), math.radians(df['Lng'].iloc[0])
    alt0 = df['Alt'].iloc[0]
    R = 6378137.0 
    
    # Векторизована версія для швидкості
    lat_rad = np.radians(df['Lat'])
    lon_rad = np.radians(df['Lng'])
    
    df['X_ENU'] = (lon_rad - lon0) * R * math.cos(lat0)
    df['Y_ENU'] = (lat_rad - lat0) * R
    df['Z_ENU'] = df['Alt'] - alt0
    
    return df

# --- 4. 3D-ВІЗУАЛІЗАЦІЯ (Експорт) ---
def get_trajectory_plot_json(df):
    df_filtered = df.iloc[::20, :].copy()
    fig = px.line_3d(
        df_filtered, x='X_ENU', y='Y_ENU', z='Z_ENU', 
        color='TimeSec', 
        title='3D Траєкторія польоту (ENU координати)',
        labels={'X_ENU': 'Схід (м)', 'Y_ENU': 'Північ (м)', 'Z_ENU': 'Висота (м)', 'TimeSec': 'Час (с)'}
    )
    fig.update_traces(line=dict(width=5))
    fig.update_layout(scene=dict(aspectmode='data'))
    
    # Повертаємо серіалізований JSON графіка
    return fig.to_json()

# --- FASTAPI ЕНДПОЇНТИ ---
@app.post("/analyze-log/")
async def analyze_log_endpoint(file: UploadFile = File(...)):
    if not file.filename.upper().endswith('.BIN'):
        raise HTTPException(status_code=400, detail="Файл має бути формату .BIN")

    # Створюємо тимчасовий файл, бо pymavlink потрібен шлях до файлу
    with tempfile.NamedTemporaryFile(delete=False, suffix=".BIN") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        # Пайплайн обробки
        flight_data = parse_bin_log(temp_file_path)
        flight_data, metrics = calculate_metrics(flight_data)
        flight_data = wgs84_to_enu(flight_data)
        plot_json = get_trajectory_plot_json(flight_data)

        return {
            "filename": file.filename,
            "metrics": metrics,
            "plot_data": json.loads(plot_json) # Передаємо Plotly дані як JSON об'єкт
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Прибираємо за собою
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/")
def read_root():
    return {"message": "UAV Telemetry API працює. Надішли .BIN файл на POST /analyze-log/"}                                     