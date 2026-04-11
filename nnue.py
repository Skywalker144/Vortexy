import random

class FeatureChange:
    """
    描述一步动作引起的特征变化
    """
    def __init__(self, added, removed):
        self.added = added      # 新增特征的索引列表 (list of int)
        self.removed = removed  # 移除特征的索引列表 (list of int)

class Accumulator:
    """
    累加器：缓存神经网络隐藏层的输入结果
    避免每次评估时都全量重新计算。
    """
    def __init__(self, size):
        self.values = [0.0] * size

    def copy(self):
        new_acc = Accumulator(len(self.values))
        new_acc.values = self.values.copy()
        return new_acc

class NNUE:
    """
    用于演示的简化版 NNUE (Efficiently Updatable Neural Network) 评估网络。
    实际工程中（如 Stockfish）：
    1. 特征维数更大（例如 256, 512, 或更高）。
    2. 会使用 HalfKP 结构，并且分为先手和后手两个累加器。
    3. 参数被量化（Quantized）为 int16/int8，通过 SIMD 指令(AVX2/AVX512)进行加速。
    """
    def __init__(self, input_size=256, hidden_size=16):
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        # 随机初始化权重 (实际应用中应该从训练好的网络文件加载权重)
        # feature_weights 形状: [input_size][hidden_size]
        self.feature_weights = [[random.gauss(0, 0.1) for _ in range(hidden_size)] for _ in range(input_size)]
        self.feature_biases = [random.gauss(0, 0.1) for _ in range(hidden_size)]
        
        # output_weights 形状: [hidden_size]
        self.output_weights = [random.gauss(0, 0.1) for _ in range(hidden_size)]
        self.output_bias = random.gauss(0, 0.1)

    def build_accumulator(self, active_features):
        """
        全量构建 (Refresh)：在搜索树的根节点，根据所有激活的特征计算一次完整的隐藏层输入。
        
        :param active_features: 当前激活特征的索引列表 (list of int)
        :return: 初始化好的 Accumulator
        """
        acc = Accumulator(self.hidden_size)
        # 先填入偏置项
        for i in range(self.hidden_size):
            acc.values[i] = self.feature_biases[i]
            
        # 累加所有激活特征的权重
        for f in active_features:
            for i in range(self.hidden_size):
                acc.values[i] += self.feature_weights[f][i]
        return acc

    def update_accumulator(self, accumulator, feature_change):
        """
        增量更新 (Update)：根据动作引发的特征差异（Added / Removed），快速更新隐藏层。
        这里是 NNUE 在深度搜索树中速度极快的核心秘密。O(1) 级别的特征更新。
        
        :param accumulator: 父节点的累加器
        :param feature_change: FeatureChange 对象，包含新增和移除的特征
        :return: 子节点的新 Accumulator
        """
        new_acc = accumulator.copy()
        
        # 减去失效特征的权重
        for f in feature_change.removed:
            for i in range(self.hidden_size):
                new_acc.values[i] -= self.feature_weights[f][i]
                
        # 加上新特征的权重
        for f in feature_change.added:
            for i in range(self.hidden_size):
                new_acc.values[i] += self.feature_weights[f][i]
                
        return new_acc

    def evaluate(self, accumulator):
        """
        前向传播：将累加器的结果通过激活函数并映射为最终的局面分数。
        返回的分数通常统一为“MAX方（先手方）视角的得分”。
        
        :param accumulator: 当前节点的累加器
        :return: 局面评分 (float)
        """
        score = self.output_bias
        
        for i in range(self.hidden_size):
            # 激活函数：Clipped ReLU (0, 1)。在量化网络中非常常见，防止数值溢出。
            hidden_val = max(0.0, min(1.0, accumulator.values[i]))
            score += hidden_val * self.output_weights[i]
            
        return score
