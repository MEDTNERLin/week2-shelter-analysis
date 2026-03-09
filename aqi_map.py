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

class AQIMapGenerator:
    def __init__(self):
        self.api_key = os.getenv('MOENV_API_KEY')
        if not self.api_key or self.api_key == 'your_moenv_api_key_here':
            raise ValueError("請在 .env 檔案中設定正確的 MOENV_API_KEY")
        
        self.api_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432"
        self.aqi_data = None
        
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
            print(f"API 回應狀態: {response.status_code}")
            print(f"API 回應類型: {type(data)}")
            
            # 檢查數據格式
            if isinstance(data, list) and len(data) > 0:
                # 直接使用列表數據
                self.aqi_data = pd.DataFrame(data)
                print(f"成功獲取 {len(self.aqi_data)} 個測站數據")
                print(f"可用欄位: {list(self.aqi_data.columns)}")
                return True
            elif isinstance(data, dict) and 'records' in data:
                # 使用字典中的 records
                self.aqi_data = pd.DataFrame(data['records'])
                print(f"成功獲取 {len(self.aqi_data)} 個測站數據")
                return True
            else:
                print("API 回應格式錯誤")
                print(f"數據類型: {type(data)}")
                if isinstance(data, dict):
                    print(f"可用欄位: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"列表長度: {len(data)}")
                    if len(data) > 0:
                        print(f"第一項欄位: {list(data[0].keys()) if isinstance(data[0], dict) else '非字典項目'}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"API 請求失敗: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"JSON 解析失敗: {e}")
            return False
        except Exception as e:
            print(f"獲取數據時發生錯誤: {e}")
            return False
    
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
    
    def create_map(self):
        """創建 AQI 地圖"""
        if self.aqi_data is None or len(self.aqi_data) == 0:
            print("沒有可用的 AQI 數據")
            return None
        
        # 計算地圖中心點（台灣中心）
        valid_coords = self.aqi_data[
            self.aqi_data['latitude'].notna() & 
            self.aqi_data['longitude'].notna() &
            (self.aqi_data['latitude'] != '') &
            (self.aqi_data['longitude'] != '')
        ]
        
        if len(valid_coords) == 0:
            print("沒有有效的座標數據")
            return None
        
        # 轉換座標為數值
        valid_coords = valid_coords.copy()
        valid_coords['latitude'] = pd.to_numeric(valid_coords['latitude'], errors='coerce')
        valid_coords['longitude'] = pd.to_numeric(valid_coords['longitude'], errors='coerce')
        valid_coords = valid_coords.dropna(subset=['latitude', 'longitude'])
        
        if len(valid_coords) == 0:
            print("沒有有效的數值座標")
            return None
        
        center_lat = valid_coords['latitude'].mean()
        center_lon = valid_coords['longitude'].mean()
        
        # 創建地圖
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles='OpenStreetMap'
        )
        
        # 添加測站標記
        for idx, station in valid_coords.iterrows():
            try:
                lat = float(station['latitude'])
                lon = float(station['longitude'])
                
                # 獲取測站資訊
                site_name = station.get('sitename', '未知測站')
                aqi = station.get('aqi', 'N/A')
                pollutant = station.get('mainpollutant', 'N/A')
                status = station.get('status', 'N/A')
                county = station.get('county', 'N/A')
                
                # 獲取顏色
                color = self.get_aqi_color(aqi) if aqi != 'N/A' else 'gray'
                
                # 創建彈出視窗內容
                popup_content = f"""
                <b>{site_name}</b><br>
                縣市: {county}<br>
                AQI: {aqi}<br>
                狀態: {status}<br>
                主要污染物: {pollutant}
                """
                
                # 創建標記
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=8,
                    popup=folium.Popup(popup_content, max_width=200),
                    color='black',
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=1
                ).add_to(m)
                
            except (ValueError, TypeError) as e:
                print(f"跳過無效座標數據: {station.get('sitename', '未知')}")
                continue
        
        # 添加圖例
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 150px; height: 200px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>AQI 指標</h4>
        <i class="fa fa-circle" style="color:green"></i> 0-50 良好<br>
        <i class="fa fa-circle" style="color:yellow"></i> 51-100 中等<br>
        <i class="fa fa-circle" style="color:orange"></i> 101-150 對敏感族群不健康<br>
        <i class="fa fa-circle" style="color:red"></i> 151-200 對所有族群不健康<br>
        <i class="fa fa-circle" style="color:purple"></i> 201-300 非常不健康<br>
        <i class="fa fa-circle" style="color:maroon"></i> 300+ 危害<br>
        </div>
        '''
        
        m.get_root().html.add_child(folium.Element(legend_html))
        
        return m
    
    def save_map(self, map_obj, filename='outputs/aqi_map.html'):
        """保存地圖"""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            map_obj.save(filename)
            print(f"地圖已保存至: {filename}")
            return True
        except Exception as e:
            print(f"保存地圖失敗: {e}")
            return False
    
    def run(self):
        """執行完整流程"""
        print("=== 台灣空氣品質地圖生成器 ===")
        print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 獲取數據
        if not self.fetch_aqi_data():
            return False
        
        # 創建地圖
        aqi_map = self.create_map()
        if aqi_map is None:
            return False
        
        # 保存地圖
        return self.save_map(aqi_map)

def main():
    """主程式"""
    try:
        generator = AQIMapGenerator()
        success = generator.run()
        
        if success:
            print("\n[成功] AQI 地圖生成成功！")
            print("請開啟 outputs/aqi_map.html 查看地圖")
        else:
            print("\n[失敗] AQI 地圖生成失敗")
            
    except ValueError as e:
        print(f"[設定錯誤] {e}")
        print("請檢查 .env 檔案中的 API Key 設定")
    except Exception as e:
        print(f"[程式錯誤] {e}")

if __name__ == "__main__":
    main()
