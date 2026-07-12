"""神经网络激活函数完整实现：Sigmoid、Tanh、ReLU、Leaky ReLU、ELU、Softmax。

Related node: ml_activation_function
Source IDs: book_deep_learning_ai, book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid 激活函数：σ(x) = 1 / (1 + exp(-x))。"""
    return 1 / (1 + np.exp(-np.clip(x, -500, 500)))


def sigmoid_derivative(x: np.ndarray) -> np.ndarray:
    """Sigmoid 的导数：σ'(x) = σ(x) * (1 - σ(x))。"""
    s = sigmoid(x)
    return s * (1 - s)


def tanh(x: np.ndarray) -> np.ndarray:
    """双曲正切函数：tanh(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))。"""
    return np.tanh(x)


def tanh_derivative(x: np.ndarray) -> np.ndarray:
    """Tanh 的导数：tanh'(x) = 1 - tanh²(x)。"""
    return 1 - np.tanh(x) ** 2


def relu(x: np.ndarray) -> np.ndarray:
    """ReLU：Rectified Linear Unit，f(x) = max(0, x)。"""
    return np.maximum(0, x)


def relu_derivative(x: np.ndarray) -> np.ndarray:
    """ReLU 的导数：x > 0 时为 1，否则为 0。"""
    return (x > 0).astype(float)


def leaky_relu(x: np.ndarray, alpha: float = 0.01) -> np.ndarray:
    """Leaky ReLU：f(x) = x if x > 0 else αx，防止神经元死亡。"""
    return np.where(x > 0, x, alpha * x)


def leaky_relu_derivative(x: np.ndarray, alpha: float = 0.01) -> np.ndarray:
    """Leaky ReLU 的导数。"""
    return np.where(x > 0, 1, alpha)


def elu(x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """ELU：Exponential Linear Unit，x > 0 时为 x，否则为 α(exp(x) - 1)。"""
    return np.where(x > 0, x, alpha * (np.exp(x) - 1))


def elu_derivative(x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """ELU 的导数。"""
    return np.where(x > 0, 1, elu(x, alpha) + alpha)


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """
    Softmax 函数：将向量转换为概率分布。
    softmax(x)_i = exp(x_i) / Σexp(x_j)

    数值稳定版本：减去最大值。
    """
    x_shifted = x - np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x_shifted)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


def softmax_derivative(x: np.ndarray) -> np.ndarray:
    """Softmax 的雅可比矩阵（对角元素）。"""
    s = softmax(x)
    return s * (1 - s)


def swish(x: np.ndarray, beta: float = 1.0) -> np.ndarray:
    """Swish：f(x) = x · σ(βx)，自门控激活函数。"""
    return x * sigmoid(beta * x)


def swish_derivative(x: np.ndarray, beta: float = 1.0) -> np.ndarray:
    """Swish 的导数。"""
    s = sigmoid(beta * x)
    return s + beta * x * s * (1 - s)


def mish(x: np.ndarray) -> np.ndarray:
    """Mish：f(x) = x · tanh(softplus(x))。"""
    return x * np.tanh(np.log(1 + np.exp(x)))


def mish_derivative(x: np.ndarray) -> np.ndarray:
    """Mish 的导数。"""
    sp = np.log(1 + np.exp(x))  # softplus
    tanh_sp = np.tanh(sp)
    sigmoid_x = sigmoid(x)
    return tanh_sp + x * sigmoid_x * (1 - tanh_sp ** 2)


class ActivationFunctions:
    """常用激活函数集合。"""

    FUNCTIONS = {
        'sigmoid': (sigmoid, sigmoid_derivative),
        'tanh': (tanh, tanh_derivative),
        'relu': (relu, relu_derivative),
        'leaky_relu': (lambda x: leaky_relu(x, 0.01), lambda x: leaky_relu_derivative(x, 0.01)),
        'elu': (lambda x: elu(x, 1.0), lambda x: elu_derivative(x, 1.0)),
        'swish': (swish, lambda x: swish_derivative(x, 1.0)),
        'mish': (mish, mish_derivative),
    }

    @classmethod
    def get(cls, name: str):
        return cls.FUNCTIONS.get(name, (sigmoid, sigmoid_derivative))


if __name__ == "__main__":
    print("=" * 60)
    print("激活函数对比演示")
    print("=" * 60)

    # 测试数据
    x = np.linspace(-5, 5, 100)

    print("\n1. 各激活函数值域：")
    print("-" * 40)
    for name in ['sigmoid', 'tanh', 'relu', 'leaky_relu', 'elu', 'swish', 'mish']:
        func, _ = ActivationFunctions.get(name)
        y = func(x)
        print(f"{name:<15}: range=[{y.min():.3f}, {y.max():.3f}]")

    print("\n2. 梯度消失分析：")
    print("-" * 40)
    print("当 |x| 很大时，各函数的梯度：")
    for name in ['sigmoid', 'tanh', 'relu']:
        func, grad = ActivationFunctions.get(name)
        y_grad = grad(x)
        # 计算 x > 3 时梯度的最大值
        large_x_grad = grad(x[np.abs(x) > 3]).max()
        print(f"{name:<15}: gradient at |x|>3 ≈ {large_x_grad:.6f}")

    print("\n3. 神经元死亡分析（ReLU vs Leaky ReLU）：")
    print("-" * 40)
    x_neg = np.array([-10, -5, -1, 0, 1, 5, 10])
    print(f"{'x':<10} {'ReLU':<15} {'Leaky ReLU':<15} {'ELU':<15}")
    for xi in x_neg:
        x_arr = np.array([xi])
        print(f"{xi:<10} {relu(x_arr)[0]:<15.4f} {leaky_relu(x_arr)[0]:<15.4f} {elu(x_arr)[0]:<15.4f}")

    print("\n4. Softmax 数值稳定性：")
    print("-" * 40)
    # 演示数值稳定性问题
    x_large = np.array([1000, 1001, 1002])
    print(f"原始输入: {x_large}")
    print(f"普通 softmax（会溢出）: {sigmoid(x_large)[:1]}...")  # 近似结果

    x_shifted = x_large - np.max(x_large)
    exp_shifted = np.exp(x_shifted)
    softmax_stable = exp_shifted / np.sum(exp_shifted)
    print(f"数值稳定 softmax: {softmax_stable}")
    print(f"概率和: {softmax_stable.sum():.6f}")

    print("\n5. 多分类任务中的 Softmax：")
    print("-" * 40)
    logits = np.array([2.0, 1.0, 0.5, 0.1])
    probs = softmax(logits)
    print(f"Logits: {logits}")
    print(f"Probabilities: {probs.round(4)}")
    print(f"预测类别: {np.argmax(probs)}")
