"""感知机（Perceptron）完整实现，包含收敛性演示与 PLA 口袋算法对比。

Related node: ml_perceptron
Source IDs: book_hands_on_ml_3e_zh, book_mml_deisenroth
"""

from __future__ import annotations

import numpy as np


def sign(z: float) -> int:
    """符号函数：大于等于 0 输出 1，否则输出 -1。"""
    return 1 if z >= 0 else -1


class Perceptron:
    """标准感知机（PLA）。"""

    def __init__(self, lr: float = 1.0):
        self.lr = lr
        self.weights: np.ndarray | None = None
        self.bias: float = 0.0

    def _predict_raw(self, x: np.ndarray) -> float:
        """线性组合：w·x + b。"""
        return float(x @ self.weights + self.b)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """对整个样本矩阵预测，返回 ±1 标签。"""
        return np.array([sign(self._predict_raw(x)) for x in X])

    def fit(self, X: np.ndarray, y: np.ndarray, max_iter: int = 1000) -> int:
        """
        感知机学习算法（PLA）：对每个错分样本执行更新。
        若数据线性可分，算法会在有限步内收敛。
        返回实际迭代次数。
        """
        n_features = X.shape[1]
        self.weights = np.zeros(n_features)
        self.bias = 0.0

        for iteration in range(max_iter):
            errors = 0
            for x_i, y_i in zip(X, y):
                if sign(self._predict_raw(x_i)) != y_i:
                    # 感知机更新规则
                    self.weights += self.lr * y_i * x_i
                    self.bias += self.lr * y_i
                    errors += 1
            if errors == 0:
                return iteration + 1
        return max_iter


class PocketPLA:
    """口袋算法（Pocket PLA）：保留历史上最好的 w。"""

    def __init__(self, lr: float = 1.0):
        self.lr = lr
        self.best_weights: np.ndarray | None = None
        self.best_bias: float = 0.0
        self.best_errors: int = float("inf")

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([sign(float(x @ self.best_weights + self.best_bias)) for x in X])

    def fit(self, X: np.ndarray, y: np.ndarray, max_iter: int = 1000) -> list[int]:
        """口袋算法主循环，返回每轮的最优错误数历史。"""
        n_features = X.shape[1]
        w = np.zeros(n_features)
        b = 0.0
        errors_history = []

        for _ in range(max_iter):
            # 标准 PLA 一次扫描
            for x_i, y_i in zip(X, y):
                if sign(float(x_i @ w + b)) != y_i:
                    w = w + self.lr * y_i * x_i
                    b = b + self.lr * y_i
                    break

            # 计算当前 w 的错误数
            preds = np.array([sign(float(x @ w + b)) for x in X])
            errors = int(np.sum(preds != y))
            errors_history.append(errors)

            # 更新口袋
            if errors < self.best_errors:
                self.best_errors = errors
                self.best_weights = w.copy()
                self.best_bias = b

            if errors == 0:
                break

        return errors_history


if __name__ == "__main__":
    # 生成线性可分数据
    rng = np.random.default_rng(0)
    n = 100

    # 类别 1：分布在右上区域
    X1 = rng.normal(loc=[2, 2], scale=0.8, size=(n // 2, 2))
    y1 = np.ones(n // 2, dtype=int)

    # 类别 -1：分布在左下区域
    X2 = rng.normal(loc=[-1, -1], scale=0.8, size=(n // 2, 2))
    y2 = -np.ones(n // 2, dtype=int)

    X = np.vstack([X1, X2])
    y = np.concatenate([y1, y2])

    # 训练标准感知机
    pla = Perceptron(lr=1.0)
    steps = pla.fit(X, y)
    print(f"PLA 收敛步数: {steps}")
    print(f"最终 weights: {pla.weights.round(3)}, bias: {pla.bias:.3f}")

    preds = pla.predict(X)
    acc = float(np.mean(preds == y))
    print(f"训练准确率: {acc:.2%}")

    # 口袋算法演示
    pocket = PocketPLA(lr=1.0)
    errors_hist = pocket.fit(X, y, max_iter=100)
    print(f"Pocket 最优错误数: {pocket.best_errors} / {n}")
    print(f"前 5 轮错误数: {errors_hist[:5]}")