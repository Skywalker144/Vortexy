import math
import numpy as np

INF = float('inf')

def quiescence_search(game, state, alpha, beta, to_play, accumulator, nnue):
    """
    静止搜索 (Quiescence Search, QS)
    """
    stand_pat = nnue.evaluate(accumulator) * to_play
    
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
        
    noisy_actions = getattr(game, "get_noisy_actions", lambda s, tp: [])(state, to_play)
    
    for action in noisy_actions:
        child_state = game.get_next_state(state, action, to_play)
        change = game.get_feature_change(state, action, to_play)
        child_acc = nnue.update_accumulator(accumulator, change)
        
        score = -quiescence_search(game, child_state, -beta, -alpha, -to_play, child_acc, nnue)
        
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
            
    return alpha


def negamax_nnue(game, state, depth, alpha, beta, to_play, accumulator, nnue):
    """
    采用 Negamax (负极大值) 框架的 AlphaBeta + NNUE 搜索。
    兼容 AlphaZero 风格的 game 接口。
    """
    # 1. 终局判断
    if game.is_terminal(state):
        winner = game.get_winner(state)
        if winner == 0 or winner is None:
            return 0
        return INF if winner == to_play else -INF
        
    # 2. 深度耗尽，进入叶子节点评估
    if depth == 0:
        return nnue.evaluate(accumulator) * to_play
        
    legal_actions_mask = game.get_is_legal_actions(state, to_play)
    legal_actions = np.where(legal_actions_mask)[0]
    
    if len(legal_actions) == 0:
        return 0  # 无路可走，视为平局或按规则处理
        
    best_value = -INF
    
    # 3. 遍历动作，展开搜索树
    for action in legal_actions:
        child_state = game.get_next_state(state, action, to_play)
        
        # === NNUE 增量更新 ===
        change = game.get_feature_change(state, action, to_play)
        child_acc = nnue.update_accumulator(accumulator, change)
        
        # === Negamax 递归 ===
        child_value = -negamax_nnue(
            game,
            child_state, 
            depth - 1, 
            -beta, 
            -alpha, 
            -to_play, 
            child_acc, 
            nnue
        )
        
        # 4. 维护最大值与 Alpha 边界
        if child_value > best_value:
            best_value = child_value
            
        alpha = max(alpha, best_value)
        
        # 5. Alpha-Beta 剪枝 (Beta Cut-off)
        if alpha >= beta:
            break
            
    return best_value


def search(game, state, to_play, depth, nnue):
    """
    搜索主入口函数
    返回: (最佳动作, MAX视角的局面得分)
    """
    alpha = -INF
    beta = INF
    best_action = None
    best_value = -INF
    
    # 1. 在根节点全量构建 (Refresh) NNUE 累加器
    active_features = game.get_active_features(state, to_play)
    root_acc = nnue.build_accumulator(active_features)
    
    legal_actions_mask = game.get_is_legal_actions(state, to_play)
    legal_actions = np.where(legal_actions_mask)[0]
    
    if len(legal_actions) == 0:
        return None, 0
        
    # 2. 遍历根节点的动作
    for action in legal_actions:
        child_state = game.get_next_state(state, action, to_play)
        
        change = game.get_feature_change(state, action, to_play)
        child_acc = nnue.update_accumulator(root_acc, change)
        
        # 调用 Negamax 搜索子树
        child_value = -negamax_nnue(
            game,
            child_state, 
            depth - 1, 
            -beta, 
            -alpha, 
            -to_play, 
            child_acc, 
            nnue
        )
        
        if child_value > best_value:
            best_value = child_value
            best_action = action
            
        alpha = max(alpha, best_value)
        
    final_score = best_value * to_play
    return best_action, final_score
