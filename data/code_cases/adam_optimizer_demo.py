"""Adam 优化器完整实现：从 SGD 到 Adam 的演化过程。

Related node: ml_gradient_optimization_basic
Source IDs: book_deep_learning_ai, book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np
from typing import Callable


def sgd_update(params: np.ndarray, grads: np.ndarray, lr: float) -> np.ndarray:
    """标准随机梯度下降更新。"""
    return params - lr * grads


def momentum_update(params: np.ndarray, grads: np.ndarray, velocity: np.ndarray,
                    lr: float, momentum: float = 0.9) -> tuple[np.ndarray, np.ndarray]:
    """
    动量 SGD 更新。

    v_t = β * v_{t-1} + (1 - β) * ∇L
    θ_t = θ_{t-1} - lr * v_t
    """
    velocity = momentum * velocity + (1 - momentum) * grads
    params = params - lr * velocity
    return params, velocity


def rmsprop_update(params: np.ndarray, grads: np.ndarray, squares: np.ndarray,
                   lr: float, decay: float = 0.9, eps: float = 1e-8) -> tuple[np.ndarray, np.ndarray]:
    """
    RMSprop 更新：每个参数独立的学习率。

    E[g²]_t = β * E[g²]_{t-1} + (1 - β) * g²_t
    θ_t = θ_{t-1} - lr / sqrt(E[g²]_t + ε) * g_t
    """
    squares = decay * squares + (1 - decay) * (grads ** 2)
    params = params - lr * grads / np.sqrt(squares + eps)
    return params, squares


def adam_update(params: np.ndarray, grads: np.ndarray,
                m: np.ndarray, v: np.ndarray,
                t: int, lr: float = 0.001,
                beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Adam 更新：Adaptive Moment Estimation。

    m_t = β1 * m_{t-1} + (1 - β1) * g_t        (一阶矩估计)
    v_t = β2 * v_{t-1} + (1 - β2) * g²_t       (二阶矩估计)

    m̂_t = m_t / (1 - β1^t)                      (偏置校正)
    v̂_t = v_t / (1 - β2^t)                      (偏置校正)

    θ_t = θ_{t-1} - lr * m̂_t / (sqrt(v̂_t) + ε)
    """
    # 更新一阶和二阶矩估计
    m = beta1 * m + (1 - beta1) * grads
    v = beta2 * v + (1 - beta2) * (grads ** 2)

    # 偏置校正
    m_hat = m / (1 - beta1 ** t)
    v_hat = v / (1 - beta2 ** t)

    # 参数更新
    params = params - lr * m_hat / (np.sqrt(v_hat) + eps)

    return params, m, v


class AdamOptimizer:
    """Adam 优化器类。"""

    def __init__(self, lr: float = 0.001, beta1: float = 0.9, beta2: float = 0.999,
                 eps: float = 1e-8):
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.t = 0
        self.m: dict = {}  # 一阶矩
        self.v: dict = {}  # 二阶矩

    def step(self, params_dict: dict[str, np.ndarray], grads_dict: dict[str, np.ndarray]):
        """
        执行一步 Adam 更新。

        Args:
            params_dict: 参数字典
            grads_dict: 梯度字典
        """
        self.t += 1

        for name, params in params_dict.items():
            grads = grads_dict[name]

            # 初始化一阶和二阶矩
            if name not in self.m:
                self.m[name] = np.zeros_like(params)
                self.v[name] = np.zeros_like(params)

            # Adam 更新
            m = self.beta1 * self.m[name] + (1 - self.beta1) * grads
            v = self.beta2 * self.v[name] + (1 - self.beta2) * (grads ** 2)

            # 偏置校正
            m_hat = m / (1 - self.beta1 ** self.t)
            v_hat = v / (1 - self.beta2 ** self.t)

            # 更新参数
            params_dict[name] = params - self.lr * m_hat / (np.sqrt(v_hat) + self.eps)

            # 保存动量
            self.m[name] = m
            self.v[name] = v

        return params_dict


def compare_optimizers():
    """对比不同优化器在病态曲面上的收敛速度。"""
    print("=" * 60)
    print("优化器对比：SGD vs Momentum vs RMSprop vs Adam")
    print("=" * 60)

    # 病态二次函数：f(x, y) = x² + 25y²
    # 在 y 方向曲率大，收敛困难
    def rosenbrock(x: np.ndarray) -> float:
        """Rosenbrock 函数。"""
        return (1 - x[0])**2 + 100 * (x[1] - x[0]**2)**2

    def rosenbrock_grad(x: np.ndarray) -> np.ndarray:
        """Rosenbrock 函数的梯度。"""
        dx0 = -2 * (1 - x[0]) - 400 * x[0] * (x[1] - x[0]**2)
        dx1 = 200 * (x[1] - x[0]**2)
        return np.array([dx0, dx1])

    # 优化器配置
    optimizers = {
        'SGD': {'lr': 0.001},
        'Momentum': {'lr': 0.001, 'momentum': 0.9},
        'RMSprop': {'lr': 0.01, 'decay': 0.9},
        'Adam': {'lr': 0.001, 'beta1': 0.9, 'beta2': 0.999},
    }

    initial_pos = np.array([-1.5, 1.5])

    print(f"\n初始位置: {initial_pos}")
    print(f"初始损失: {rosenbrock(initial_pos):.2f}")
    print("\n" + "-" * 60)

    for name, config in optimizers.items():
        x = initial_pos.copy()
        lr = config.get('lr', 0.001)
        losses = []

        m = np.zeros(2)
        v = np.zeros(2)
        squares = np.zeros(2)
        velocity = np.zeros(2)

        for t in range(1, 1001):
            grads = rosenbrock_grad(x)

            if name == 'SGD':
                x = x - lr * grads
            elif name == 'Momentum':
                velocity = config['momentum'] * velocity + (1 - config['momentum']) * grads
                x = x - lr * velocity
            elif name == 'RMSprop':
                squares = config['decay'] * squares + (1 - config['decay']) * (grads ** 2)
                x = x - lr * grads / np.sqrt(squares + 1e-8)
            elif name == 'Adam':
                m = config['beta1'] * m + (1 - config['beta1']) * grads
                v = config['beta2'] * v + (1 - config['beta2']) * (grads ** 2)
                m_hat = m / (1 - config['beta1'] ** t)
                v_hat = v / (1 - config['beta2'] ** t)
                x = x - lr * m_hat / (np.sqrt(v_hat) + 1e-8)

            losses.append(rosenbrock(x))

            if t % 200 == 0:
                print(f"{name:<12}: iter={t:4d}, loss={losses[-1]:.4f}, pos=({x[0]:.3f}, {x[1]:.3f})")

    print("\n观察：")
    print("  - SGD 在曲率大的方向上震荡严重，收敛最慢")
    print("  - Momentum 通过累积速度减少震荡")
    print("  - RMSprop 通过自适应学习率适应不同方向")
    print("  - Adam 结合两者优点，通常收敛最快最稳定")


def adam_vs_sgd_on_saddle():
    """演示 Adam 和 SGD 在鞍点附近的行为差异。"""
    print("\n" + "=" * 60)
    print("Adam vs SGD：鞍点逃脱能力")
    print("=" * 60)

    # 鞍点函数：f(x, y) = x² - y²
    def saddle(x: np.ndarray) -> float:
        return x[0]**2 - x[1]**2

    def saddle_grad(x: np.ndarray) -> np.ndarray:
        return np.array([2*x[0], -2*x[1]])

    # 测试不同初始点
    test_points = [
        np.array([0.1, 0.1]),   # 靠近鞍点中心
        np.array([1.0, 1.0]),
    ]

    print("\n从不同初始点出发：")
    for x0 in test_points:
        print(f"\n初始位置: {x0}, 函数值: {saddle(x0):.4f}")

        # SGD
        x_sgd = x0.copy()
        for _ in range(100):
            grads = saddle_grad(x_sgd)
            x_sgd = x_sgd - 0.1 * grads

        # Adam
        x_adam = x0.copy()
        m = np.zeros(2)
        v = np.zeros(2)
        for t in range(1, 101):
            grads = saddle_grad(x_adam)
            m = 0.9 * m + 0.1 * grads
            v = 0.999 * v + 0.001 * (grads ** 2)
            m_hat = m / (1 - 0.9 ** t)
            v_hat = v / (1 - 0.999 ** t)
            x_adam = x_adam - 0.1 * m_hat / (np.sqrt(v_hat) + 1e-8)

        print(f"  SGD  终点: ({x_sgd[0]:.4f}, {x_sgd[1]:.4f}), f={saddle(x_sgd):.4f}")
        print(f"  Adam 终点: ({x_adam[0]:.4f}, {x_adam[1]:.4f}), f={saddle(x_adam):.4f}")


if __name__ == "__main__":
    compare_optimizers()
    adam_vs_sgd_on_saddle()
