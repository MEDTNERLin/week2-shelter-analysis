import pandas as pd

def fix_covered_playgrounds(csv_file):
    """
    修正學校風雨操場的分類：若處所名稱包含學校相關關鍵字且包含"風雨操場"，則歸類為室內
    """
    # 讀取CSV檔案
    df = pd.read_csv(csv_file)
    
    print(f"原始資料筆數: {len(df)}")
    
    # 學校相關關鍵字
    school_keywords = ['國小', '國民小學', '國中', '國民中學', '高中', '高級中學', '中學', '小學', '分校']
    
    # 找出包含風雨操場的記錄
    covered_playground_mask = df['避難收容處所名稱'].str.contains('風雨操場', na=False)
    
    # 進一步篩選包含學校關鍵字的記錄
    covered_playgrounds = []
    for idx, row in df[covered_playground_mask].iterrows():
        facility_name = row['避難收容處所名稱']
        if any(keyword in facility_name for keyword in school_keywords):
            covered_playgrounds.append((idx, facility_name))
    
    print(f"\n找到 {len(covered_playgrounds)} 個學校風雨操場:")
    for idx, name in covered_playgrounds:
        print(f"  索引 {idx}: {name}")
        # 更新為室內
        df.loc[idx, 'is_indoor'] = True
    
    # 統計更新前後的變化
    original_indoor_count = df['is_indoor'].sum()
    original_outdoor_count = len(df) - original_indoor_count
    
    print(f"\n更新前分類:")
    print(f"  室內: {original_indoor_count} 筆")
    print(f"  室外: {original_outdoor_count} 筆")
    
    # 保存更新後的檔案
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    # 重新讀取確認更新
    df_updated = pd.read_csv(csv_file)
    updated_indoor_count = df_updated['is_indoor'].sum()
    updated_outdoor_count = len(df_updated) - updated_indoor_count
    
    print(f"\n更新後分類:")
    print(f"  室內: {updated_indoor_count} 筆")
    print(f"  室外: {updated_outdoor_count} 筆")
    print(f"  變更: {updated_indoor_count - original_indoor_count} 個從室外改為室內")
    
    return df_updated

if __name__ == "__main__":
    csv_file = "data/避難收容處所點位檔案v9.csv"
    updated_df = fix_covered_playgrounds(csv_file)
