import requests
import folium
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
import urllib3

# 禁用 SSL 警告（僅用於開發環境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 載入環境變數
load_dotenv()

class CombinedMapGenerator:
    def __init__(self):
        self.api_key = os.getenv('MOENV_API_KEY')
        if not self.api_key or self.api_key == 'your_moenv_api_key_here':
            raise ValueError("請在 .env 檔案中設定正確的 MOENV_API_KEY")
        
        self.api_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432"
        self.aqi_data = None
        self.shelter_data = None
        
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
        print(f"原始數據: {original_count} 筆")
        
        # 過濾條件
        filtered_data = self.shelter_data.copy()
        
        # 1. 移除經緯度為 (0,0) 的記錄
        filtered_data = filtered_data[
            ~((filtered_data['經度'] == 0) & (filtered_data['緯度'] == 0))
        ]
        zero_count = original_count - len(filtered_data)
        
        # 2. 移除經緯度為空值的記錄
        filtered_data = filtered_data[
            filtered_data['經度'].notna() & 
            filtered_data['緯度'].notna()
        ]
        null_count = original_count - zero_count - len(filtered_data)
        
        # 3. 移除明顯在海中的座標（台灣本島及離島的合理範圍）
        # 台灣本島及主要離島的經緯度範圍
        valid_lon_min, valid_lon_max = 117, 123
        valid_lat_min, valid_lat_max = 21, 27
        
        filtered_data = filtered_data[
            (filtered_data['經度'] >= valid_lon_min) & 
            (filtered_data['經度'] <= valid_lon_max) &
            (filtered_data['緯度'] >= valid_lat_min) & 
            (filtered_data['緯度'] <= valid_lat_max)
        ]
        invalid_geo_count = original_count - zero_count - null_count - len(filtered_data)
        
        print(f"過濾後數據: {len(filtered_data)} 筆")
        print(f"  - 移除 (0,0) 座標: {zero_count} 筆")
        print(f"  - 移除空值座標: {null_count} 筆")
        print(f"  - 移除無效地理範圍: {invalid_geo_count} 筆")
        
        # 統計室內外分布
        indoor_count = filtered_data['is_indoor'].sum()
        outdoor_count = len(filtered_data) - indoor_count
        print(f"  - 室內場所: {indoor_count} 筆")
        print(f"  - 室外場所: {outdoor_count} 筆")
        
        return filtered_data
    
    def get_aqi_color(self, aqi_value):
        """根據 AQI 數值回傳對應顏色"""
        try:
            aqi = int(aqi_value)
        except (ValueError, TypeError):
            return 'gray'
        
        if aqi <= 50:
            return 'green'      # 良好
        elif aqi <= 100:
            return 'yellow'     # 中等
        elif aqi <= 150:
            return 'orange'     # 對敏感族群不健康
        elif aqi <= 200:
            return 'red'        # 對所有族群不健康
        elif aqi <= 300:
            return 'purple'     # 非常不健康
        else:
            return 'maroon'      # 危害
    
    def create_combined_map(self):
        """創建 AQI 和避難收容處所的綜合地圖"""
        if self.aqi_data is None or len(self.aqi_data) == 0:
            print("沒有可用的 AQI 數據")
            return None
        
        if self.shelter_data is None:
            print("沒有可用的避難收容處所數據")
            return None
        
        # 過濾避難收容處所數據
        filtered_shelters = self.filter_shelter_data()
        if filtered_shelters is None or len(filtered_shelters) == 0:
            print("沒有有效的避難收容處所數據")
            return None
        
        # 計算地圖中心點（基於所有數據點）
        all_lats = []
        all_lons = []
        
        # 添加 AQI 測站座標
        valid_aqi = self.aqi_data[
            self.aqi_data['latitude'].notna() & 
            self.aqi_data['longitude'].notna()
        ]
        valid_aqi = valid_aqi.copy()
        valid_aqi['latitude'] = pd.to_numeric(valid_aqi['latitude'], errors='coerce')
        valid_aqi['longitude'] = pd.to_numeric(valid_aqi['longitude'], errors='coerce')
        valid_aqi = valid_aqi.dropna(subset=['latitude', 'longitude'])
        
        all_lats.extend(valid_aqi['latitude'].tolist())
        all_lons.extend(valid_aqi['longitude'].tolist())
        
        # 添加避難收容處所座標
        all_lats.extend(filtered_shelters['緯度'].tolist())
        all_lons.extend(filtered_shelters['經度'].tolist())
        
        if len(all_lats) == 0:
            print("沒有有效的座標數據")
            return None
        
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
        
        # 創建地圖
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles='OpenStreetMap'
        )
        
        # 添加 AQI 測站標記
        print("正在添加 AQI 測站...")
        for idx, station in valid_aqi.iterrows():
            try:
                lat = float(station['latitude'])
                lon = float(station['longitude'])
                
                # 獲取測站資訊
                site_name = station.get('sitename', '未知測站')
                aqi = station.get('aqi', 'N/A')
                pollutant = station.get('pollutant', 'N/A')
                status = station.get('status', 'N/A')
                county = station.get('county', 'N/A')
                
                # 獲取顏色
                color = self.get_aqi_color(aqi) if aqi != 'N/A' else 'gray'
                
                # 創建彈出視窗內容
                popup_content = f"""
                <b><span style="color: blue;">AQI 測站</span></b><br>
                <b>{site_name}</b><br>
                縣市: {county}<br>
                AQI: <span style="color: {color}; font-weight: bold;">{aqi}</span><br>
                狀態: {status}<br>
                主要污染物: {pollutant}
                """
                
                # 創建圓形標記
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=6,
                    popup=folium.Popup(popup_content, max_width=200),
                    color='black',
                    fillColor=color,
                    fillOpacity=0.8,
                    weight=1
                ).add_to(m)
                
            except (ValueError, TypeError) as e:
                print(f"跳過無效 AQI 座標數據: {station.get('sitename', '未知')}")
                continue
        
        # 添加避難收容處所標記
        print("正在添加避難收容處所...")
        for idx, shelter in filtered_shelters.iterrows():
            try:
                lat = float(shelter['緯度'])
                lon = float(shelter['經度'])
                
                # 獲取收容處所資訊
                name = shelter.get('避難收容處所名稱', '未知收容處所')
                address = shelter.get('避難收容處所地址', '地址未知')
                county = shelter.get('縣市及鄉鎮市區', '未知縣市')
                capacity = shelter.get('預計收容人數', 'N/A')
                is_indoor = shelter.get('is_indoor', False)
                
                # 根據室內外決定圖標樣式
                if is_indoor:
                    # 室內場所 - 使用藍色方形
                    icon_color = 'blue'
                    icon_symbol = '🏢'
                    marker_type = 'square'
                else:
                    # 室外場所 - 使用綠色方形
                    icon_color = 'green'
                    icon_symbol = '🏞️'
                    marker_type = 'square'
                
                # 創建彈出視窗內容
                popup_content = f"""
                <b><span style="color: {icon_color};">避難收容處所</span></b><br>
                <b>{name}</b><br>
                類型: {'室內' if is_indoor else '室外'} {icon_symbol}<br>
                地址: {address}<br>
                縣市: {county}<br>
                預計收容人數: {capacity}
                """
                
                # 創建不同的標記樣式
                # 統一使用方形標記，用顏色區分室內外
                folium.RegularPolygonMarker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_content, max_width=200),
                    number_of_sides=4,
                    radius=5,
                    rotation=45,
                    color='black',
                    fillColor=icon_color,
                    fillOpacity=0.7,
                    weight=1
                ).add_to(m)
                
            except (ValueError, TypeError) as e:
                print(f"跳過無效避難收容處所座標數據: {shelter.get('避難收容處所名稱', '未知')}")
                continue
        
        # 添加圖例
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 280px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px">
        <h4>圖例說明</h4>
        <b><span style="color: blue;">AQI 測站</span></b><br>
        <i class="fa fa-circle" style="color:green"></i> 0-50 良好<br>
        <i class="fa fa-circle" style="color:yellow"></i> 51-100 中等<br>
        <i class="fa fa-circle" style="color:orange"></i> 101-150 對敏感族群不健康<br>
        <i class="fa fa-circle" style="color:red"></i> 151-200 對所有族群不健康<br>
        <i class="fa fa-circle" style="color:purple"></i> 201-300 非常不健康<br>
        <i class="fa fa-circle" style="color:maroon"></i> 300+ 危害<br>
        <br>
        <b><span style="color: blue;">避難收容處所</span></b><br>
        <i class="fa fa-square" style="color:blue"></i> 室內場所 🏢<br>
        <i class="fa fa-square" style="color:green"></i> 室外場所 🏞️
        </div>
        '''
        
        m.get_root().html.add_child(folium.Element(legend_html))
        
        return m
    
    def save_map(self, map_obj, filename='outputs/combined_map.html'):
        """保存地圖"""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            map_obj.save(filename)
            print(f"綜合地圖已保存至: {filename}")
            return True
        except Exception as e:
            print(f"保存地圖失敗: {e}")
            return False
    
    def run(self):
        """執行完整流程"""
        print("=== 台灣 AQI 與避難收容處所綜合地圖生成器 ===")
        print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 獲取 AQI 數據
        if not self.fetch_aqi_data():
            return False
        
        # 載入避難收容處所數據
        csv_file = "data/避難收容處所點位檔案v9.csv"
        if not self.load_shelter_data(csv_file):
            return False
        
        # 創建綜合地圖
        combined_map = self.create_combined_map()
        if combined_map is None:
            return False
        
        # 保存地圖
        return self.save_map(combined_map)

def main():
    """主程式"""
    try:
        generator = CombinedMapGenerator()
        success = generator.run()
        
        if success:
            print("\n[成功] 綜合地圖生成成功！")
            print("請開啟 outputs/combined_map.html 查看地圖")
        else:
            print("\n[失敗] 綜合地圖生成失敗")
            
    except ValueError as e:
        print(f"[設定錯誤] {e}")
        print("請檢查 .env 檔案中的 API Key 設定")
    except Exception as e:
        print(f"[程式錯誤] {e}")

if __name__ == "__main__":
    main()
