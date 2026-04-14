import os
import torch
import numpy as np
import time
import argparse
from datetime import datetime

from alphabeta import search
from nnue_torch import NNUEPyTorch, create_nnue_for_game
from selfplay import SelfPlayManager
from train import NNUETrainer, IncrementalTrainer
from evaluate import NetworkSelector, NNUUEvaluator


class TrainingPipeline:
    """
    完整的训练管道：自我对弈 + 训练 + 评估 + 选择。
    支持迭代训练，持续提升网络棋力。
    """
    def __init__(
        self,
        game,
        game_name: str,
        input_size: int,
        hidden_size: int = 32,
        device: str = 'auto',
        save_dir: str = 'checkpoints'
    ):
        self.game = game
        self.game_name = game_name
        self.device = device if device != 'auto' else ('cuda' if torch.cuda.is_available() else 'cpu')
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        self.current_nnue = NNUEPyTorch(input_size=input_size, hidden_size=hidden_size)
        self.current_nnue.to(self.device)
        
        self.selfplay_manager = SelfPlayManager(game, self.current_nnue, device=self.device)
        self.trainer = IncrementalTrainer(self.current_nnue, lr=0.001, device=self.device)
        self.selector = NetworkSelector(game, win_rate_threshold=0.52)
        self.evaluator = NNUUEvaluator(game, device=self.device)
        
        self.round = 0
        self.best_nnue = None
        
    def run_round(self, num_games=100, train_epochs=10, eval_games=50, verbose=True):
        """
        执行一轮训练。
        
        Args:
            num_games: 自我对弈生成的数据量
            train_epochs: 每轮训练的 epoch 数
            eval_games: 用于评估新网络实力的对局数
            verbose: 是否打印详细信息
        """
        self.round += 1
        round_start = time.time()
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Round {self.round}")
            print(f"{'='*60}")
        
        if verbose:
            print("\n[1/4] Self-play data generation...")
        data_start = time.time()
        dataset = self.selfplay_manager.generate_dataset(
            num_games=num_games,
            verbose=verbose,
            random_prob=0.0
        )
        if verbose:
            print(f"  Generated {len(dataset)} games in {time.time()-data_start:.1f}s")
        
        if verbose:
            print(f"\n[2/4] Training NNUE for {train_epochs} epochs...")
        train_start = time.time()
        history = self.trainer.train_with_incremental_data(
            new_data=dataset,
            old_data=None,
            epochs=train_epochs,
            batch_size=64,
            verbose=verbose
        )
        if verbose:
            print(f"  Training completed in {time.time()-train_start:.1f}s")
        
        if self.best_nnue is not None:
            if verbose:
                print(f"\n[3/4] Evaluating new network vs current best...")
            eval_start = time.time()
            should_replace, stats, win_rate = self.selector.should_replace(
                self.best_nnue,
                self.current_nnue,
                num_games=eval_games
            )
            if verbose:
                print(f"  New network win rate: {win_rate:.1%}")
                print(f"  Evaluation completed in {time.time()-eval_start:.1f}s")
            
            if should_replace:
                if verbose:
                    print(f"  ✓ New network is stronger! Replacing best.")
                self.best_nnue = NNUEPyTorch(
                    input_size=self.current_nnue.input_size,
                    hidden_size=self.current_nnue.hidden_size
                )
                self.best_nnue.load_state_dict(self.current_nnue.state_dict())
            else:
                if verbose:
                    print(f"  ✗ New network is not strong enough. Keeping current best.")
                self.current_nnue.load_state_dict(self.best_nnue.state_dict())
        else:
            if verbose:
                print(f"\n[3/4] First round - setting current network as best")
            self.best_nnue = NNUEPyTorch(
                input_size=self.current_nnue.input_size,
                hidden_size=self.current_nnue.hidden_size
            )
            self.best_nnue.load_state_dict(self.current_nnue.state_dict())
            
            if verbose:
                print(f"\n[4/4] Evaluating absolute strength...")
        
        if verbose:
            self._evaluate_absolute_strength()
        
        self._save_checkpoint()
        
        round_time = time.time() - round_start
        if verbose:
            print(f"\nRound {self.round} completed in {round_time:.1f}s")
    
    def _evaluate_absolute_strength(self):
        """评估当前最佳网络的绝对实力"""
        nnue = self.best_nnue
        
        from nnue_torch import NNUEPyTorch
        random_nnue = NNUEPyTorch(
            input_size=nnue.input_size,
            hidden_size=nnue.hidden_size
        )
        random_nnue.to(self.device)
        
        print("  Playing 50 games vs random network...")
        black_wins = 0
        white_wins = 0
        draws = 0
        
        for i in range(50):
            if (i + 1) % 10 == 0:
                print(f"    Game {i+1}/50...")
            
            result = self._play_single_game(nnue, random_nnue, depth=3)
            if result == 1:
                black_wins += 1
            elif result == -1:
                white_wins += 1
            else:
                draws += 1
        
        total = black_wins + white_wins + draws
        win_rate = (black_wins + draws / 2) / total
        print(f"  Win rate vs random: {win_rate:.1%} ({black_wins}W/{draws}D/{white_wins}L)")
    
    def _play_single_game(self, nnue_black, nnue_white, depth):
        """下一盘棋"""
        state, to_play = self.game.get_initial_state()
        move_count = 0
        
        while not self.game.is_terminal(state):
            nnue = nnue_black if to_play == 1 else nnue_white
            
            legal_mask = self.game.get_is_legal_actions(state, to_play)
            legal_actions = np.where(legal_mask)[0]
            
            if len(legal_actions) == 0:
                break
            
            action, _ = search(self.game, state, to_play, depth, nnue)
            if action is None:
                action = np.random.choice(legal_actions)
            
            state = self.game.get_next_state(state, action, to_play)
            to_play = -to_play
            move_count += 1
            
            if move_count > 1000:
                break
        
        winner = self.game.get_winner(state)
        return 1 if winner == 1 else (-1 if winner == -1 else 0)
    
    def _save_checkpoint(self):
        """保存检查点"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.save_dir, f"{self.game_name}_round{self.round}_{timestamp}.pt")
        
        torch.save({
            'round': self.round,
            'model_state_dict': self.best_nnue.state_dict(),
            'model_config': {
                'input_size': self.best_nnue.input_size,
                'hidden_size': self.best_nnue.hidden_size
            }
        }, filepath)
        
        best_filepath = os.path.join(self.save_dir, f"{self.game_name}_best.pt")
        torch.save({
            'round': self.round,
            'model_state_dict': self.best_nnue.state_dict(),
            'model_config': {
                'input_size': self.best_nnue.input_size,
                'hidden_size': self.best_nnue.hidden_size
            }
        }, best_filepath)
        
        print(f"  Checkpoint saved: {filepath}")
        print(f"  Best model updated: {best_filepath}")
    
    def load_best(self, filepath=None):
        """加载最佳模型"""
        if filepath is None:
            filepath = os.path.join(self.save_dir, f"{self.game_name}_best.pt")
        
        if not os.path.exists(filepath):
            print(f"No saved model found at {filepath}")
            return False
        
        checkpoint = torch.load(filepath, map_location=self.device)
        self.current_nnue.load_state_dict(checkpoint['model_state_dict'])
        
        if self.best_nnue is None:
            self.best_nnue = NNUEPyTorch(
                input_size=checkpoint['model_config']['input_size'],
                hidden_size=checkpoint['model_config']['hidden_size']
            )
        self.best_nnue.load_state_dict(checkpoint['model_state_dict'])
        
        self.round = checkpoint.get('round', 0)
        print(f"Loaded model from round {self.round}")
        return True


def main():
    parser = argparse.ArgumentParser(description='Train AlphaBeta + NNUE')
    parser.add_argument('--game', type=str, default='tictactoe', 
                        choices=['tictactoe', 'gomoku'],
                        help='Game to train on')
    parser.add_argument('--rounds', type=int, default=10,
                        help='Number of training rounds')
    parser.add_argument('--games-per-round', type=int, default=100,
                        help='Self-play games per round')
    parser.add_argument('--epochs', type=int, default=10,
                        help='Training epochs per round')
    parser.add_argument('--hidden-size', type=int, default=32,
                        help='NNUE hidden layer size')
    parser.add_argument('--eval-games', type=int, default=50,
                        help='Games for evaluation')
    parser.add_argument('--device', type=str, default='auto',
                        help='Device (auto/cuda/cpu)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint')
    parser.add_argument('--save-dir', type=str, default='checkpoints',
                        help='Directory to save checkpoints')
    
    args = parser.parse_args()
    
    if args.game == 'tictactoe':
        from envs.tictactoe import TicTacToe
        game = TicTacToe()
        input_size = 18
        board_size = 3
    elif args.game == 'gomoku':
        from envs.gomoku import Gomoku
        game = Gomoku(board_size=15, use_renju=False)
        input_size = 450
        board_size = 15
    else:
        raise ValueError(f"Unknown game: {args.game}")
    
    print(f"\n{'='*60}")
    print(f"AlphaBeta + NNUE Training Pipeline")
    print(f"Game: {args.game}")
    print(f"Board size: {board_size}")
    print(f"Input size: {input_size}")
    print(f"Hidden size: {args.hidden_size}")
    print(f"{'='*60}\n")
    
    pipeline = TrainingPipeline(
        game=game,
        game_name=args.game,
        input_size=input_size,
        hidden_size=args.hidden_size,
        device=args.device,
        save_dir=args.save_dir
    )
    
    if args.resume:
        pipeline.load_best()
    
    for round_num in range(args.rounds):
        pipeline.run_round(
            num_games=args.games_per_round,
            train_epochs=args.epochs,
            eval_games=args.eval_games,
            verbose=True
        )
        
        if (round_num + 1) % 5 == 0:
            print(f"\n{'='*60}")
            print(f"SUMMARY after {round_num + 1} rounds")
            print(f"{'='*60}")
            print(f"Current best model saved at: {args.save_dir}/{args.game}_best.pt")
            print(f"{'='*60}\n")
    
    print("\nTraining complete!")
    print(f"Best model: {args.save_dir}/{args.game}_best.pt")


if __name__ == "__main__":
    main()
