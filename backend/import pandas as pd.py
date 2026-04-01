import pandas as pd
import numpy as np
import math
import plotly.express as px
from pymavlink import mavutil
import plotly.io as pio
from pathlib import Path

# --- 0. ПІДГОТОВКА ВІДНОСНОГО ШЛЯХУ ---

current_dir = Path(".")

# --- 1. ПАРСИНГ ТЕЛЕМЕТРІЇ (Data Parsing) ---
def parse_bin_log(file_path):
    """
    Читає .BIN файл та витягує повідомлення GPS та IMU у pandas DataFrame.
    """
    mlog = mavutil.mavlink_connection(file_path)
    
    gps_data = []
    imu_data = []
    
    while True:
        msg = mlog.recv_match(type=['GPS', 'IMU'], blocking=False)
        if msg is None:
            break
            
        msg_dict = msg.to_dict()
        
        if msg.get_type() == 'GPS' and msg_dict['Status'] >= 3: # Беремо лише 3D Fix
            gps_data.append({
                'TimeUS': msg_dict['TimeUS'],
                'Lat': msg_dict['Lat'] / 1e7,  # Конвертація у градуси
                'Lng': msg_dict['Lng'] / 1e7,
                'Alt': msg_dict['Alt']         # Висота (метри)
            })
            
        elif msg.get_type() == 'IMU':
            imu_data.append({
                'TimeUS': msg_dict['TimeUS'],
                'AccX': msg_dict['AccX'],      # Прискорення (м/с^2)
                'AccY': msg_dict['AccY'],
                'AccZ': msg_dict['AccZ']
            })

    # Створюємо DataFrame
    df_gps = pd.DataFrame(gps_data)
    df_imu = pd.DataFrame(imu_data)
    
    # Оскільки датчики мають різну частоту семплювання, об'єднуємо їх за найближчим часом
    df_gps = df_gps.sort_values('TimeUS')
    df_imu = df_imu.sort_values('TimeUS')
    df_merged = pd.merge_asof(df_imu, df_gps, on='TimeUS', direction='nearest')
    
    # Видаляємо рядки без GPS (до фіксації супутників)
    df_merged = df_merged.dropna(subset=['Lat', 'Lng', 'Alt']).reset_index(drop=True)
    
    # Переводимо час з мікросекунд у секунди від початку логу
    t0 = df_merged['TimeUS'].iloc[0]
    df_merged['TimeSec'] = (df_merged['TimeUS'] - t0) / 1e6
    
    return df_merged

# --- 2. ЯДРО АНАЛІТИКИ: Математика та інтегрування ---
def haversine(lat1, lon1, lat2, lon2):
    """
    Обчислює відстань між двома точками на сфері (Землі) за їхніми координатами.
    """
    R = 6371000  # Радіус Землі в метрах
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_metrics(df):
    """
    Обчислення підсумкових показників місії.
    """
    # 1. Загальна пройдена дистанція (Haversine)
    total_distance = 0.0
    for i in range(1, len(df)):
        total_distance += haversine(df['Lat'].iloc[i-1], df['Lng'].iloc[i-1], 
                                    df['Lat'].iloc[i], df['Lng'].iloc[i])
        
    # 2. Швидкість через метод трапецій (інтегрування прискорення)
    # Зверни увагу: сире інтегрування IMU дасть значний дрейф (похибку), 
    # це варто описати в теоретичному обґрунтуванні!
    df['dt'] = df['TimeSec'].diff().fillna(0)
    
    # Проєкція горизонтального прискорення (спрощено)
    df['AccHoriz'] = np.sqrt(df['AccX']**2 + df['AccY']**2)
    
    # v(t) = v(t-1) + 0.5 * (a(t) + a(t-1)) * dt
    velocities = [0.0]
    for i in range(1, len(df)):
        v_prev = velocities[-1]
        a_curr = df['AccHoriz'].iloc[i]
        a_prev = df['AccHoriz'].iloc[i-1]
        dt = df['dt'].iloc[i]
        
        v_curr = v_prev + 0.5 * (a_curr + a_prev) * dt
        velocities.append(v_curr)
        
    df['VelHoriz_IMU'] = velocities
    
    max_accel = df[['AccX', 'AccY', 'AccZ']].abs().max().max()
    max_alt_gain = df['Alt'].max() - df['Alt'].min()
    total_time = df['TimeSec'].iloc[-1]
    
    print("--- Підсумкові метрики польоту ---")
    print(f"Тривалість польоту: {total_time:.2f} с")
    print(f"Максимальне прискорення: {max_accel:.2f} м/с^2")
    print(f"Максимальний набір висоти: {max_alt_gain:.2f} м")
    print(f"Пройдена дистанція (Haversine): {total_distance:.2f} м")
    
    return df

# --- 3. КОНВЕРТАЦІЯ WGS-84 -> ENU ---
def wgs84_to_enu(df):
    """
    Переводить глобальні координати у локальну декартову систему (метри від старту).
    Використовується наближення плоскої Землі (достатньо для локальних польотів БПЛА).
    """
    lat0 = math.radians(df['Lat'].iloc[0])
    lon0 = math.radians(df['Lng'].iloc[0])
    alt0 = df['Alt'].iloc[0]
    R = 6378137.0 # Екваторіальний радіус Землі
    
    x_enu, y_enu, z_enu = [], [], []
    
    for _, row in df.iterrows():
        lat = math.radians(row['Lat'])
        lon = math.radians(row['Lng'])
        
        d_lon = lon - lon0
        d_lat = lat - lat0
        
        x = d_lon * R * math.cos(lat0) # Схід (East)
        y = d_lat * R                  # Північ (North)
        z = row['Alt'] - alt0          # Вгору (Up)
        
        x_enu.append(x)
        y_enu.append(y)
        z_enu.append(z)
        
    df['X_ENU'] = x_enu
    df['Y_ENU'] = y_enu
    df['Z_ENU'] = z_enu
    
    return df

# --- 4. 3D-ВІЗУАЛІЗАЦІЯ ---
def plot_trajectory(df):
    """
    Будує інтерактивний 3D-графік просторової траєкторії.
    """
    pio.renderers.default = "browser" # Або "vscode" чи "browser"
    df_filtered = df.iloc[::20, :].copy()
    fig = px.line_3d(df_filtered, x='X_ENU', y='Y_ENU', z='Z_ENU', 
                     color='TimeSec', # Динамічне колорування за плином часу
                     title='3D Траєкторія польоту (ENU координати)',
                     labels={'X_ENU': 'Схід (м)', 'Y_ENU': 'Північ (м)', 'Z_ENU': 'Висота (м)', 'TimeSec': 'Час (с)'})
    
    fig.update_traces(line=dict(width=5))
    fig.update_layout(scene=dict(aspectmode='data')) # Зберігає реальні пропорції осей
    fig.show()

# --- ГОЛОВНИЙ БЛОК ---
if __name__ == "__main__":
    log_file = current_dir / "bin" / "00000001.BIN" # Заміни на шлях до свого файлу
    
    print("Парсинг логу...")
    flight_data = parse_bin_log(log_file)
    
    print("Обчислення метрик та інтегрування...")
    flight_data = calculate_metrics(flight_data)
    
    print("Конвертація систем координат...")
    flight_data = wgs84_to_enu(flight_data)
    
    print("Побудова 3D моделі...")
    plot_trajectory(flight_data)