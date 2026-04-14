import os
import torch
import numpy as np

from nnue_torch import NNUEPyTorch
from envs.tictactoe import TicTacToe
from alphabeta import search


def print_board(board):
    """打印棋盘"""
    print("\n  0   1   2")
    for i in range(3):
        row = f"{i} "
        for j in range(3):
            if board[i, j] == 1:
                row += " X "
            elif board[i, j] == -1:
                row += " O "
            else:
                row += " . "
            if j < 2:
                row += "|"
        print(row)
        if i < 2:
            print("  ---+---+---")
    print()


def play_tictactoe(model_path=None, human_plays_first=True):
    """
    人机对弈
    
    Args:
        model_path: NNUE 模型路径，None 则使用随机初始化
        human_plays_first: True 则人类先手(执X)，False 则AI先手
    """
    game = TicTacToe()
    
    if model_path and os.path.exists(model_path):
        checkpoint = torch.load(model_path, map_location='cpu')
        nnue = NNUEPyTorch(
            input_size=checkpoint['model_config']['input_size'],
            hidden_size=checkpoint['model_config']['hidden_size']
        )
        nnue.load_state_dict(checkpoint['model_state_dict'])
        print(f"Loaded model from {model_path}")
        if 'total_games' in checkpoint:
            print(f"Model trained with ~{checkpoint.get('total_games', 0)} self-play games")
    else:
        nnue = NNUEPyTorch(input_size=18, hidden_size=32)
        print("Using random initialized NNUE (no trained model)")

    nnue.eval()

    to_play = 1
    state, _ = game.get_initial_state()
    human_player = 1 if human_plays_first else -1
    ai_player = -1 if human_plays_first else 1

    print("\n" + "=" * 40)
    print("TicTacToe: Human vs NNUE+AlphaBeta")
    print("=" * 40)
    print(f"You are {'X' if human_player == 1 else 'O'}")
    print(f"AI is {'O' if ai_player == 1 else 'X'}")
    print("=" * 40)

    if human_plays_first:
        print("\nYou play first (X)")
    else:
        print("\nAI plays first (O)")

    move_history = []
    move_count = 0

    while not game.is_terminal(state):
        print_board(state[-1])

        if to_play == human_player:
            legal_mask = game.get_is_legal_actions(state, to_play)
            legal_actions = np.where(legal_mask)[0]

            print(f"Your turn ({'X' if to_play == 1 else 'O'})")
            print(f"Legal moves: {legal_actions.tolist()}")

            valid_input = False
            while not valid_input:
                try:
                    user_input = input("Enter move (0-8): ").strip()
                    action = int(user_input)

                    if action not in legal_actions:
                        print(f"Invalid move. Must be one of: {legal_actions.tolist()}")
                    else:
                        valid_input = True
                except ValueError:
                    print("Please enter a number 0-8")

            action = int(user_input)
        else:
            print(f"AI is thinking...")

            legal_mask = game.get_is_legal_actions(state, to_play)
            legal_actions = np.where(legal_mask)[0]

            if len(legal_actions) == 0:
                break

            action, score = search(game, state, to_play, depth=4, nnue=nnue)

            if action is None:
                action = legal_actions[0]

            row, col = action // 3, action % 3
            print(f"AI plays: ({row}, {col})")

        state = game.get_next_state(state, action, to_play)
        to_play = -to_play
        move_count += 1

        winner = game.get_winner(state)
        if winner is not None:
            break

        if move_count > 20:
            print("Too many moves, something went wrong")
            break

    print_board(state[-1])

    winner = game.get_winner(state)

    print("\n" + "=" * 40)
    if winner == human_player:
        print("You WIN! Congratulations!")
    elif winner == ai_player:
        print("AI WINS! Better luck next time.")
    else:
        print("It's a DRAW!")
    print("=" * 40)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Play TicTacToe vs NNUE')
    parser.add_argument('--model', type=str, default='checkpoints/tictactoe_best.pt',
                        help='Path to trained model')
    parser.add_argument('--first', action='store_true', default=True,
                        help='Human plays first (X)')
    parser.add_argument('--second', action='store_true',
                        help='AI plays first')

    args = parser.parse_args()

    human_plays_first = not args.second

    model_path = args.model if os.path.exists(args.model) else None
    if model_path is None and os.path.exists('checkpoints/tictactoe_best.pt'):
        model_path = 'checkpoints/tictactoe_best.pt'
        print(f"No model specified, using default: {model_path}")
    elif model_path is None:
        print("No trained model found, using random initialized NNUE")

    play_tictactoe(model_path=model_path, human_plays_first=human_plays_first)


if __name__ == "__main__":
    main()
