import pandas as pd
import json


def convert_fan_data_to_json(filename):
    """
    读取特定格式的Excel文件，并将其转换为用于图表展示的JSON文件。

    Excel格式假定:
    - 第一行是风扇型号。
    - 每个风扇型号占据两列，第一列是"噪声"，第二列是"风量"。
    - 不同风扇的数据点（行数）可以不同。

    Args:
        filename (str): 文件名（不包含路径和后缀）。
    """
    # 自动补全路径和后缀
    excel_path = f'xlsx/{filename}.xlsx'
    json_path = f'json/{filename}.json'
    
    try:
        # 读取Excel文件，不使用合并的单元格作为列名
        df = pd.read_excel(excel_path, header=0)
        print("成功读取Excel文件。")
    except FileNotFoundError:
        print(f"错误：找不到文件 '{excel_path}'。请确保文件名正确并且文件在脚本所在的目录中。")
        return

    all_fans_data = {}
    
    # 获取所有非空的列名（这些是实际的风扇型号）
    fan_names = [col for col in df.columns if not col.startswith('Unnamed:')]
    
    for i, fan_name in enumerate(fan_names):
        # 计算每个风扇数据的起始列索引
        start_col = df.columns.get_loc(fan_name)
        
        # 检查后续列是否为Unnamed，以确定这个风扇的数据列数
        next_col_index = start_col + 1
        col_count = 1
        while (next_col_index < len(df.columns) and 
               df.columns[next_col_index].startswith('Unnamed:')):
            col_count += 1
            next_col_index += 1
            
        # 获取该风扇的所有相关列
        cols = df.columns[start_col:start_col + col_count]
        
        # 提取数据
        fan_df = df[cols].dropna()
        
        if col_count == 3:  # 三列格式：[噪声, 温度, 转速]
            points = [[round(row[0], 2), round(row[1], 2), round(row[2], 2)] for row in fan_df.values.tolist()]
            print(f"处理三列数据风扇: {fan_name}，包含转速数据")
        else:  # 两列格式：[噪声, 温度]
            points = [[round(row[0], 2), round(row[1], 2)] for row in fan_df.values.tolist()]
            print(f"处理两列数据风扇: {fan_name}")
            
        all_fans_data[fan_name] = points
        print(f"已处理风扇: {fan_name}，共 {len(points)} 个数据点。")

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_fans_data, f, ensure_ascii=False, indent=4)

    print(f"\n处理完成！所有数据已成功保存到 '{json_path}' 文件中。")


# --- 使用方法 ---
if __name__ == '__main__':
    # 现在只需要传入文件名（不含路径和后缀）
    convert_fan_data_to_json('27mm冷排换扇-前八250W')
    convert_fan_data_to_json('27mm冷排换扇')
    convert_fan_data_to_json('AK700换扇')
    convert_fan_data_to_json('双塔单扇双扇三扇')
    convert_fan_data_to_json('RZ700D换扇')
    convert_fan_data_to_json('挑战者SE单扇双扇')
    convert_fan_data_to_json('Hyper612APEX单扇双扇')
    convert_fan_data_to_json('AK700单扇双扇')
    convert_fan_data_to_json('AK400G2换扇')
    convert_fan_data_to_json('双塔双扇不同布局')
    convert_fan_data_to_json('RT600换扇')
    convert_fan_data_to_json('双塔不同策略')
