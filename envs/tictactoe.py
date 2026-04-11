import numpy as np
# from utils import print_board


class TicTacToe:
    def __init__(self):
        self.board = np.zeros((3, 3))
        self.board_size = 3
        self.num_planes = 3

    def get_initial_state(self):
        return np.zeros((1, self.board_size, self.board_size)), 1

    @staticmethod
    def get_is_legal_actions(state, to_play):
        state = state[-1].flatten()
        return state == 0

    def get_next_state(self, state, action, to_play):
        state = state.copy()

        row = action // self.board_size
        col = action % self.board_size
        
        state[0, row, col] = to_play

        return state

    @staticmethod
    def get_winner(state, last_action=None, last_player=None):
        # Check rows and columns for a winner
        for i in range(3):
            if np.all(state[-1][i, :] == 1):  # Check rows for player 1
                return 1
            if np.all(state[-1][i, :] == -1):  # Check rows for player -1
                return -1
            if np.all(state[-1][:, i] == 1):  # Check columns for player 1
                return 1
            if np.all(state[-1][:, i] == -1):  # Check columns for player -1
                return -1

        # Check diagonals for a winner
        if np.all(np.diag(state[-1]) == 1) or np.all(np.diag(np.fliplr(state[-1])) == 1):  # Player 1 diagonals
            return 1
        if np.all(np.diag(state[-1]) == -1) or np.all(np.diag(np.fliplr(state[-1])) == -1):  # Player -1 diagonals
            return -1

        # Check for a draw (no empty spaces left)
        if np.all(state[-1] != 0):
            return 0  # 0 represents a draw

        # No winner yet
        return None

    def is_terminal(self, state, last_action=None, last_player=None):
        return (np.all(state[-1] != 0)
                or self.get_winner(state, last_action, last_player) is not None)

    def get_active_features(self, state, to_play):
        """Returns a list of active feature indices for NNUE."""
        board = state[-1]
        p1_indices = np.where(board.flatten() == 1)[0]
        p_minus_1_indices = np.where(board.flatten() == -1)[0] + self.board_size**2
        return list(p1_indices) + list(p_minus_1_indices)

    def get_feature_change(self, state, action, to_play):
        """Returns a FeatureChange object for NNUE incremental update."""
        from nnue import FeatureChange
        added = []
        if to_play == 1:
            added.append(int(action))
        else:
            added.append(int(self.board_size**2 + action))
        return FeatureChange(added=added, removed=[])

    def get_win_pos(self, final_state):
        b = final_state[-1]
        pos = np.zeros((3, 3), dtype=np.int8)
        
        for i in range(3):
            if abs(np.sum(b[i, :])) == 3: pos[i, :] = 1
        for i in range(3):
            if abs(np.sum(b[:, i])) == 3: pos[:, i] = 1
        if abs(np.trace(b)) == 3:
            np.fill_diagonal(pos, 1)
        if abs(np.trace(np.fliplr(b))) == 3:
            pos[0, 2] = pos[1, 1] = pos[2, 0] = 1
            
        return pos