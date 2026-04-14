import numpy as np
import torch
from collections import defaultdict
import time

from alphabeta import search
from selfplay import SelfPlayManager


class NNUUEvaluator:
    """
    NNUE 网络评估器。
    用于比较两个网络的棋力。
    """
    def __init__(self, game, device='auto'):
        self.game = game
        self.device = device if device != 'auto' else ('cuda' if torch.cuda.is_available() else 'cpu')
        
    def evaluate_match(
        self,
        nnue_black,
        nnue_white,
        num_games: int = 100,
        depth: int = 3,
        verbose: bool = True,
        random_prob: float = 0.0
    ):
        """
        让两个网络对弈，评估相对实力。
        
        Args:
            nnue_black: 黑方网络
            nnue_white: 白方网络
            num_games: 对局数
            depth: AlphaBeta 搜索深度
            verbose: 是否打印详细信息
            random_prob: 随机动作概率
            
        Returns:
            dict: 包含胜率的统计结果
        """
        nnue_black.eval()
        nnue_white.eval()
        
        black_wins = 0
        white_wins = 0
        draws = 0
        
        results = []
        
        for i in range(num_games):
            if verbose and (i + 1) % 20 == 0:
                print(f"  Playing game {i+1}/{num_games}...")
            
            result = self._play_single_game(
                nnue_black, nnue_white, depth, random_prob
            )
            results.append(result)
            
            if result == 1:
                black_wins += 1
            elif result == -1:
                white_wins += 1
            else:
                draws += 1
        
        total = black_wins + white_wins + draws
        
        stats = {
            'black_wins': black_wins,
            'white_wins': white_wins,
            'draws': draws,
            'total': total,
            'black_win_rate': black_wins / total if total > 0 else 0,
            'white_win_rate': white_wins / total if total > 0 else 0,
            'draw_rate': draws / total if total > 0 else 0,
        }
        
        if verbose:
            print(f"\n{'='*40}")
            print(f"Evaluation Results ({num_games} games)")
            print(f"{'='*40}")
            print(f"Black (NNUE 1) wins: {black_wins} ({stats['black_win_rate']:.1%})")
            print(f"White (NNUE 2) wins: {white_wins} ({stats['white_win_rate']:.1%})")
            print(f"Draws: {draws} ({stats['draw_rate']:.1%})")
            print(f"{'='*40}")
        
        return stats
    
    def _play_single_game(self, nnue_black, nnue_white, depth, random_prob):
        """下一盘棋，返回结果"""
        state, to_play = self.game.get_initial_state()
        
        move_count = 0
        while not self.game.is_terminal(state):
            nnue = nnue_black if to_play == 1 else nnue_white
            
            legal_mask = self.game.get_is_legal_actions(state, to_play)
            legal_actions = np.where(legal_mask)[0]
            
            if len(legal_actions) == 0:
                break
            
            if np.random.rand() < random_prob:
                action = np.random.choice(legal_actions)
            else:
                action, _ = search(self.game, state, to_play, depth, nnue)
                if action is None:
                    action = np.random.choice(legal_actions)
            
            state = self.game.get_next_state(state, action, to_play)
            to_play = -to_play
            move_count += 1
            
            if move_count > 1000:
                break
        
        winner = self.game.get_winner(state)
        
        if winner == 1:
            return 1
        elif winner == -1:
            return -1
        else:
            return 0
    
    def evaluate_strength(self, nnue, num_games=50, depth=3, baseline='random'):
        """
        评估单个网络的绝对实力。
        
        Args:
            nnue: 要评估的网络
            num_games: 对局数
            depth: 搜索深度
            baseline: 'random' 或 'uniform'
            
        Returns:
            dict: 胜率统计
        """
        nnue.eval()
        
        if baseline == 'random':
            from nnue_torch import NNUEPyTorch
            random_nnue = NNUEPyTorch(
                input_size=nnue.input_size,
                hidden_size=nnue.hidden_size
            )
        else:
            random_nnue = None
        
        black_wins = 0
        white_wins = 0
        draws = 0
        
        for i in range(num_games):
            if (i + 1) % 10 == 0:
                print(f"  Playing game {i+1}/{num_games}...")
            
            if random_nnue is not None:
                result = self._play_single_game(nnue, random_nnue, depth, random_prob=0.0)
            else:
                result = self._play_single_game(nnue, nnue, depth, random_prob=0.1)
            
            if result == 1:
                black_wins += 1
            elif result == -1:
                white_wins += 1
            else:
                draws += 1
        
        total = black_wins + white_wins + draws
        
        return {
            'black_wins': black_wins,
            'white_wins': white_wins,
            'draws': draws,
            'win_rate': (black_wins + draws / 2) / total if total > 0 else 0
        }


def compare_networks(nnue1, nnue2, game, num_games=100, depth=3):
    """
    便捷函数：比较两个网络的强弱。
    
    Returns:
        bool: True if nnue1 is stronger (wins more), False otherwise
    """
    evaluator = NNUUEvaluator(game)
    stats = evaluator.evaluate_match(nnue1, nnue2, num_games=num_games, depth=depth)
    return stats['black_win_rate'] > 0.5


class NetworkSelector:
    """
    网络选择器：在迭代训练中选择保留哪个网络。
    """
    def __init__(self, game, win_rate_threshold=0.52, min_games=50):
        self.game = game
        self.win_rate_threshold = win_rate_threshold
        self.min_games = min_games
        self.evaluator = NNUUEvaluator(game)
        
    def should_replace(
        self,
        old_nnue,
        new_nnue,
        num_games: int = None
    ):
        """
        判断是否应该用新网络替换旧网络。
        
        Returns:
            tuple: (should_replace, stats)
        """
        if num_games is None:
            num_games = self.min_games
            
        stats = self.evaluator.evaluate_match(
            new_nnue, old_nnue,
            num_games=num_games,
            verbose=True
        )
        
        new_win_rate = (stats['black_wins'] + stats['draws'] / 2) / stats['total']
        
        should_replace = new_win_rate >= self.win_rate_threshold
        
        return should_replace, stats, new_win_rate


if __name__ == "__main__":
    from envs.tictactoe import TicTacToe
    from nnue_torch import NNUEPyTorch
    
    print("=" * 50)
    print("Testing Network Evaluation")
    print("=" * 50)
    
    game = TicTacToe()
    nnue1 = NNUEPyTorch(input_size=18, hidden_size=32)
    nnue2 = NNUEPyTorch(input_size=18, hidden_size=32)
    
    evaluator = NNUUEvaluator(game)
    
    print("\nComparing two random networks...")
    stats = evaluator.evaluate_match(nnue1, nnue2, num_games=20, verbose=True)
