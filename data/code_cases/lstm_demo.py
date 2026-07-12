"""LSTM（长短期记忆网络）完整实现：门控机制与序列建模。

Related node: ml_lstm
Source IDs: book_deep_learning_ai
"""

from __future__ import annotations

import numpy as np


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid 激活函数。"""
    return 1 / (1 + np.exp(-np.clip(x, -500, 500)))


def tanh(x: np.ndarray) -> np.ndarray:
    """Tanh 激活函数。"""
    return np.tanh(x)


class LSTMCell:
    """
    单个 LSTM 单元。

    公式：
    f_t = σ(W_f·[h_{t-1}, x_t] + b_f)  # 遗忘门
    i_t = σ(W_i·[h_{t-1}, x_t] + b_i)  # 输入门
    c̃_t = tanh(W_c·[h_{t-1}, x_t] + b_c)  # 候选记忆
    c_t = f_t * c_{t-1} + i_t * c̃_t  # 新记忆
    o_t = σ(W_o·[h_{t-1}, x_t] + b_o)  # 输出门
    h_t = o_t * tanh(c_t)  # 输出
    """

    def __init__(self, input_size: int, hidden_size: int):
        self.input_size = input_size
        self.hidden_size = hidden_size

        # Xavier 初始化
        scale = np.sqrt(2.0 / (input_size + hidden_size))

        # 权重矩阵
        self.Wf = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.Wi = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.Wc = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.Wo = np.random.randn(hidden_size, input_size + hidden_size) * scale

        # 偏置
        self.bf = np.zeros((hidden_size, 1))
        self.bi = np.zeros((hidden_size, 1))
        self.bc = np.zeros((hidden_size, 1))
        self.bo = np.zeros((hidden_size, 1))

    def forward(self, x: np.ndarray, h_prev: np.ndarray, c_prev: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        前向传播。

        Args:
            x: 输入 (input_size, batch)
            h_prev: 上一时刻隐藏状态 (hidden_size, batch)
            c_prev: 上一时刻记忆 (hidden_size, batch)

        Returns:
            h: 当前隐藏状态
            c: 当前记忆
        """
        # 拼接
        concat = np.vstack([h_prev, x])  # (input_size + hidden_size, batch)

        # 遗忘门
        f = sigmoid(self.Wf @ concat + self.bf)

        # 输入门
        i = sigmoid(self.Wi @ concat + self.bi)

        # 候选记忆
        c_tilde = tanh(self.Wc @ concat + self.bc)

        # 新记忆
        c = f * c_prev + i * c_tilde

        # 输出门
        o = sigmoid(self.Wo @ concat + self.bo)

        # 隐藏状态
        h = o * tanh(c)

        # 保存用于反向传播
        self.cache = {
            'concat': concat, 'f': f, 'i': i, 'c_tilde': c_tilde,
            'c': c, 'o': o, 'h': h, 'c_prev': c_prev, 'h_prev': h_prev
        }

        return h, c


class LSTM:
    """LSTM 层。"""

    def __init__(self, input_size: int, hidden_size: int):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.cell = LSTMCell(input_size, hidden_size)

    def forward_sequence(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray, list]:
        """
        处理整个序列。

        Args:
            X: 输入序列 (input_size, seq_len, batch)

        Returns:
            outputs: 所有时刻的隐藏状态 (hidden_size, seq_len, batch)
            h_last: 最后一个隐藏状态
            caches: 反向传播所需的缓存
        """
        seq_len = X.shape[1]
        batch_size = X.shape[2]

        # 初始化
        h = np.zeros((self.hidden_size, seq_len, batch_size))
        c = np.zeros((self.hidden_size, seq_len, batch_size))
        h_prev = np.zeros((self.hidden_size, batch_size))
        c_prev = np.zeros((self.hidden_size, batch_size))

        caches = []

        # 逐时刻处理
        for t in range(seq_len):
            x_t = X[:, t, :]  # (input_size, batch)
            h_prev, c_prev = self.cell.forward(x_t, h_prev, c_prev)
            h[:, t, :] = h_prev
            c[:, t, :] = c_prev
            caches.append(self.cell.cache)

        return h, h_prev, caches


def gradient_clipping(grad, threshold=5.0):
    """梯度裁剪。"""
    norm = np.linalg.norm(grad)
    if norm > threshold:
        grad = grad * threshold / norm
    return grad


def lstm_forward_demo():
    """演示 LSTM 前向传播。"""
    print("=" * 60)
    print("LSTM 前向传播演示")
    print("=" * 60)

    np.random.seed(42)

    # 参数
    input_size = 4
    hidden_size = 3
    seq_len = 5
    batch_size = 2

    # 模拟输入序列
    X = np.random.randn(input_size, seq_len, batch_size)
    print(f"\n输入形状: {X.shape} (input_size, seq_len, batch)")

    # 初始化 LSTM
    lstm = LSTM(input_size, hidden_size)

    # 前向传播
    outputs, h_last, caches = lstm.forward_sequence(X)

    print(f"输出形状: {outputs.shape} (hidden_size, seq_len, batch)")
    print(f"最后隐藏状态形状: {h_last.shape} (hidden_size, batch)")

    # 分析门控行为
    print("\n分析 LSTM 门控机制：")

    # 遗忘门
    f_values = [cache['f'][:, 0] for cache in caches]  # 取第一个样本
    print(f"\n遗忘门（第一样本，5个时间步）:")
    for t, f in enumerate(f_values):
        print(f"  t={t}: f={f.round(4)}")

    # 输入门
    i_values = [cache['i'][:, 0] for cache in caches]
    print(f"\n输入门（第一样本，5个时间步）:")
    for t, i in enumerate(i_values):
        print(f"  t={t}: i={i.round(4)}")

    # 输出门
    o_values = [cache['o'][:, 0] for cache in caches]
    print(f"\n输出门（第一样本，5个时间步）:")
    for t, o in enumerate(o_values):
        print(f"  t={t}: o={o.round(4)}")


def compare_rnn_vs_lstm():
    """对比普通 RNN 和 LSTM 处理长序列的能力。"""
    print("\n" + "=" * 60)
    print("RNN vs LSTM：长序列依赖")
    print("=" * 60)

    print("\n普通 RNN 的问题：")
    print("  - 梯度消失：∂L/∂h_0 需要经过 t 次链式法则")
    print("  - 长期依赖困难：早期信息难以传递到后期")

    print("\nLSTM 的解决方案：")
    print("  - 记忆单元 c：专门存储长期信息")
    print("  - 遗忘门 f：选择性地丢弃旧记忆")
    print("  - 输入门 i：选择性地添加新记忆")
    print("  - 残差连接：c_t = f_t * c_{t-1} + i_t * c̃_t")

    # 简化对比
    print("\n简化示例：")
    print("  假设：初始记忆 c_0 = [1, 1, 1]")
    print("        遗忘门 f = 0.9（保留90%）")
    print("        新记忆 i = 0.1，c̃ = [0, 0, 0]")
    print("  经过 10 步后：c_10 ≈ [0.35, 0.35, 0.35]")
    print("  即使没有新输入，早期记忆仍然保留！")


def vanishing_gradient_demo():
    """演示梯度消失问题。"""
    print("\n" + "=" * 60)
    print("梯度消失与 LSTM 的解决")
    print("=" * 60)

    print("\n普通 RNN 的梯度流：")
    print("  ∂h_t/∂h_{t-k} = ∏(diag(σ'(z)))  · W")
    print("  如果 |W| < 1 且激活导数 < 1，梯度指数衰减")

    print("\n10 步后的梯度幅度（假设梯度衰减率 0.9）：")
    for k in [1, 5, 10, 20]:
        gradient = 0.9 ** k
        bar = '█' * int(gradient * 50)
        print(f"  k={k:2d}: {gradient:.6f} {bar}")

    print("\nLSTM 的梯度高速公路：")
    print("  ∂c_t/∂c_{t-1} = f_t")
    print("  如果遗忘门 f ≈ 0.9，梯度可以较好地传递")
    print("  记忆单元直接传递，绕过激活函数的非线性")


def lstm_for_sequence_classification():
    """演示 LSTM 用于序列分类。"""
    print("\n" + "=" * 60)
    print("LSTM 序列分类")
    print("=" * 60)

    np.random.seed(42)

    # 模拟：情感分析任务
    # 序列 = 词向量序列
    # 类别 = 正面(1) / 负面(0)

    vocab_size = 100
    embed_dim = 50
    hidden_size = 64
    seq_len = 20
    n_samples = 100

    print(f"\n任务：情感分类")
    print(f"  词表大小: {vocab_size}")
    print(f"  词向量维度: {embed_dim}")
    print(f"  序列长度: {seq_len}")
    print(f"  隐藏状态维度: {hidden_size}")

    # 模拟词向量序列
    X = np.random.randn(embed_dim, seq_len, n_samples)

    # 随机初始化 LSTM
    lstm = LSTM(embed_dim, hidden_size)

    # 前向传播
    outputs, h_last, _ = lstm.forward_sequence(X)

    print(f"\n  最后一个隐藏状态形状: {h_last.shape}")

    # 简单分类器
    W_class = np.random.randn(1, hidden_size) * 0.01
    b_class = np.zeros((1, 1))

    logits = W_class @ h_last + b_class
    probs = 1 / (1 + np.exp(-logits))

    print(f"  预测概率分布:")
    print(f"    min: {probs.min():.4f}")
    print(f"    max: {probs.max():.4f}")
    print(f"    mean: {probs.mean():.4f}")


if __name__ == "__main__":
    lstm_forward_demo()
    compare_rnn_vs_lstm()
    vanishing_gradient_demo()
    lstm_for_sequence_classification()