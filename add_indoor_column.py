import pandas as pd

def classify_shelter_type(facility_name):
    """
    根據避難收容處所名稱判斷是否為室內場所
    返回 True (室內) 或 False (室外)
    """
    if pd.isna(facility_name):
        return False
    
    facility_name = str(facility_name).strip()
    
    # 室內場所關鍵字
    indoor_keywords = [
        '活動中心', '辦公處', '國小', '國中', '高中', '學校', '教室', '禮堂',
        '圖書館', '社區中心', '集會所', '會議室', '體育館', '游泳池',
        '老人活動中心', '里民活動中心', '村辦公處', '鄉公所', '市公所',
        '區公所', '消防局', '警察局', '衛生所', '醫院', '診所',
        '教會', '教堂', '寺廟', '宮', '廟', '文化中心', '藝文中心',
        '訓練中心', '研習中心', '福利中心', '服务中心', '管理處',
        '遊客中心', '行政中心', '大廳', '綜合教室', '多功能中心'
    ]
    
    # 室外場所關鍵字
    outdoor_keywords = [
        '公園', '廣場', '河濱公園', '森林', '綠地', '草地', '球場',
        '田徑場', '運動場', '停車場', '海灘', '港灣', '碼頭',
        '堤防', '空地', '廣場', '廣場', '親水公園', '兒童遊戲場'
    ]
    
    # 檢查是否包含室內關鍵字
    for keyword in indoor_keywords:
        if keyword in facility_name:
            return True
    
    # 檢查是否包含室外關鍵字
    for keyword in outdoor_keywords:
        if keyword in facility_name:
            return False
    
    # 根據名稱模式判斷
    # 通常以「里」、「村」結尾且包含「辦公處」、「活動中心」等為室內
    if any(word in facility_name for word in ['辦公處', '活動中心', '集會所']):
        return True
    
    # 默認情況：如果名稱中包含「公園」、「廣場」等室外場所，則為室外
    if any(word in facility_name for word in ['公園', '廣場', '場']):
        return False
    
    # 如果無法確定，默認為室內（較為保守的判斷）
    return True

def add_indoor_column(csv_file):
    """
    在CSV檔案中新增is_indoor欄位並根據處所名稱分類
    """
    # 讀取CSV檔案
    df = pd.read_csv(csv_file)
    
    print(f"原始資料筆數: {len(df)}")
    print(f"欄位: {list(df.columns)}")
    
    # 新增is_indoor欄位
    df['is_indoor'] = df['避難收容處所名稱'].apply(classify_shelter_type)
    
    # 統計分類結果
    indoor_count = df['is_indoor'].sum()
    outdoor_count = len(df) - indoor_count
    
    print(f"\n分類結果:")
    print(f"室內場所: {indoor_count} 筆 ({indoor_count/len(df)*100:.1f}%)")
    print(f"室外場所: {outdoor_count} 筆 ({outdoor_count/len(df)*100:.1f}%)")
    
    # 顯示一些分類範例
    print(f"\n室內場所範例:")
    indoor_examples = df[df['is_indoor'] == True]['避難收容處所名稱'].head(5)
    for name in indoor_examples:
        print(f"  - {name}")
    
    print(f"\n室外場所範例:")
    outdoor_examples = df[df['is_indoor'] == False]['避難收容處所名稱'].head(5)
    for name in outdoor_examples:
        print(f"  - {name}")
    
    # 保存更新後的CSV檔案
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n已更新CSV檔案: {csv_file}")
    
    return df

if __name__ == "__main__":
    csv_file = "data/避難收容處所點位檔案v9.csv"
    updated_df = add_indoor_column(csv_file)
