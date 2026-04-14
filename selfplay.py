import numpy as np
import torch
from collections import defaultdict
import pickle
import os

from alphabeta import search
from nnue_torch import NNUEPyTorch


class SelfPlayData:
    """自我对弈产生的数据结构"""
    def __init__(self):
        self.states = []
        self.to_plays = []
        self.active_features = []   # 每步的激活特征索引列表
        self.search_scores = []     # 每步的 AlphaBeta 搜索分数
        self.result = 0  # +1: player1 wins, -1: player2 wins, 0: draw

    def add(self, state, to_play, features, search_score=0.0):
        self.states.append(state.copy())
        self.to_plays.append(to_play)
        self.active_features.append(features)
        self.search_scores.append(search_score)

    def set_result(self, result):
        self.result = result

    def __len__(self):
        return len(self.states)


class SelfPlayManager:
    """
    自我对弈管理器。
    驱动引擎进行自我对弈，收集训练数据。
    """
    def __init__(self, game, nnue, device='cpu'):
        self.game = game
        self.nnue = nnue
        self.device = device
        self.nnue.to(device)
        self.nnue.eval()
        
    def play_one_game(self, verbose=False, random_prob=0.0, search_depth=3):
        """
        下一盘棋。

        Args:
            verbose: 是否打印对局过程
            random_prob: 以此概率随机选择动作（用于探索）
            search_depth: AlphaBeta 搜索深度

        Returns:
            SelfPlayData: 包含所有状态、特征、搜索分数和结果的数据
        """
        state, to_play = self.game.get_initial_state()
        data = SelfPlayData()

        move_count = 0
        while not self.game.is_terminal(state):
            if verbose:
                print(f"Move {move_count}: to_play={to_play}")

            legal_mask = self.game.get_is_legal_actions(state, to_play)
            legal_actions = np.where(legal_mask)[0]

            if len(legal_actions) == 0:
                break

            # 记录当前局面的特征（走棋前）
            features = self.game.get_active_features(state, to_play)

            # 选择动作并记录搜索分数
            if np.random.rand() < random_prob:
                action = np.random.choice(legal_actions)
                search_score = 0.0  # 随机走子没有搜索分数
            else:
                action, search_score = search(
                    self.game, state, to_play, depth=search_depth, nnue=self.nnue
                )
                if action is None:
                    action = np.random.choice(legal_actions)
                    search_score = 0.0
                else:
                    # 将搜索分数 clamp 到 [-1, 1]，忽略 ±INF（终局分数）
                    search_score = max(-1.0, min(1.0, search_score))

            # 记录：(走棋前的局面, 当前玩家, 当前玩家视角的特征, 搜索分数)
            data.add(state, to_play, features, search_score)

            # 执行动作
            state = self.game.get_next_state(state, action, to_play)
            to_play = -to_play
            move_count += 1

        # 记录最终结果
        winner = self.game.get_winner(state)
        if winner == 0 or winner is None:
            data.set_result(0)
        else:
            data.set_result(1 if winner == 1 else -1)

        if verbose:
            print(f"Game over. Winner: {data.result}")

        return data
    
    def generate_dataset(self, num_games, verbose=False, random_prob=0.0):
        """
        生成多个对局的训练数据。
        
        Args:
            num_games: 对局数量
            verbose: 是否打印详细信息
            random_prob: 随机动作概率
            
        Returns:
            List[SelfPlayData]: 所有对局数据
        """
        all_games = []
        
        for i in range(num_games):
            if verbose and (i + 1) % 10 == 0:
                print(f"Playing game {i + 1}/{num_games}")
            
            game_data = self.play_one_game(verbose=verbose and (i < 2), random_prob=random_prob)
            all_games.append(game_data)
        
        return all_games
    
    def save_dataset(self, dataset, filepath):
        """保存数据集到文件"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(dataset, f)
        print(f"Dataset saved to {filepath} ({len(dataset)} games)")
    
    def load_dataset(self, filepath):
        """从文件加载数据集"""
        with open(filepath, 'rb') as f:
            dataset = pickle.load(f)
        print(f"Dataset loaded from {filepath} ({len(dataset)} games)")
        return dataset


def states_to_tensors(dataset, nnue, lmbda=0.75):
    """
    将 SelfPlayData 列表转换为 PyTorch 张量格式。

    Args:
        dataset: List[SelfPlayData]
        nnue: NNUEPyTorch（用于获取 input_size）
        lmbda: 混合目标权重，target = λ * search_score + (1-λ) * game_result

    Returns:
        features: (N, input_size) 稠密二值特征向量
        targets: (N,) 混合目标值，范围 [-1, 1]
    """
    input_size = nnue.input_size
    all_features = []
    all_targets = []

    for game_data in dataset:
        result = game_data.result

        for i in range(len(game_data.states)):
            # 构造稠密二值特征向量
            dense = torch.zeros(input_size, dtype=torch.float32)
            for f_idx in game_data.active_features[i]:
                if f_idx < input_size:
                    dense[f_idx] = 1.0

            to_play = game_data.to_plays[i]
            # 将 game_result 转换为当前玩家视角
            game_target = result * to_play
            # search_score 已经是当前玩家视角（search 返回的就是 to_play 视角）
            search_target = game_data.search_scores[i]
            # 混合目标
            target = lmbda * search_target + (1 - lmbda) * game_target

            all_features.append(dense)
            all_targets.append(target)

    features = torch.stack(all_features)
    targets = torch.tensor(all_targets, dtype=torch.float32)

    return features, targets


if __name__ == "__main__":
    from envs.tictactoe import TicTacToe
    from envs.gomoku import Gomoku
    
    print("=" * 50)
    print("Testing SelfPlay with TicTacToe")
    print("=" * 50)
    
    game = TicTacToe()
    nnue = NNUEPyTorch(input_size=18, hidden_size=32)
    manager = SelfPlayManager(game, nnue)
    
    dataset = manager.generate_dataset(num_games=5, verbose=True)
    print(f"\nGenerated {len(dataset)} games")
    for i, game_data in enumerate(dataset):
        print(f"  Game {i+1}: {len(game_data)} states, result={game_data.result}")
        if len(game_data) > 0:
            print(f"    Features[0]: {game_data.active_features[0]}")
            print(f"    Search scores: {game_data.search_scores}")
