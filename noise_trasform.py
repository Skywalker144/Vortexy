import numpy as np

def adjust_for_env_noise(val_old_ref, val_new_ref, val_target):
    """
    根据参考声源的环境噪声变化，修正其他声源的分贝值。
    
    参数:
    val_old_ref: 参考声源在旧环境下的分贝 (e.g., 42.0)
    val_new_ref: 参考声源在新环境下的分贝 (e.g., 41.4)
    val_target:  想要求解的、在旧环境下测得的目标分贝值 (可以是单个数值或列表/数组)
    
    返回:
    在新环境下的预测分贝值
    """
    # 1. 计算能量差值 (Delta Power)
    # 也就是旧环境比新环境多出来的噪音能量
    p_old_ref = 10**(val_old_ref / 10.0)
    p_new_ref = 10**(val_new_ref / 10.0)
    p_diff = p_old_ref - p_new_ref
    
    # 如果差值小于0，说明环境噪音变大了，逻辑反转即可，代码通用
    
    # 2. 将目标值转换为能量
    target_array = np.array(val_target)
    p_target_old = 10**(target_array / 10.0)
    
    # 3. 减去环境能量差值，得到新环境下的能量
    p_target_new = p_target_old - p_diff
    
    # 边界检查：如果减去环境底噪后能量小于等于0，说明数据无效（目标声音比环境底噪变化量还小）
    # 这里用 NaN 标记无效值
    if isinstance(p_target_new, np.ndarray):
        p_target_new = np.where(p_target_new > 0, p_target_new, np.nan)
    else:
        if p_target_new <= 0: return None
        
    # 4. 转回分贝
    return 10 * np.log10(p_target_new)

# --- 你的案例 ---
ref_day1 = 42.0
ref_day2 = 41.4

# 假设你第一天还测了两个数据：一个很响的 50dB，一个很轻的 41.5dB
other_sources_day1 = [40.0, 45.8, 43.1, 40]

new_values = adjust_for_env_noise(ref_day1, ref_day2, other_sources_day1)

print(f"环境能量差 (Power Diff): {10**(ref_day1/10) - 10**(ref_day2/10):.2f}")
print("-" * 30)
for old, new in zip(other_sources_day1, new_values):
    print(f"旧值: {old} dBA -> 新值: {new:.2f} dBA (变化: {new-old:.2f} dB)")