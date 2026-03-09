import pandas as pd
import numpy as np

def analyze_coordinates(csv_file):
    # 讀取CSV檔案
    df = pd.read_csv(csv_file)
    
    print("=== 座標品質分析報告 ===")
    print(f"總資料筆數: {len(df)}")
    print(f"欄位: {list(df.columns)}")
    
    # 檢查經緯度欄位
    lon_col = '經度'
    lat_col = '緯度'
    
    # 基本統計
    print(f"\n=== 經度基本統計 ===")
    print(df[lon_col].describe())
    print(f"\n=== 緯度基本統計 ===")
    print(df[lat_col].describe())
    
    # 檢查座標系統
    print(f"\n=== 座標系統判斷 ===")
    
    # 台灣經緯度範圍 (EPSG:4326)
    # 經度: 119-123度, 緯度: 21-26度
    tw_lon_min, tw_lon_max = 119, 123
    tw_lat_min, tw_lat_max = 21, 26
    
    # 台灣二度分帶範圍 (EPSG:3826)
    # 經度: 170000-330000, 緯度: 2400000-2800000
    twd97_lon_min, twd97_lon_max = 170000, 330000
    twd97_lat_min, twd97_lat_max = 2400000, 2800000
    
    # 判斷座標系統
    lat_lon_count = 0
    twd97_count = 0
    zero_count = 0
    
    for idx, row in df.iterrows():
        lon = row[lon_col]
        lat = row[lat_col]
        
        # 檢查是否為0或空值
        if pd.isna(lon) or pd.isna(lat) or lon == 0 or lat == 0:
            zero_count += 1
            continue
            
        # 檢查是否為經緯度
        if (tw_lon_min <= lon <= tw_lon_max) and (tw_lat_min <= lat <= tw_lat_max):
            lat_lon_count += 1
        # 檢查是否為二度分帶
        elif (twd97_lon_min <= lon <= twd97_lon_max) and (twd97_lat_min <= lat <= twd97_lat_max):
            twd97_count += 1
        else:
            print(f"異常座標 - 索引{idx}: 經度={lon}, 緯度={lat}")
    
    print(f"經緯度座標 (EPSG:4326): {lat_lon_count} 筆")
    print(f"二度分帶座標 (EPSG:3826): {twd97_count} 筆")
    print(f"零值或空值: {zero_count} 筆")
    
    # 檢查是否有混用情況
    if lat_lon_count > 0 and twd97_count > 0:
        print("\n[警告] 發現座標系統混用情況！")
    elif lat_lon_count > 0:
        print("\n[OK] 使用經緯度座標系統 (EPSG:4326)")
    elif twd97_count > 0:
        print("\n[OK] 使用二度分帶座標系統 (EPSG:3826)")
    
    # 離群值檢測
    print(f"\n=== 離群值檢測 ===")
    
    outliers = []
    for idx, row in df.iterrows():
        lon = row[lon_col]
        lat = row[lat_col]
        
        if pd.isna(lon) or pd.isna(lat):
            continue
            
        # 檢查是否為 (0,0)
        if lon == 0 and lat == 0:
            outliers.append(f"索引{idx}: (0,0) 座標")
        # 檢查是否在台灣範圍外 (經緯度)
        elif (tw_lon_min <= lon <= tw_lon_max) and (tw_lat_min <= lat <= tw_lat_max):
            continue
        # 檢查是否在台灣範圍外 (二度分帶)
        elif (twd97_lon_min <= lon <= twd97_lon_max) and (twd97_lat_min <= lat <= twd97_lat_max):
            continue
        else:
            outliers.append(f"索引{idx}: 經度={lon}, 緯度={lat} (超出台灣範圍)")
    
    if outliers:
        print(f"發現 {len(outliers)} 個離群值:")
        for outlier in outliers[:10]:  # 只顯示前10個
            print(f"  - {outlier}")
        if len(outliers) > 10:
            print(f"  ... 還有 {len(outliers) - 10} 個離群值")
    else:
        print("[OK] 未發現明顯離群值")
    
    return {
        'total_records': len(df),
        'lat_lon_count': lat_lon_count,
        'twd97_count': twd97_count,
        'zero_count': zero_count,
        'outliers': outliers,
        'has_mixing': lat_lon_count > 0 and twd97_count > 0
    }

if __name__ == "__main__":
    csv_file = "data/避難收容處所點位檔案v9.csv"
    results = analyze_coordinates(csv_file)
