import torch
import torch.nn as nn
import numpy as np


class NNUEPyTorch(nn.Module):
    """
    PyTorch 版本的 NNUE 评估网络。
    保持与原有 nnue.py 相同的接口，便于集成 AlphaBeta 搜索。
    """
    def __init__(self, input_size=256, hidden_size=16):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        self.feature_weights = nn.Parameter(
            torch.randn(input_size, hidden_size) * 0.1
        )
        self.feature_biases = nn.Parameter(
            torch.zeros(hidden_size)
        )
        self.output_weights = nn.Parameter(
            torch.randn(hidden_size) * 0.1
        )
        self.output_bias = nn.Parameter(torch.tensor(0.0))
        
    def build_accumulator(self, active_features):
        """
        全量构建累加器（用于搜索树的根节点）。
        返回隐藏层输入向量（未激活）。
        """
        device = self.feature_weights.device
        acc = torch.zeros(self.hidden_size, device=device)
        acc = acc + self.feature_biases
        
        for f in active_features:
            acc = acc + self.feature_weights[f]
        
        return acc
    
    def update_accumulator(self, accumulator, feature_change):
        """
        增量更新累加器（用于搜索树的子节点）。
        """
        new_acc = accumulator.clone()
        
        for f in feature_change.removed:
            new_acc = new_acc - self.feature_weights[f]
            
        for f in feature_change.added:
            new_acc = new_acc + self.feature_weights[f]
            
        return new_acc
    
    def evaluate(self, accumulator):
        """
        前向传播：返回 MAX 方视角的评估分数。
        """
        hidden = torch.clamp(accumulator, 0.0, 1.0)
        score = self.output_bias + torch.dot(hidden, self.output_weights)
        return score.item()
    
    def forward(self, accumulator):
        """
        批量评估（用于训练，从 accumulator 开始）。
        注意：这只训练第二层。如需训练全部权重，使用 forward_from_features。
        """
        hidden = torch.clamp(accumulator, 0.0, 1.0)
        score = self.output_bias + torch.matmul(hidden, self.output_weights)
        return score

    def forward_from_features(self, dense_features):
        """
        从稠密特征向量做完整前向传播（训练用，经过两层）。

        Args:
            dense_features: (batch_size, input_size) 二值特征向量
        Returns:
            score: (batch_size,) 评估分数，经过 tanh 映射到 [-1, 1]
        """
        # 第一层：特征 → 隐藏层（等价于 build_accumulator 的批量版本）
        acc = torch.matmul(dense_features, self.feature_weights) + self.feature_biases
        # ClippedReLU
        hidden = torch.clamp(acc, 0.0, 1.0)
        # 第二层：隐藏层 → 输出
        score = self.output_bias + torch.matmul(hidden, self.output_weights)
        # tanh 将输出映射到 [-1, 1]，与训练目标范围一致
        return torch.tanh(score)


class FeatureTransformer(nn.Module):
    """
    特征变换层：将棋盘状态转换为 NNUE 的输入特征。
    可以学习有意义的特征表示。
    """
    def __init__(self, board_size=15, hidden_size=128):
        super().__init__()
        self.board_size = board_size
        self.num_features = board_size * board_size * 2  # 黑白双方
        
        self.conv = nn.Sequential(
            nn.Conv2d(2, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(64 * board_size * board_size, hidden_size),
            nn.ReLU()
        )
        
    def forward(self, board):
        """
        board: (batch_size, 2, board_size, board_size)
        返回: (batch_size, hidden_size)
        """
        return self.conv(board)


class EnhancedNNUE(nn.Module):
    """
    增强版 NNUE：使用卷积网络提取特征，适合五子棋等复杂游戏。
    """
    def __init__(self, board_size=15, feature_hidden=128, output_hidden=32):
        super().__init__()
        self.board_size = board_size
        
        self.feature_transformer = FeatureTransformer(board_size, feature_hidden)
        
        self.output_layer = nn.Sequential(
            nn.Linear(feature_hidden, output_hidden),
            nn.ReLU(),
            nn.Linear(output_hidden, 1)
        )
        
    def get_active_features(self, state, to_play):
        """
        提取激活特征（兼容原有接口）。
        返回 (player_features, opponent_features)
        """
        board = state[-1]
        player_plane = 0 if to_play == 1 else 1
        opp_plane = 1 if to_play == 1 else 0
        
        player_indices = np.where(board.flatten() == to_play)[0]
        opp_indices = np.where(board.flatten() == -to_play)[0] + self.board_size * self.board_size
        
        return list(player_indices), list(opp_indices)
    
    def extract_features(self, board_tensor):
        """
        board_tensor: (batch_size, 2, board_size, board_size)
        """
        return self.feature_transformer(board_tensor)
    
    def forward(self, features):
        """
        features: (batch_size, feature_hidden)
        """
        return self.output_layer(features).squeeze(-1)


def create_nnue_for_game(game_name, board_size=3, hidden_size=16):
    """
    工厂函数：为指定游戏创建合适的 NNUE 模型。
    """
    if game_name == "tictactoe":
        input_size = board_size * board_size * 2  # 18
        return NNUEPyTorch(input_size=input_size, hidden_size=hidden_size)
    elif game_name == "gomoku":
        input_size = board_size * board_size * 2  # 450 for 15x15
        return NNUEPyTorch(input_size=input_size, hidden_size=hidden_size)
    else:
        raise ValueError(f"Unknown game: {game_name}")


if __name__ == "__main__":
    torch.set_printoptions(sci_mode=False, precision=4)
    
    nnue = NNUEPyTorch(input_size=18, hidden_size=16)
    print(f"NNUE Parameters: {sum(p.numel() for p in nnue.parameters())}")
    
    active_features = [0, 1, 10]
    acc = nnue.build_accumulator(active_features)
    print(f"Accumulator: {acc}")
    
    score = nnue.evaluate(acc)
    print(f"Score: {score}")
    
    from nnue import FeatureChange
    change = FeatureChange(added=[2], removed=[0])
    new_acc = nnue.update_accumulator(acc, change)
    print(f"Updated Accumulator: {new_acc}")
    
    new_score = nnue.evaluate(new_acc)
    print(f"New Score: {new_score}")
