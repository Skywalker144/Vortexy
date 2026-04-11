import sys
from envs.tictactoe import TicTacToe
from nnue import NNUE
from alphabeta import search

game = TicTacToe()
state, to_play = game.get_initial_state()
nnue = NNUE(input_size=18, hidden_size=16)

# Test running a search from the initial state
best_action, score = search(game, state, to_play, depth=3, nnue=nnue)
print(f"Best action: {best_action}, Score: {score}")
