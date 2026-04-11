# AlphaBeta

​    **AlphaBeta搜索**（Alpha-Beta Pruning）是经典的**极大极小搜索**（Minimax）优化算法，广泛用于国际象棋、中国象棋、五子棋等**双人、零和、完全信息、轮流行动**的棋类游戏中。它的核心思想是：在搜索博弈树时，通过维护当前已知的上下界，**提前剪掉不可能影响最终决策的分支**，从而在保证结果与普通Minimax完全一致的前提下，大幅减少搜索节点数。

## AlphaBeta算法流程

​    AlphaBeta在计算一步棋时，会以当前棋局为根节点，递归搜索到给定深度（或终局）。搜索过程中会不断维护两个边界值：

- **alpha**：当前路径上，**MAX方**（当前搜索目标方）已经确保能够得到的最低分数下界
- **beta**：当前路径上，**MIN方**（对手）已经确保能够得到的最高分数上界

​    当搜索发现某一分支已经不可能比当前已知方案更优时，就可以直接停止该分支的继续展开，这就是**剪枝**。

```python
# 将当前棋局作为根节点。to_play代表轮到谁走子。1代表先手，-1代表后手
best_action, best_value = search(
    state,
    to_play,
    depth=max_depth
)

1. 递归展开博弈树
2. 在叶子节点或终局节点进行评估
3. 回溯时更新 alpha / beta
4. 如果 alpha >= beta，则进行剪枝
```

​    接下来具体介绍每个步骤的内容。

***

#### 1、递归搜索框架

​    AlphaBeta本质上是在Minimax基础上加入剪枝逻辑。搜索时需要先判断：当前节点是终局、达到深度上限，还是还要继续展开子节点。

```python
def alphabeta(state, depth, alpha, beta, to_play):
    # 终局节点：直接返回终局分数
    if state.is_terminal():
        return terminal_value(state, to_play)

    # 到达深度上限：返回静态评估值
    if depth == 0:
        return evaluate(state, to_play)

    legal_actions = state.get_legal_actions()

    if to_play == 1:
        return max_value(state, legal_actions, depth, alpha, beta, to_play)
    else:
        return min_value(state, legal_actions, depth, alpha, beta, to_play)
```

​    这里有一个关键约定：

- `to_play == 1` 时，表示当前节点是**极大节点**（MAX）
- `to_play == -1` 时，表示当前节点是**极小节点**（MIN）

​    也就是说，MAX想让分数尽可能大，MIN想让分数尽可能小。

***

#### 2、叶子节点评估

​    AlphaBeta本身并不决定“局面好坏”，它只负责在博弈树中传播分数。真正给出局面价值的是**评估函数**。

```python
def terminal_value(state, to_play):
    winner = state.get_winner()  # 1表示先手胜，-1表示后手胜，0表示平局
    if winner == 0:
        return 0
    if winner == 1:
        return +inf
    return -inf

def evaluate(state, to_play):
    score = 0

    # 例子：根据棋形、子力、控制区域等进行打分
    score += evaluate_material(state)
    score += evaluate_position(state)
    score += evaluate_threats(state)

    return score
```

​    评估函数返回的是一个**静态分数**：

- 分数越大，越有利于MAX方
- 分数越小，越有利于MIN方
- 如果是零和博弈，常常会设计成双方优势此消彼长的形式

​    在很多实现中，评估值通常统一成“**从固定一方视角**”来定义，例如永远表示“对先手有多好”；也可以定义成“**从当前行动方视角**”来评估，但那样在递归过程中就要格外注意符号转换。

​    在这里为了和Minimax / AlphaBeta的标准写法一致，默认评估值始终从**MAX方视角**解释。

***

#### 3、MAX节点搜索

​    当轮到MAX方走棋时，要在所有合法动作中选择**价值最大的那个动作**。同时不断更新 `alpha`，表示“MAX目前已经找到的最好下界”。

```python
def max_value(state, legal_actions, depth, alpha, beta, to_play):
    value = -inf

    for action in legal_actions:
        child_state = state.get_next_state(action, to_play)
        child_value = alphabeta(
            child_state,
            depth - 1,
            alpha,
            beta,
            -to_play
        )

        value = max(value, child_value)
        alpha = max(alpha, value)

        if alpha >= beta:
            break  # Beta剪枝

    return value
```

​    这里的含义是：

- `value`：当前MAX节点遍历到目前为止的最好分数
- `alpha`：祖先路径上，MAX已经保证自己至少能拿到这么多
- 若 `alpha >= beta`，说明当前MIN祖先节点已经有更好的选择，不会再让这条分支被真正走到，因此后续兄弟节点可以直接跳过

***

#### 4、MIN节点搜索

​    当轮到MIN方走棋时，要在所有合法动作中选择**价值最小的那个动作**。同时不断更新 `beta`，表示“MIN目前已经找到的最好上界”。

```python
def min_value(state, legal_actions, depth, alpha, beta, to_play):
    value = +inf

    for action in legal_actions:
        child_state = state.get_next_state(action, to_play)
        child_value = alphabeta(
            child_state,
            depth - 1,
            alpha,
            beta,
            -to_play
        )

        value = min(value, child_value)
        beta = min(beta, value)

        if alpha >= beta:
            break  # Alpha剪枝

    return value
```

​    与MAX节点完全对称：

- `value`：当前MIN节点目前找到的最小分数
- `beta`：MIN已经保证自己最多只会让局面好到这个程度
- 若 `alpha >= beta`，说明当前分支对祖先来说已经不可能成为更优选择，可以立刻停止

***

#### 5、剪枝原理

​    AlphaBeta剪枝成立的前提是：双方都按最优策略行动。

​    举个例子，假设当前在某个MAX节点下搜索：

1. MAX已经在别的分支里找到一个分数至少为 `alpha = 8` 的走法
2. 现在搜索另一个子节点，发现该子节点对应的MIN节点已经能把结果压到 `beta = 6`
3. 因为 `beta <= alpha`，说明这个分支最终结果最多只能到6
4. 但MAX已经有能拿到8的分支了，所以这个分支不可能被选中
5. 因此该分支后续未搜索的子树全部可以剪掉

```python
if alpha >= beta:
    break
```

​    这条判断就是AlphaBeta搜索最核心的一行。

​    从区间理解：

- MAX希望把结果往大推，所以维护下界 `alpha`
- MIN希望把结果往小压，所以维护上界 `beta`
- 当下界已经不小于上界时，说明“这个区间已经没有继续讨论的必要”

***

#### 6、根节点决策

​    在真正落子时，除了需要知道该局面的分值，还需要知道**是哪一个动作达成了这个最优值**。因此根节点通常会额外记录最优动作。

```python
def search(state, to_play, depth):
    alpha = -inf
    beta = +inf

    legal_actions = state.get_legal_actions()
    best_action = None

    if to_play == 1:  # MAX走
        best_value = -inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_value = alphabeta(
                child_state,
                depth - 1,
                alpha,
                beta,
                -to_play
            )

            if child_value > best_value:
                best_value = child_value
                best_action = action

            alpha = max(alpha, best_value)
    else:  # MIN走
        best_value = +inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_value = alphabeta(
                child_state,
                depth - 1,
                alpha,
                beta,
                -to_play
            )

            if child_value < best_value:
                best_value = child_value
                best_action = action

            beta = min(beta, best_value)

    return best_action, best_value
```

​    最终返回的 `best_action` 就是当前局面下搜索深度范围内的最优动作。

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

def evaluate(state):
    score = 0
    score += evaluate_material(state)
    score += evaluate_position(state)
    score += evaluate_threats(state)
    return score

def alphabeta(state, depth, alpha, beta, to_play):
    if state.is_terminal():
        return terminal_value(state)

    if depth == 0:
        return evaluate(state)

    legal_actions = state.get_legal_actions()

    if to_play == 1:
        value = -inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            value = max(
                value,
                alphabeta(child_state, depth - 1, alpha, beta, -to_play)
            )
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    else:
        value = +inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            value = min(
                value,
                alphabeta(child_state, depth - 1, alpha, beta, -to_play)
            )
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value

def search(state, to_play, depth):
    alpha = -inf
    beta = +inf
    best_action = None

    legal_actions = state.get_legal_actions()

    if to_play == 1:
        best_value = -inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_value = alphabeta(child_state, depth - 1, alpha, beta, -to_play)
            if child_value > best_value:
                best_value = child_value
                best_action = action
            alpha = max(alpha, best_value)
    else:
        best_value = +inf
        for action in legal_actions:
            child_state = state.get_next_state(action, to_play)
            child_value = alphabeta(child_state, depth - 1, alpha, beta, -to_play)
            if child_value < best_value:
                best_value = child_value
                best_action = action
            beta = min(beta, best_value)

    return best_action, best_value
```

## AlphaBeta理论补充

### Alpha和Beta的含义

​    AlphaBeta里的 `alpha` 和 `beta` 不是“当前节点真实值”，而是沿着搜索路径逐步累积出的**可保证边界**：

- `alpha`：MAX已知至少能拿到的值
- `beta`：MIN已知至多会接受的值

​    它们的作用不是直接给局面打分，而是帮助判断“某个分支是否还有继续搜索的必要”。

### 为什么剪枝后结果不变

​    AlphaBeta并不是近似算法。只要：

1. 搜索深度相同
2. 评估函数相同
3. 动作生成一致

​    那么AlphaBeta与普通Minimax返回的结果完全一致，只是**少搜索了许多无效节点**。

### Move Ordering的重要性

​    AlphaBeta的剪枝效率高度依赖**动作排序**（Move Ordering）。

​    如果更强、更可能成为最优解的动作被优先搜索，那么 `alpha` 和 `beta` 会更快收紧，后续分支就更容易被剪掉。

​    常见排序方法包括：

- 先搜索吃子、冲四、将军等强迫性动作
- 优先搜索历史上表现好的动作
- 使用上一次迭代深化得到的主变着法作为第一候选
- 使用置换表中的最佳着法优先搜索

​    在理想排序下，AlphaBeta的搜索效率会远高于朴素Minimax。

#### 注意

1. `evaluate(state)` 的返回分数必须在整个搜索树中保持统一语义，例如始终表示“从MAX方视角看”的好坏。
2. `terminal_value(state)` 与 `evaluate(state)` 的正负方向必须一致，否则搜索会出现逻辑错误。
3. `alpha >= beta` 时可以立即剪枝，因为该分支已经不可能影响祖先节点的最终决策。
4. AlphaBeta通常搭配**迭代加深**、**动作排序**、**置换表**、**静态搜索（Quiescence Search）**一起使用，否则单纯固定深度搜索容易出现地平线效应。
