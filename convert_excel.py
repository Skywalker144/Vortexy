#!/usr/bin/env python3
"""
将xlsx文件夹中的Excel文件转换为JSON格式供网站使用
"""

import pandas as pd
import json
import os
from pathlib import Path

def convert_excel_to_json():
    xlsx_dir = Path('xlsx')
    all_data = {}
    
    # 遍历所有xlsx文件
    for file_path in xlsx_dir.glob('*.xlsx'):
        project_name = file_path.stem  # 获取文件名（不含扩展名）
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, header=None)
            
            fans = {}
            # 第一行是风扇型号，每3列一个风扇
            num_fans = len(df.columns) // 3
            
            for i in range(num_fans):
                col_start = i * 3
                fan_name = str(df.iloc[0, col_start])
                
                if pd.isna(fan_name) or fan_name == 'nan':
                    continue
                
                # 提取数据：噪音、温升、转速
                data_points = []
                for row_idx in range(1, len(df)):
                    noise = df.iloc[row_idx, col_start]
                    temp = df.iloc[row_idx, col_start + 1]
                    rpm = df.iloc[row_idx, col_start + 2]
                    
                    # 跳过空值
                    if pd.isna(noise) or pd.isna(temp) or pd.isna(rpm):
                        continue
                    
                    data_points.append({
                        'noise': float(noise),
                        'temp': float(temp),
                        'rpm': float(rpm)
                    })
                
                if data_points:
                    # 按噪音排序
                    data_points.sort(key=lambda x: x['noise'])
                    fans[fan_name] = data_points
            
            if fans:
                all_data[project_name] = fans
                print(f"已处理: {project_name} - {len(fans)} 个风扇")
        
        except Exception as e:
            print(f"处理 {file_path} 时出错: {e}")
    
    # 保存为JSON
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n转换完成！共 {len(all_data)} 个项目")
    return all_data

if __name__ == '__main__':
    convert_excel_to_json()
