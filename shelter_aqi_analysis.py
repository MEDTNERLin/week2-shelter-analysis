import requests
import folium
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
import urllib3
import math

# 禁用 SSL 警告（僅用於開發環境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 載入環境變數
load_dotenv()

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    使用 Haversine 公式計算兩點間的距離（公里）
    """
    # 將經緯度轉換為弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine 公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # 地球半徑（公里）
    r = 6371
    return c * r

class ShelterAQIAnalysis:
    def __init__(self):
        self.api_key = os.getenv('MOENV_API_KEY')
        if not self.api_key or self.api_key == 'your_moenv_api_key_here':
            raise ValueError("請在 .env 檔案中設定正確的 MOENV_API_KEY")
        
        self.api_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432"
        self.aqi_data = None
        self.shelter_data = None
        self.analysis_results = None
        
    def fetch_aqi_data(self):
        """獲取全台即時 AQI 數據"""
        try:
            params = {
                'api_key': self.api_key,
                'format': 'json'
            }
            
            print("正在獲取空氣品質數據...")
            response = requests.get(self.api_url, params=params, timeout=30, verify=False)
            response.raise_for_status()
            
            data = response.json()
            
            # 檢查數據格式
            if isinstance(data, list) and len(data) > 0:
                # 直接使用列表數據
                self.aqi_data = pd.DataFrame(data)
                print(f"成功獲取 {len(self.aqi_data)} 個測站數據")
                return True
            elif isinstance(data, dict) and 'records' in data:
                # 使用字典中的 records
                self.aqi_data = pd.DataFrame(data['records'])
                print(f"成功獲取 {len(self.aqi_data)} 個測站數據")
                return True
            else:
                print("API 回應格式錯誤")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"API 請求失敗: {e}")
            return False
        except Exception as e:
            print(f"獲取數據時發生錯誤: {e}")
            return False
    
    def modify_kaohsiung_aqi(self):
        """手動將高雄測站的 AQI 值設為 150"""
        if self.aqi_data is None:
            return False
        
        print("正在修改高雄測站的 AQI 值...")
        
        # 找到高雄相關測站
        kaohsiung_stations = self.aqi_data[
            self.aqi_data['county'].str.contains('高雄', na=False)
        ].copy()
        
        if len(kaohsiung_stations) > 0:
            print(f"找到 {len(kaohsiung_stations)} 個高雄測站:")
            for idx, station in kaohsiung_stations.iterrows():
                original_aqi = station.get('aqi', 'N/A')
                station_name = station.get('sitename', '未知')
                print(f"  - {station_name}: {original_aqi} -> 150")
                
                # 修改 AQI 值
                self.aqi_data.loc[idx, 'aqi'] = '150'
                # 修改狀態
                self.aqi_data.loc[idx, 'status'] = '對所有族群不健康'
            
            return True
        else:
            print("未找到高雄測站")
            return False
    
    def load_shelter_data(self, csv_file):
        """載入避難收容處所數據"""
        try:
            print("正在載入避難收容處所數據...")
            self.shelter_data = pd.read_csv(csv_file)
            print(f"成功載入 {len(self.shelter_data)} 筆避難收容處所數據")
            return True
        except Exception as e:
            print(f"載入避難收容處所數據失敗: {e}")
            return False
    
    def filter_shelter_data(self):
        """過濾無效的避難收容處所數據"""
        if self.shelter_data is None:
            return None
        
        print("正在過濾無效的避難收容處所數據...")
        
        # 原始數據統計
        original_count = len(self.shelter_data)
        
        # 過濾條件
        filtered_data = self.shelter_data.copy()
        
        # 1. 移除經緯度為 (0,0) 的記錄
        filtered_data = filtered_data[
            ~((filtered_data['經度'] == 0) & (filtered_data['緯度'] == 0))
        ]
        
        # 2. 移除經緯度為空值的記錄
        filtered_data = filtered_data[
            filtered_data['經度'].notna() & 
            filtered_data['緯度'].notna()
        ]
        
        # 3. 移除明顯在海中的座標
        valid_lon_min, valid_lon_max = 117, 123
        valid_lat_min, valid_lat_max = 21, 27
        
        filtered_data = filtered_data[
            (filtered_data['經度'] >= valid_lon_min) & 
            (filtered_data['經度'] <= valid_lon_max) &
            (filtered_data['緯度'] >= valid_lat_min) & 
            (filtered_data['緯度'] <= valid_lat_max)
        ]
        
        print(f"過濾後數據: {len(filtered_data)} 筆")
        return filtered_data
    
    def find_nearest_aqi_stations(self):
        """為每個避難收容處所找到最近的 AQI 測站"""
        if self.aqi_data is None or self.shelter_data is None:
            return None
        
        print("正在為每個避難收容處所找到最近的 AQI 測站...")
        
        # 過濾避難收容處所數據
        filtered_shelters = self.filter_shelter_data()
        if filtered_shelters is None or len(filtered_shelters) == 0:
            return None
        
        # 準備 AQI 測站數據
        valid_aqi = self.aqi_data[
            self.aqi_data['latitude'].notna() & 
            self.aqi_data['longitude'].notna()
        ].copy()
        
        valid_aqi['latitude'] = pd.to_numeric(valid_aqi['latitude'], errors='coerce')
        valid_aqi['longitude'] = pd.to_numeric(valid_aqi['longitude'], errors='coerce')
        valid_aqi = valid_aqi.dropna(subset=['latitude', 'longitude'])
        
        # 確保 AQI 值為數值
        valid_aqi['aqi_numeric'] = pd.to_numeric(valid_aqi['aqi'], errors='coerce')
        valid_aqi = valid_aqi.dropna(subset=['aqi_numeric'])
        
        print(f"有效的 AQI 測站: {len(valid_aqi)} 個")
        print(f"有效的避難收容處所: {len(filtered_shelters)} 個")
        
        # 分析結果
        results = []
        
        for idx, shelter in filtered_shelters.iterrows():
            try:
                shelter_lat = float(shelter['緯度'])
                shelter_lon = float(shelter['經度'])
                
                # 計算到每個 AQI 測站的距離
                min_distance = float('inf')
                nearest_station = None
                nearest_aqi = None
                
                for _, station in valid_aqi.iterrows():
                    station_lat = float(station['latitude'])
                    station_lon = float(station['longitude'])
                    
                    # 使用 Haversine 公式計算距離
                    distance = haversine_distance(shelter_lat, shelter_lon, station_lat, station_lon)
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_station = station
                        nearest_aqi = float(station['aqi_numeric'])
                
                # 分類風險等級
                risk_level = "Normal"
                if nearest_aqi > 100:
                    risk_level = "High Risk"
                elif nearest_aqi > 50 and not shelter.get('is_indoor', False):
                    risk_level = "Warning"
                
                # 建立結果記錄
                result = {
                    '避難收容處所名稱': shelter.get('避難收容處所名稱', '未知'),
                    '縣市及鄉鎮市區': shelter.get('縣市及鄉鎮市區', '未知'),
                    '避難收容處所地址': shelter.get('避難收容處所地址', '未知'),
                    '經度': shelter.get('經度'),
                    '緯度': shelter.get('緯度'),
                    'is_indoor': shelter.get('is_indoor', False),
                    '預計收容人數': shelter.get('預計收容人數', 'N/A'),
                    '最近AQI測站': nearest_station.get('sitename', '未知') if nearest_station is not None else 'N/A',
                    '測站縣市': nearest_station.get('county', '未知') if nearest_station is not None else 'N/A',
                    '最近AQI值': nearest_aqi if nearest_aqi is not None else 'N/A',
                    '測站狀態': nearest_station.get('status', '未知') if nearest_station is not None else 'N/A',
                    '距離(km)': round(min_distance, 2) if min_distance != float('inf') else 'N/A',
                    '風險等級': risk_level
                }
                
                results.append(result)
                
            except (ValueError, TypeError) as e:
                print(f"處理避難收容處所時發生錯誤: {shelter.get('避難收容處所名稱', '未知')}")
                continue
        
        self.analysis_results = pd.DataFrame(results)
        print(f"完成 {len(results)} 個避難收容處所的分析")
        
        return self.analysis_results
    
    def save_analysis_results(self, filename='outputs/shelter_aqi_analysis.csv'):
        """保存分析結果"""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            self.analysis_results.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"分析結果已保存至: {filename}")
            return True
        except Exception as e:
            print(f"保存分析結果失敗: {e}")
            return False
    
    def print_summary(self):
        """印出分析摘要"""
        if self.analysis_results is None:
            return
        
        print("\n=== 分析摘要 ===")
        print(f"總分析處所數量: {len(self.analysis_results)}")
        
        # 風險等級統計
        risk_counts = self.analysis_results['風險等級'].value_counts()
        print("\n風險等級分布:")
        for level, count in risk_counts.items():
            percentage = (count / len(self.analysis_results)) * 100
            print(f"  {level}: {count} 個 ({percentage:.1f}%)")
        
        # 室內外統計
        indoor_outdoor_counts = self.analysis_results['is_indoor'].value_counts()
        print("\n室內外分布:")
        for is_indoor, count in indoor_outdoor_counts.items():
            label = "室內" if is_indoor else "室外"
            percentage = (count / len(self.analysis_results)) * 100
            print(f"  {label}: {count} 個 ({percentage:.1f}%)")
        
        # 高風險處所統計
        high_risk = self.analysis_results[self.analysis_results['風險等級'] == 'High Risk']
        if len(high_risk) > 0:
            print(f"\n高風險處所數量: {len(high_risk)} 個")
            print("前10個高風險處所:")
            for idx, row in high_risk.head(10).iterrows():
                print(f"  - {row['避難收容處所名稱']} (AQI: {row['最近AQI值']}, 距離: {row['距離(km)']}km)")
    
    def run(self):
        """執行完整流程"""
        print("=== 避難收容處所 AQI 風險分析 ===")
        print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 獲取 AQI 數據
        if not self.fetch_aqi_data():
            return False
        
        # 修改高雄測站 AQI 值
        if not self.modify_kaohsiung_aqi():
            return False
        
        # 載入避難收容處所數據
        csv_file = "data/避難收容處所點位檔案v9.csv"
        if not self.load_shelter_data(csv_file):
            return False
        
        # 分析避難收容處所
        if self.find_nearest_aqi_stations() is None:
            return False
        
        # 保存結果
        if not self.save_analysis_results():
            return False
        
        # 印出摘要
        self.print_summary()
        
        return True

def main():
    """主程式"""
    try:
        analyzer = ShelterAQIAnalysis()
        success = analyzer.run()
        
        if success:
            print("\n[成功] 避難收容處所 AQI 風險分析完成！")
            print("分析結果已保存至 outputs/shelter_aqi_analysis.csv")
        else:
            print("\n[失敗] 分析失敗")
            
    except ValueError as e:
        print(f"[設定錯誤] {e}")
        print("請檢查 .env 檔案中的 API Key 設定")
    except Exception as e:
        print(f"[程式錯誤] {e}")

if __name__ == "__main__":
    main()
