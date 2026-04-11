# AlphaBeta + NNUE

​    **AlphaBeta + NNUE** 是一种将经典博弈树搜索与神经网络评估结合起来的方案。其基本框架仍然是**AlphaBeta剪枝搜索**，但在叶子节点或静态评估阶段，不再完全依赖手工设计的特征函数，而是使用**NNUE**（Efficiently Updatable Neural Network）来对局面进行快速评估。

​    这种组合方式在现代棋类AI中非常重要，尤其适用于**搜索分支大、要求评估速度极高**的场景。因为AlphaBeta需要评估大量节点，所以神经网络不能太慢；而NNUE正是为此设计的一种**可增量更新、推理速度快、适合CPU搜索框架**的评估网络。

## AlphaBeta + NNUE算法流程

​    整个搜索过程仍然遵循AlphaBeta的主框架：

```python
best_action, best_value = search(
    state,
    to_play,
    depth=max_depth
)

1. 递归展开博弈树
2. 在叶子节点调用NNUE评估局面
3. 回溯时更新 alpha / beta
4. 若 alpha >= beta，则剪枝
```

​    与纯AlphaBeta相比，最大的区别在于第2步：**评估函数由NNUE提供**。接下来分别说明。

***

#### 1、搜索主框架

​    先看整体递归框架。它与传统AlphaBeta基本一致，只是在深度到达上限时调用 `nnue_evaluate()`。

```python
def alphabeta_nnue(state, depth, alpha, beta, to_play, accumulator):
    if state.is_terminal():
        return terminal_value(state)

    if depth == 0:
        return nnue_evaluate(state, to_play, accumulator)

    legal_actions = state.get_legal_actions()

    if to_play == 1:
        value = -inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(accumulator, state, action, to_play)
            child_value = alphabeta_nnue(
                child_state,
                depth - 1,
                alpha,
                beta,
                -to_play,
                child_acc
            )

            value = max(value, child_value)
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    else:
        value = +inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(accumulator, state, action, to_play)
            child_value = alphabeta_nnue(
                child_state,
                depth - 1,
                alpha,
                beta,
                -to_play,
                child_acc
            )

            value = min(value, child_value)
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value
```

​    这里新增的 `accumulator` 是NNUE实现中的关键结构，用来缓存隐藏层输入的累积结果，从而避免每到一个新节点都从头完整编码整个棋盘。

***

#### 2、终局与叶子节点评估

​    当搜索遇到终局时，应直接返回明确的胜负值；只有在“未终局但达到搜索深度上限”时，才调用NNUE进行静态评估。

```python
def terminal_value(state):
    winner = state.get_winner()
    if winner == 1:
        return +inf
    if winner == -1:
        return -inf
    return 0

def nnue_evaluate(state, to_play, accumulator):
    # 将累积特征送入后续全连接层，得到局面分数
    score = NNUE.forward(accumulator)
    return score
```

​    这里的 `score` 仍然必须满足AlphaBeta搜索的统一语义：

- 若分数大，表示局面对MAX方更有利
- 若分数小，表示局面对MIN方更有利

​    因此，无论NNUE内部是否区分当前行动方、先后手、王的位置、棋型特征，最终输出到搜索器时都必须转换到统一标准。

***

#### 3、NNUE的基本思想

​    普通神经网络虽然也能评估棋局，但在AlphaBeta中会遇到一个大问题：**搜索节点太多，重复推理成本太高**。

​    NNUE之所以适合AlphaBeta，是因为棋类搜索中相邻节点之间通常只相差“一步棋”。也就是说，从父节点到子节点，棋盘状态变化非常小。于是可以利用这一点：

- 父节点已经计算好的中间特征，不必全部丢弃
- 只对“这一步棋导致变化的那部分特征”做增量更新
- 然后快速得到子节点的评估结果

​    这就是NNUE中“Efficiently Updatable”的含义。

```python
def update_accumulator(accumulator, state, action, to_play):
    changed_features = get_changed_features(state, action, to_play)

    new_accumulator = accumulator.copy()
    for feature in changed_features.removed:
        new_accumulator -= INPUT_WEIGHTS[feature]
    for feature in changed_features.added:
        new_accumulator += INPUT_WEIGHTS[feature]

    return new_accumulator
```

​    这个过程可以理解为：

1. 某一步棋让一些特征失效（例如某个棋子离开原位置）
2. 同时让一些新特征生效（例如该棋子到达新位置，或者形成新的棋形）
3. 累加器把对应输入权重减掉和加上，就得到新局面的隐藏层输入

​    因此，相比每次都完整重新编码整盘棋，NNUE在深度搜索里会快很多。

***

#### 4、MAX节点搜索

​    与普通AlphaBeta一样，在MAX节点要尽量让分数最大化：

```python
def max_value_nnue(state, legal_actions, depth, alpha, beta, to_play, accumulator):
    value = -inf

    for action in legal_actions:
        child_state = state.get_next_state(action, to_play)
        child_acc = update_accumulator(accumulator, state, action, to_play)

        child_value = alphabeta_nnue(
            child_state,
            depth - 1,
            alpha,
            beta,
            -to_play,
            child_acc
        )

        value = max(value, child_value)
        alpha = max(alpha, value)

        if alpha >= beta:
            break

    return value
```

​    逻辑上与传统版本没有区别，区别仅在于叶子节点的值来自NNUE，而不是纯手工评估函数。

***

#### 5、MIN节点搜索

​    在MIN节点则要尽量让分数最小化：

```python
def min_value_nnue(state, legal_actions, depth, alpha, beta, to_play, accumulator):
    value = +inf

    for action in legal_actions:
        child_state = state.get_next_state(action, to_play)
        child_acc = update_accumulator(accumulator, state, action, to_play)

        child_value = alphabeta_nnue(
            child_state,
            depth - 1,
            alpha,
            beta,
            -to_play,
            child_acc
        )

        value = min(value, child_value)
        beta = min(beta, value)

        if alpha >= beta:
            break

    return value
```

​    因为剪枝机制不依赖评估函数的具体形式，所以只要NNUE输出是稳定且语义一致的，AlphaBeta剪枝就仍然完全成立。

***

#### 6、根节点决策

​    搜索入口除了根节点局面外，通常还需要先初始化根节点的NNUE累加器：

```python
def search(state, to_play, depth):
    alpha = -inf
    beta = +inf
    best_action = None

    root_acc = build_accumulator(state, to_play)
    legal_actions = state.get_legal_actions()

    if to_play == 1:
        best_value = -inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(root_acc, state, action, to_play)
            child_value = alphabeta_nnue(
                child_state,
                depth - 1,
                alpha,
                beta,
                -to_play,
                child_acc
            )

            if child_value > best_value:
                best_value = child_value
                best_action = action

            alpha = max(alpha, best_value)
    else:
        best_value = +inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(root_acc, state, action, to_play)
            child_value = alphabeta_nnue(
                child_state,
                depth - 1,
                alpha,
                beta,
                -to_play,
                child_acc
            )

            if child_value < best_value:
                best_value = child_value
                best_action = action

            beta = min(beta, best_value)

    return best_action, best_value
```

​    `build_accumulator(state, to_play)` 通常只在根节点或需要完全重建特征时调用一次；之后大多数搜索节点都通过增量更新完成特征维护。

***

#### 7、完整伪代码

```python
def terminal_value(state):
    winner = state.get_winner()
    if winner == 1:
        return +inf
    if winner == -1:
        return -inf
    return 0

def build_accumulator(state, to_play):
    accumulator = BIAS.copy()
    active_features = encode_features(state, to_play)
    for feature in active_features:
        accumulator += INPUT_WEIGHTS[feature]
    return accumulator

def update_accumulator(accumulator, state, action, to_play):
    changed_features = get_changed_features(state, action, to_play)

    new_acc = accumulator.copy()
    for feature in changed_features.removed:
        new_acc -= INPUT_WEIGHTS[feature]
    for feature in changed_features.added:
        new_acc += INPUT_WEIGHTS[feature]
    return new_acc

def nnue_evaluate(state, to_play, accumulator):
    hidden = clipped_relu(accumulator)
    score = output_layer(hidden)
    return score

def alphabeta_nnue(state, depth, alpha, beta, to_play, accumulator):
    if state.is_terminal():
        return terminal_value(state)

    if depth == 0:
        return nnue_evaluate(state, to_play, accumulator)

    legal_actions = state.get_legal_actions()

    if to_play == 1:
        value = -inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(accumulator, state, action, to_play)
            value = max(
                value,
                alphabeta_nnue(child_state, depth - 1, alpha, beta, -to_play, child_acc)
            )
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    else:
        value = +inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(accumulator, state, action, to_play)
            value = min(
                value,
                alphabeta_nnue(child_state, depth - 1, alpha, beta, -to_play, child_acc)
            )
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value

def search(state, to_play, depth):
    alpha = -inf
    beta = +inf
    best_action = None
    root_acc = build_accumulator(state, to_play)

    legal_actions = state.get_legal_actions()

    if to_play == 1:
        best_value = -inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(root_acc, state, action, to_play)
            child_value = alphabeta_nnue(child_state, depth - 1, alpha, beta, -to_play, child_acc)
            if child_value > best_value:
                best_value = child_value
                best_action = action
            alpha = max(alpha, best_value)
    else:
        best_value = +inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_acc = update_accumulator(root_acc, state, action, to_play)
            child_value = alphabeta_nnue(child_state, depth - 1, alpha, beta, -to_play, child_acc)
            if child_value < best_value:
                best_value = child_value
                best_action = action
            beta = min(beta, best_value)

    return best_action, best_value
```

## NNUE结构补充

### 为什么不是直接用普通神经网络

​    在AlphaBeta搜索中，程序每一步可能要评估几十万到几百万个节点。如果每个节点都重新做一次完整神经网络前向传播，成本通常太高。

​    普通卷积网络或Transformer虽然表达能力强，但更适合AlphaZero那种“少量高价值评估 + MCTS引导”的框架；对于AlphaBeta这种“海量节点 + 高频静态评估”的框架，推理速度往往是第一位的。

​    NNUE就是在这种需求下发展出来的：它保留了神经网络比手工特征更强的拟合能力，同时把推理成本压到足够低，适合在CPU上做深度搜索。

### NNUE与传统手工评估的关系

​    从功能上看，NNUE扮演的是“更强的评估函数”。

- 传统AlphaBeta：`evaluate(state)` 通常由人工规则编写
- AlphaBeta + NNUE：`evaluate(state)` 由训练好的NNUE模型输出

​    换句话说，搜索框架几乎不变，主要升级的是“叶子节点评估器”。

### 增量更新为什么重要

​    假设一个局面只走了一步棋，那么绝大多数棋子位置都没变。如果每次都把整盘棋重新编码一遍，会做大量重复计算。

​    NNUE通过维护累加器，把“父节点已经算过的大部分内容”复用到子节点，只对变化部分做增删，因此在搜索树中极其高效。

### 典型工程搭配

​    在实际引擎里，AlphaBeta + NNUE通常还会结合：

- **迭代加深**：先搜浅层，再搜深层
- **置换表**：缓存局面结果，避免重复搜索
- **走法排序**：让更可能强的招法先搜索，提高剪枝率
- **静态搜索**：在“局面不安静”时继续只搜索吃子/强迫手，减轻地平线效应
- **Aspiration Window**：围绕上一次迭代分数设定更窄的 alpha / beta 区间

​    这些优化与NNUE并不冲突，反而通常是一起使用的。

#### 注意

1. NNUE输出的分数必须与AlphaBeta搜索使用的分数语义一致，例如始终表示“从MAX方视角看”的局面优劣。
2. `build_accumulator()` 和 `update_accumulator()` 的特征定义必须完全一致，否则增量更新后的评估会与完整重算不匹配。
3. 如果某些走法会引起复杂特征变化（例如吃子、升变、禁手状态变化、特殊规则变化），增量更新逻辑要覆盖完整，不能只处理简单移动。
4. AlphaBeta + NNUE提升的是评估质量与搜索效率的平衡，但它仍然需要动作排序、置换表、迭代加深等工程优化，单靠NNUE本身并不能自动得到强引擎。
