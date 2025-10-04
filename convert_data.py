import pandas as pd
import json


def convert_fan_data_to_json(excel_path='fans.xlsx', json_path='fan_data.json'):
    """
    读取特定格式的Excel文件，并将其转换为用于图表展示的JSON文件。

    Excel格式假定:
    - 第一行是风扇型号。
    - 每个风扇型号占据两列，第一列是“噪声”，第二列是“风量”。
    - 不同风扇的数据点（行数）可以不同。

    Args:
        excel_path (str): 输入的Excel文件路径。
        json_path (str): 输出的JSON文件路径。
    """
    try:
        # 使用pd.read_excel()读取Excel文件，第一行作为列标题
        df = pd.read_excel(excel_path, header=0)
        print("成功读取Excel文件。")
    except FileNotFoundError:
        print(f"错误：找不到文件 '{excel_path}'。请确保文件名正确并且文件在脚本所在的目录中。")
        return

    all_fans_data = {}

    # df.columns 会得到所有列的标题列表。我们每次处理两列，所以步长为2。
    for i in range(0, len(df.columns), 2):
        # 第i列的标题就是风扇的型号
        fan_name = df.columns[i]

        # 获取当前风扇对应的“噪声”和“风量”两列的列名
        noise_col_name = df.columns[i]
        airflow_col_name = df.columns[i + 1]

        # 提取这两列数据，并使用 .dropna() 删除所有包含空值的行
        # 这样就可以处理每个风扇数据点数量不同的情况
        fan_df = df[[noise_col_name, airflow_col_name]].dropna()

        # 为了方便绘图，我们通常将数据整理成 [x, y] 的形式。
        # 在这里，x轴是“风量”，y轴是“噪声”。
        # .values 将DataFrame转换为Numpy数组，.tolist() 将其转换为列表
        points = fan_df[[airflow_col_name, noise_col_name]].values.tolist()

        # 将处理好的数据存入字典
        all_fans_data[fan_name] = points
        print(f"已处理风扇: {fan_name}，共 {len(points)} 个数据点。")

    # 将最终的字典写入JSON文件

    # 使用 'w' 模式（写入），encoding='utf-8' 来支持中文字符
    with open(json_path, 'w', encoding='utf-8') as f:
        # json.dump() 用于将Python字典写入文件
        # ensure_ascii=False 确保中文字符能正常显示
        # indent=4 让JSON文件格式化，更易于阅读
        json.dump(all_fans_data, f, ensure_ascii=False, indent=4)

    print(f"\n处理完成！所有数据已成功保存到 '{json_path}' 文件中。")


# --- 使用方法 ---
if __name__ == '__main__':
    # 你只需要把这里的 'fans.xlsx' 换成你的实际文件名即可
    convert_fan_data_to_json(excel_path='27mm冷排换扇同噪声数据.xlsx', json_path='27mm冷排换扇同噪声数据.json')
    convert_fan_data_to_json(excel_path='单塔单扇换扇数据.xlsx', json_path='单塔单扇换扇数据.json')
    convert_fan_data_to_json(excel_path='27mm冷排换扇同噪声数据-前八250W.xlsx', json_path='27mm冷排换扇同噪声数据-前八250W.json')