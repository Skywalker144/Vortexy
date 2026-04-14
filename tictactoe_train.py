import signal
import sys
import os

from nnue_torch import NNUEPyTorch
from envs.tictactoe import TicTacToe
from selfplay import SelfPlayManager
from train import IncrementalTrainer
from evaluate import NNUUEvaluator
from datetime import datetime


class GracefulInterruptHandler:
    def __init__(self):
        self.interrupted = False
        self.original_handler = signal.signal(signal.SIGINT, self.handler)

    def handler(self, signum, frame):
        self.interrupted = True


def train_tictactoe(
    games_per_round: int = 100,
    train_epochs: int = 10,
    hidden_size: int = 32,
    save_dir: str = 'checkpoints',
    random_prob: float = 0.3
):
    os.makedirs(save_dir, exist_ok=True)
    
    game = TicTacToe()
    input_size = 18

    nnue = NNUEPyTorch(input_size=input_size, hidden_size=hidden_size)
    nnue.share_memory()
    
    selfplay_manager = SelfPlayManager(game, nnue)
    trainer = IncrementalTrainer(nnue, lr=0.001)
    evaluator = NNUUEvaluator(game)

    best_nnue = NNUEPyTorch(input_size=input_size, hidden_size=hidden_size)
    best_nnue.load_state_dict(nnue.state_dict())

    round_num = 0
    total_games = 0

    def save_checkpoint(nnue_to_save, round_num, total_games):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(save_dir, f"tictactoe_r{round_num}_g{total_games}_{timestamp}.pt")
        best_filepath = os.path.join(save_dir, "tictactoe_best.pt")

        torch_save = {
            'round': round_num,
            'total_games': total_games,
            'model_state_dict': nnue_to_save.state_dict(),
            'model_config': {
                'input_size': nnue_to_save.input_size,
                'hidden_size': nnue_to_save.hidden_size
            }
        }

        import torch
        torch.save(torch_save, filepath)
        torch.save(torch_save, best_filepath)
        print(f"\n[Saved] {filepath}")
        print(f"[Saved] {best_filepath}")

    handler = GracefulInterruptHandler()

    print("=" * 60)
    print("TicTacToe NNUE Training")
    print(f"Games per round: {games_per_round}")
    print(f"Train epochs per round: {train_epochs}")
    print(f"Hidden size: {hidden_size}")
    print(f"Save directory: {save_dir}")
    print("=" * 60)
    print("Press Ctrl+C to stop and save...\n")

    try:
        while not handler.interrupted:
            round_num += 1
            round_start = datetime.now()

            print(f"\n--- Round {round_num} ---")

            print(f"[1/3] Self-play ({games_per_round} games, random_prob={random_prob})...")
            dataset = selfplay_manager.generate_dataset(num_games=games_per_round, verbose=False, random_prob=random_prob)
            total_games += len(dataset)
            print(f"       Generated {len(dataset)} games, total: {total_games}")

            print(f"[2/3] Training ({train_epochs} epochs)...")
            history = trainer.train_with_incremental_data(
                new_data=dataset,
                epochs=train_epochs,
                batch_size=64,
                verbose=False
            )
            print(f"       Loss: {history['train_loss'][-1]:.4f}")

            print(f"[3/3] Evaluating vs best...")
            black_wins = 0
            white_wins = 0
            draws = 0

            for _ in range(50):
                result = evaluator._play_single_game(nnue, best_nnue, depth=3, random_prob=0.0)
                if result == 1:
                    black_wins += 1
                elif result == -1:
                    white_wins += 1
                else:
                    draws += 1

            total = black_wins + white_wins + draws
            new_win_rate = (black_wins + draws * 0.5) / total

            print(f"       vs best: {black_wins}W/{draws}D/{white_wins}L")
            print(f"       New win rate: {new_win_rate:.1%}")

            if new_win_rate >= 0.52:
                print(f"       -> New network is stronger! Updating best.")
                best_nnue.load_state_dict(nnue.state_dict())
            else:
                print(f"       -> Keeping current best.")
                nnue.load_state_dict(best_nnue.state_dict())

            elapsed = (datetime.now() - round_start).total_seconds()
            print(f"       Round time: {elapsed:.1f}s")

    except KeyboardInterrupt:
        pass

    print("\n\n" + "=" * 60)
    print("Training interrupted by user")
    print("=" * 60)

    save_checkpoint(best_nnue, round_num, total_games)

    print(f"\nTotal rounds: {round_num}")
    print(f"Total games: {total_games}")
    print("Training complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Train TicTacToe NNUE')
    parser.add_argument('--games', type=int, default=100, help='Games per round')
    parser.add_argument('--epochs', type=int, default=10, help='Training epochs per round')
    parser.add_argument('--hidden', type=int, default=32, help='Hidden size')
    parser.add_argument('--dir', type=str, default='checkpoints', help='Save directory')
    parser.add_argument('--random', type=float, default=0.3, help='Random action probability')

    args = parser.parse_args()

    train_tictactoe(
        games_per_round=args.games,
        train_epochs=args.epochs,
        hidden_size=args.hidden,
        save_dir=args.dir,
        random_prob=args.random
    )
