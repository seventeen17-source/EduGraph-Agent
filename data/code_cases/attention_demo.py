"""注意力机制（Attention）完整实现：从 Seq2Seq 到 Transformer。

Related node: ml_attention_mechanism
Source IDs: book_deep_learning_ai
"""

from __future__ import annotations

import numpy as np


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Softmax 函数。"""
    x_shifted = x - np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x_shifted)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


def dot_product_attention(Q: np.ndarray, K: np.ndarray, V: np.ndarray,
                         mask: np.ndarray = None, scale: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """
    缩放点积注意力。

    Attention(Q, K, V) = softmax(QK^T / √d_k) V

    Args:
        Q: Query (seq_len_q, d_k)
        K: Key (seq_len_k, d_k)
        V: Value (seq_len_k, d_v)
        mask: 掩码 (可选)
        scale: 是否缩放

    Returns:
        output: 注意力输出
        attention_weights: 注意力权重
    """
    d_k = K.shape[-1]

    # 计算注意力分数
    scores = Q @ K.T

    if scale:
        scores = scores / np.sqrt(d_k)

    # 应用掩码
    if mask is not None:
        scores = np.where(mask == 0, -1e9, scores)

    # Softmax
    attention_weights = softmax(scores, axis=-1)

    # 加权求和
    output = attention_weights @ V

    return output, attention_weights


class ScaledDotProductAttention:
    """缩放点积注意力类。"""

    def __init__(self, d_k: int):
        self.d_k = d_k

    def forward(self, Q: np.ndarray, K: np.ndarray, V: np.ndarray,
                mask: np.ndarray = None) -> tuple[np.ndarray, np.ndarray]:
        return dot_product_attention(Q, K, V, mask, scale=True)


class MultiHeadAttention:
    """
    多头注意力机制。

    MultiHead(Q, K, V) = Concat(head_1, ..., head_h) W^O
    where head_i = Attention(QW_i^Q, KW_i^K, VW_i^V)
    """

    def __init__(self, d_model: int, num_heads: int):
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        # 投影矩阵
        self.WQ = np.random.randn(d_model, d_model) * np.sqrt(2.0 / d_model)
        self.WK = np.random.randn(d_model, d_model) * np.sqrt(2.0 / d_model)
        self.WV = np.random.randn(d_model, d_model) * np.sqrt(2.0 / d_model)
        self.WO = np.random.randn(d_model, d_model) * np.sqrt(2.0 / d_model)

    def split_heads(self, X: np.ndarray) -> np.ndarray:
        """将最后一个维度分成多个头。"""
        batch_size, seq_len, d_model = X.shape
        X = X.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        return X.transpose(0, 2, 1, 3)  # (batch, heads, seq, d_k)

    def forward(self, Q: np.ndarray, K: np.ndarray, V: np.ndarray,
                mask: np.ndarray = None) -> tuple[np.ndarray, np.ndarray]:
        """
        前向传播。

        Args:
            Q: (batch, seq_len_q, d_model)
            K: (batch, seq_len_k, d_model)
            V: (batch, seq_len_k, d_model)

        Returns:
            output: (batch, seq_len_q, d_model)
            attention_weights: (batch, heads, seq_len_q, seq_len_k)
        """
        batch_size = Q.shape[0]

        # 线性投影
        Q = Q @ self.WQ
        K = K @ self.WK
        V = V @ self.WV

        # 分成多头
        Q = self.split_heads(Q)  # (batch, heads, seq, d_k)
        K = self.split_heads(K)
        V = self.split_heads(V)

        # 缩放点积注意力
        attn_output, attention_weights = dot_product_attention(
            Q.reshape(-1, Q.shape[-2], Q.shape[-1]),
            K.reshape(-1, K.shape[-2], K.shape[-1]),
            V.reshape(-1, V.shape[-2], V.shape[-1]),
            mask
        )

        # 恢复形状
        seq_len_q = Q.shape[2]
        attn_output = attn_output.reshape(batch_size, self.num_heads, seq_len_q, -1)
        attention_weights = attn_output.reshape(batch_size, self.num_heads, seq_len_q, -1)

        # 合并多头
        attn_output = attn_output.transpose(0, 2, 1, 3).reshape(batch_size, seq_len_q, -1)

        # 最终线性投影
        output = attn_output @ self.WO

        return output, attention_weights


def attention_is_all_you_need():
    """演示 Attention 的核心思想。"""
    print("=" * 60)
    print("注意力机制：核心思想")
    print("=" * 60)

    print("\n传统 Seq2Seq 的问题：")
    print("  - 编码器必须将整个序列压缩成固定向量")
    print("  - 长序列信息容易丢失")
    print("  - 解码器无法访问编码器的中间状态")

    print("\n注意力机制的解决方案：")
    print("  - 每个解码步骤可以直接访问所有编码器隐藏状态")
    print("  - 根据当前解码位置，计算对各编码器位置的关注度")
    print("  - 动态选择相关信息")


def demonstrate_sdot_attention():
    """演示缩放点积注意力。"""
    print("\n" + "=" * 60)
    print("缩放点积注意力演示")
    print("=" * 60)

    np.random.seed(42)

    # 简单示例
    seq_len = 4
    d_k = 8

    # 模拟 Query 和 Key
    Q = np.random.randn(seq_len, d_k)
    K = np.random.randn(seq_len, d_k)
    V = np.random.randn(seq_len, d_k)

    print(f"\nQuery 形状: {Q.shape}")
    print(f"Key 形状: {K.shape}")
    print(f"Value 形状: {V.shape}")

    # 计算注意力
    output, weights = dot_product_attention(Q, K, V)

    print(f"\n注意力权重形状: {weights.shape}")
    print(f"输出形状: {output.shape}")

    print("\n注意力权重矩阵（第一行）：")
    print(weights[0].round(3))

    print("\n观察：")
    print("  - 权重和为 1（Softmax 的效果）")
    print("  - 对角线元素通常最大（当前位置最重要）")
    print("  - 非对角线元素表示对其他位置的关注")


def self_attention_demo():
    """演示自注意力。"""
    print("\n" + "=" * 60)
    print("自注意力（Self-Attention）演示")
    print("=" * 60)

    # 自注意力：Q、K、V 来自同一输入
    print("\n自注意力的特点：")
    print("  - Q = K = V = X（来自同一序列）")
    print("  - 每个位置可以关注序列中的任意其他位置")
    print("  - 捕获长距离依赖关系")

    np.random.seed(42)

    # 模拟句子："I love natural language processing"
    # 5 个词，每个词 4 维向量
    seq_len = 5
    d_model = 8

    X = np.random.randn(seq_len, d_model)

    print(f"\n输入序列形状: {X.shape}")
    print("  5 个词，每个 8 维嵌入")

    # 自注意力
    output, weights = dot_product_attention(X, X, X)

    print(f"\n注意力权重矩阵:")
    words = ["I", "love", "natural", "language", "NLP"]
    print("      ", end="")
    for w in words:
        print(f"{w:>8}")
    for i, w in enumerate(words):
        print(f"{w:<8}", end="")
        print("  ".join(f"{weights[i,j]:.3f}" for j in range(seq_len)))


def multihead_attention_demo():
    """演示多头注意力。"""
    print("\n" + "=" * 60)
    print("多头注意力演示")
    print("=" * 60)

    print("\n多头注意力的优势：")
    print("  - 每个头可以学习不同类型的依赖")
    print("  - 头 1：句法关系（主语-动词）")
    print("  - 头 2：语义关系（同义词）")
    print("  - 头 3：位置关系（邻近词）")

    d_model = 256
    num_heads = 8
    d_k = d_model // num_heads

    print(f"\n配置：")
    print(f"  模型维度 d_model: {d_model}")
    print(f"  头数 num_heads: {num_heads}")
    print(f"  每头维度 d_k: {d_k}")

    # 模拟
    batch_size = 1
    seq_len = 10

    mha = MultiHeadAttention(d_model, num_heads)

    Q = np.random.randn(batch_size, seq_len, d_model)
    K = np.random.randn(batch_size, seq_len, d_model)
    V = np.random.randn(batch_size, seq_len, d_model)

    output, weights = mha.forward(Q, K, K)

    print(f"\n输入形状: {Q.shape}")
    print(f"输出形状: {output.shape}")
    print(f"注意力权重形状: {weights.shape}")


def attention_vs_rnn():
    """对比 Attention 和 RNN。"""
    print("\n" + "=" * 60)
    print("Attention vs RNN")
    print("=" * 60)

    print("\n| 特性 | RNN | Attention |")
    print("|------|-----|-----------|")
    print("| 长期依赖 | ❌ 梯度消失 | ✅ 直接连接 |")
    print("| 并行计算 | ❌ 顺序计算 | ✅ 完全并行 |")
    print("| 路径长度 | O(t) | O(1) |")
    print("| 位置感知 | ✅ 天然 | ❌ 需位置编码 |")
    print("| 计算复杂度 | O(n·d) | O(n²·d) |")

    print("\n路径长度说明：")
    print("  - RNN：从第一个词到第 N 个词需要 N 步")
    print("  - Attention：任意两词之间一步可达")


if __name__ == "__main__":
    attention_is_all_you_need()
    demonstrate_sdot_attention()
    self_attention_demo()
    multihead_attention_demo()
    attention_vs_rnn()