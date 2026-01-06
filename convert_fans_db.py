import pandas as pd
import json


def convert_fans_database_to_json():
    """
    读取风扇数据库Excel文件，并将其转换为JSON文件。
    
    Excel格式：
    - 列：风扇型号、厚度、轴承类型、尺寸、品牌、价格、简介
    """
    excel_path = 'fan_data_base.xlsx'
    json_path = 'fans_database.json'
    
    try:
        # 读取Excel文件
        df = pd.read_excel(excel_path)
        print("成功读取Excel文件。")
        print(f"共读取 {len(df)} 条风扇数据。")
    except FileNotFoundError:
        print(f"错误：找不到文件 '{excel_path}'。")
        return
    except Exception as e:
        print(f"错误：读取文件时出错 - {e}")
        return

    # 转换为字典列表
    fans_list = []
    
    for index, row in df.iterrows():
        fan_data = {
            "name": str(row['风扇型号']).strip(),
            "thickness": row['厚度'] if pd.notna(row['厚度']) else None,
            "bearing": str(row['轴承类型']).strip() if pd.notna(row['轴承类型']) else "",
            "size": row['尺寸'] if pd.notna(row['尺寸']) else None,
            "brand": str(row['品牌']).strip() if pd.notna(row['品牌']) else "",
            "price": str(row['价格']).strip() if pd.notna(row['价格']) else "",
            "description": str(row['简介']).strip() if pd.notna(row['简介']) else ""
        }
        
        fans_list.append(fan_data)
        print(f"已处理: {fan_data['name']}")

    # 构建最终的JSON结构
    output_data = {
        "fans": fans_list,
        "metadata": {
            "total": len(fans_list),
            "lastUpdated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

    # 保存为JSON文件
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 处理完成！共 {len(fans_list)} 条数据已成功保存到 '{json_path}' 文件中。")


if __name__ == '__main__':
    convert_fans_database_to_json()
