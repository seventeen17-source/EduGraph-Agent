"""反向传播算法完整实现，包含多层神经网络梯度计算与参数更新。

Related node: ml_backpropagation
Source IDs: book_hands_on_ml_3e_zh, book_deep_learning_ai
"""

from __future__ import annotations

import numpy as np


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid 激活函数。"""
    return 1 / (1 + np.exp(-np.clip(x, -500, 500)))


def sigmoid_derivative(s: np.ndarray) -> np.ndarray:
    """Sigmoid 的导数：s * (1 - s)。"""
    return s * (1 - s)


def relu(x: np.ndarray) -> np.ndarray:
    """ReLU 激活函数。"""
    return np.maximum(0, x)


def relu_derivative(a: np.ndarray) -> np.ndarray:
    """ReLU 的导数。"""
    return (a > 0).astype(float)


def cross_entropy_loss(y_pred: np.ndarray, y_true: np.ndarray) -> float:
    """交叉熵损失（针对 Softmax 输出）。"""
    # 数值稳定版本
    log_probs = y_pred - np.max(y_pred, axis=1, keepdims=True)
    log_probs = np.log(np.exp(log_probs).sum(axis=1))
    return -np.mean(log_probs[np.arange(len(y_true)), y_true])


def softmax(x: np.ndarray) -> np.ndarray:
    """Softmax 激活函数。"""
    exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
    return exp_x / np.sum(exp_x, axis=1, keepdims=True)


class DenseLayer:
    """全连接层。"""

    def __init__(self, input_dim: int, output_dim: int, activation: str = "relu"):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.activation = activation
        # Xavier 初始化
        scale = np.sqrt(2.0 / input_dim)
        self.W = np.random.randn(input_dim, output_dim) * scale
        self.b = np.zeros((1, output_dim))
        self.cache = {}

    def forward(self, X: np.ndarray) -> np.ndarray:
        """前向传播：Z = X @ W + b，然后激活。"""
        Z = X @ self.W + self.b
        self.cache["X"] = X
        self.cache["Z"] = Z

        if self.activation == "sigmoid":
            A = sigmoid(Z)
        elif self.activation == "relu":
            A = relu(Z)
        elif self.activation == "softmax":
            A = softmax(Z)
        else:
            A = Z
        self.cache["A"] = A
        return A

    def backward(
        self, dA: np.ndarray, learning_rate: float = 0.01
    ) -> np.ndarray:
        """反向传播：计算 dW, db, 并返回传往前一层的梯度。"""
        A = self.cache["A"]
        Z = self.cache["Z"]
        X = self.cache["X"]
        m = X.shape[0]

        # 激活函数导数
        if self.activation == "sigmoid":
            dZ = dA * sigmoid_derivative(A)
        elif self.activation == "relu":
            dZ = dA * relu_derivative(A)
        else:
            dZ = dA

        # 参数梯度
        dW = X.T @ dZ / m
        db = np.sum(dZ, axis=0, keepdims=True) / m
        dX = dZ @ self.W.T

        # 参数更新
        self.W -= learning_rate * dW
        self.b -= learning_rate * db

        return dX


class MLP:
    """多层感知机（用于演示反向传播）。"""

    def __init__(self, layer_dims: list[int], activations: list[str]):
        self.layers = []
        for i in range(len(layer_dims) - 1):
            self.layers.append(
                DenseLayer(layer_dims[i], layer_dims[i + 1], activations[i])
            )

    def forward(self, X: np.ndarray) -> np.ndarray:
        """前向传播。"""
        A = X
        for layer in self.layers:
            A = layer.forward(A)
        return A

    def backward(self, y_pred: np.ndarray, y_true: np.ndarray):
        """反向传播：计算损失梯度并反向传播。"""
        m = y_pred.shape[0]
        # Softmax + CrossEntropy 的梯度简化形式
        dA = (y_pred - y_true) / m

        for layer in reversed(self.layers):
            dA = layer.backward(dA)

    def train_step(
        self, X: np.ndarray, y: np.ndarray, lr: float = 0.01
    ) -> float:
        """单步训练：前向 + 反向 + 参数更新，返回损失。"""
        y_pred = self.forward(X)
        # 简单均方误差作为演示损失
        loss = float(np.mean((y_pred - y) ** 2))
        self.backward(y_pred, y)
        return loss


def demo_backprop():
    """演示反向传播训练过程。"""
    # 生成二分类数据
    rng = np.random.default_rng(42)
    X = rng.randn(100, 4)
    y = (X[:, 0] + X[:, 1] > 0).astype(float)

    # 构建 2 层 MLP
    model = MLP([4, 8, 1], ["relu", "sigmoid"])

    # 训练几步
    losses = []
    for epoch in range(5):
        loss = model.train_step(X, y, lr=0.1)
        losses.append(loss)
        print(f"Epoch {epoch}: loss={loss:.4f}")

    return losses


if __name__ == "__main__":
    demo_backprop()