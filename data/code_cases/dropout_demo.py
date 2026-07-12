"""Dropout 机制完整实现：训练/测试阶段对比、正则化效果可视化。

Related node: ml_dropout
Source IDs: book_deep_learning_ai, book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np
from typing import Callable


def dropout_forward(X: np.ndarray, keep_prob: float = 0.5, training: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """
    Dropout 前向传播。

    Args:
        X: 输入激活值，形状为 (batch_size, n_features) 或 (batch_size, n_neurons)
        keep_prob: 保留概率
        training: 是否在训练模式（True = 应用 dropout，False = 不应用）

    Returns:
        (output, mask): 输出激活值和 dropout 掩码
    """
    if training:
        # 训练时：随机丢弃神经元
        mask = np.random.binomial(1, keep_prob, size=X.shape) / keep_prob
        output = X * mask
    else:
        # 测试时：不丢弃，乘以 keep_prob 补偿期望
        mask = np.ones_like(X)
        output = X  # 测试时不乘，模型本身期望输出已经考虑了 dropout

    return output, mask


def dropout_forward_layer(X: np.ndarray, keep_prob: float = 0.5, training: bool = True) -> dict:
    """
    Dropout 前向传播（层版本），返回缓存用于反向传播。

    Args:
        X: 输入
        keep_prob: 保留概率
        training: 是否训练模式

    Returns:
        包含输出和掩码的字典
    """
    cache = {"X": X, "keep_prob": keep_prob, "mask": None}

    if training:
        cache["mask"] = np.random.binomial(1, keep_prob, size=X.shape) / keep_prob
        output = X * cache["mask"]
    else:
        output = X

    cache["output"] = output
    return cache


def dropout_backward(dout: np.ndarray, cache: dict) -> np.ndarray:
    """
    Dropout 反向传播。

    Args:
        dout: 上游梯度
        cache: 前向传播时保存的缓存

    Returns:
        输入层的梯度
    """
    mask = cache["mask"]
    if mask is not None:
        return dout * mask
    return dout


class DropoutLayer:
    """可训练的 Dropout 层。"""

    def __init__(self, keep_prob: float = 0.5):
        self.keep_prob = keep_prob
        self.training: bool = False
        self.mask: np.ndarray | None = None

    def forward(self, X: np.ndarray, training: bool = True) -> np.ndarray:
        """前向传播。"""
        self.training = training
        if training:
            self.mask = np.random.binomial(1, self.keep_prob, size=X.shape) / self.keep_prob
            return X * self.mask
        return X

    def backward(self, dout: np.ndarray) -> np.ndarray:
        """反向传播。"""
        if self.mask is not None:
            return dout * self.mask
        return dout


def compare_with_without_dropout():
    """
    对比有 Dropout 和无 Dropout 模型的训练效果。
    """
    np.random.seed(42)

    # 生成复杂非线性数据
    n_samples = 500
    X = np.random.randn(n_samples, 20)
    # 创建一些冗余特征和高相关特征
    X[:, 5:10] = X[:, :5] + 0.5 * np.random.randn(n_samples, 5)  # 冗余特征
    y = (X[:, 0] + X[:, 1]**2 + 0.5 * X[:, 5] + np.sin(X[:, 10]) > 0).astype(int)

    print("=" * 60)
    print("Dropout 效果对比实验")
    print("=" * 60)
    print(f"数据维度: {X.shape}")
    print(f"正类比例: {y.mean():.2%}")

    # 简单神经网络（有/无 Dropout）
    class SimpleNN:
        def __init__(self, input_dim, hidden_dims, output_dim, dropout_rates=None):
            self.params = []
            self.dropout_rates = dropout_rates or [0.0] * len(hidden_dims)

            prev_dim = input_dim
            for i, h_dim in enumerate(hidden_dims):
                self.params.append({
                    'W': np.random.randn(prev_dim, h_dim) * np.sqrt(2.0 / prev_dim),
                    'b': np.zeros(h_dim),
                    'dropout_rate': self.dropout_rates[i]
                })
                prev_dim = h_dim

            self.params.append({
                'W': np.random.randn(prev_dim, output_dim) * np.sqrt(2.0 / prev_dim),
                'b': np.zeros(output_dim)
            })

        def relu(self, x):
            return np.maximum(0, x)

        def relu_grad(self, x):
            return (x > 0).astype(float)

        def softmax(self, x):
            exp_x = np.exp(x - x.max(axis=1, keepdims=True))
            return exp_x / exp_x.sum(axis=1, keepdims=True)

        def forward(self, X, training=True, dropout_masks=None):
            self.cache = {'X': [X], 'z': [], 'a': [], 'dropout_masks': []}
            current = X

            for i, layer in enumerate(self.params[:-1]):
                z = current @ layer['W'] + layer['b']
                self.cache['z'].append(z)
                a = self.relu(z)
                self.cache['a'].append(a)

                # Dropout
                if training and layer['dropout_rate'] > 0:
                    mask = (np.random.rand(*a.shape) < (1 - layer['dropout_rate'])) / (1 - layer['dropout_rate'])
                    a = a * mask
                    self.cache['dropout_masks'].append(mask)

                current = a
                self.cache['X'].append(current)

            # 输出层
            z = current @ self.params[-1]['W'] + self.params[-1]['b']
            self.cache['z'].append(z)
            probs = self.softmax(z)
            self.cache['a'].append(probs)

            return probs

        def backward(self, y):
            m = y.shape[0]
            self.grads = []

            # 输出层梯度
            probs = self.cache['a'][-1]
            dz = probs.copy()
            dz[np.arange(m), y] -= 1

            for i in reversed(range(len(self.params))):
                layer = self.params[i]
                prev_a = self.cache['X'][i]

                dW = prev_a.T @ dz / m
                db = dz.mean(axis=0)

                if i > 0:
                    # 反向传播 Dropout
                    if self.cache['dropout_masks']:
                        mask = self.cache['dropout_masks'][i-1]
                        dz = (dz @ self.params[i]['W'].T) * mask
                    else:
                        dz = dz @ self.params[i]['W'].T
                    dz = dz * self.relu_grad(self.cache['z'][i-1])

                self.grads.insert(0, {'dW': dW, 'db': db})

            return self.grads

        def update(self, lr=0.01):
            for i, layer in enumerate(self.params):
                layer['W'] -= lr * self.grads[i]['dW']
                layer['b'] -= lr * self.grads[i]['db']

    # 训练函数
    def train(nn, X, y, epochs=100, lr=0.1):
        losses = []
        for epoch in range(epochs):
            # 前向
            probs = nn.forward(X, training=True)
            # 损失
            loss = -np.mean(np.log(probs[np.arange(len(y)), y] + 1e-10))
            losses.append(loss)
            # 反向
            nn.backward(y)
            # 更新
            nn.update(lr)
        return losses

    def evaluate(nn, X, y):
        probs = nn.forward(X, training=False)
        preds = probs.argmax(axis=1)
        return (preds == y).mean()

    # 无 Dropout 模型
    nn_no_dropout = SimpleNN(20, [64, 32], 2, dropout_rates=[0.0, 0.0])

    # 有 Dropout 模型
    nn_with_dropout = SimpleNN(20, [64, 32], 2, dropout_rates=[0.2, 0.3])

    # 训练
    print("\n训练无 Dropout 模型...")
    losses_no_dropout = train(nn_no_dropout, X, y, epochs=200, lr=0.1)

    print("训练有 Dropout 模型...")
    losses_with_dropout = train(nn_with_dropout, X, y, epochs=200, lr=0.1)

    # 评估
    train_acc_no_dropout = evaluate(nn_no_dropout, X, y)
    test_acc_no_dropout = train_acc_no_dropout  # 本例用同一数据集

    train_acc_with_dropout = evaluate(nn_with_dropout, X, y)
    test_acc_with_dropout = train_acc_with_dropout

    print("\n" + "=" * 40)
    print("训练结果对比")
    print("=" * 40)
    print(f"无 Dropout - 最终损失: {losses_no_dropout[-1]:.4f}")
    print(f"有 Dropout - 最终损失: {losses_with_dropout[-1]:.4f}")
    print(f"\n无 Dropout - 训练准确率: {train_acc_no_dropout:.2%}")
    print(f"有 Dropout - 训练准确率: {train_acc_with_dropout:.2%}")


def inverted_dropout_demo():
    """演示 Inverted Dropout（测试时不需要额外处理）。"""
    print("\n" + "=" * 60)
    print("Inverted Dropout 演示")
    print("=" * 60)

    # 模拟神经元输出
    X = np.array([2.0, 4.0, 1.5, 3.0, 0.5])
    keep_prob = 0.8

    print(f"原始激活值: {X}")
    print(f"Keep prob: {keep_prob}")

    # 训练时
    mask = np.random.binomial(1, keep_prob, size=X.shape)
    X_train = X * mask / keep_prob
    print(f"\n训练时 (应用 dropout + inverted):")
    print(f"  掩码: {mask}")
    print(f"  输出: {X_train}")
    print(f"  期望值（多次采样的平均）: ≈ {X}")

    # 测试时
    X_test = X
    print(f"\n测试时 (不应用 dropout):")
    print(f"  输出: {X_test}")

    print("\n注意：Inverted Dropout 使测试时输出期望等于训练时期望，")
    print("      因此测试时不需要做任何额外处理。")


if __name__ == "__main__":
    inverted_dropout_demo()
    compare_with_without_dropout()
