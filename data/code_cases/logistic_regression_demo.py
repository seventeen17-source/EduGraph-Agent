"""逻辑回归完整实现，包含 Sigmoid、交叉熵损失、梯度下降与预测概率输出。

Related node: ml_logistic_regression
Source IDs: book_hands_on_ml_3e_zh, book_mml_deisenroth
"""

from __future__ import annotations

import numpy as np


def sigmoid(z: np.ndarray) -> np.ndarray:
    """Sigmoid 函数：将线性输出映射为 (0,1) 概率。"""
    return 1 / (1 + np.exp(-np.clip(z, -500, 500)))


def compute_loss(
    h: np.ndarray, y: np.ndarray, eps: float = 1e-15
) -> float:
    """二元交叉熵损失（数值稳定版本）。"""
    h = np.clip(h, eps, 1 - eps)
    return -float(
        np.mean(y * np.log(h) + (1 - y) * np.log(1 - h))
    )


def predict_proba(X: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    """返回样本属于正类的概率。"""
    z = X @ weights + bias
    return sigmoid(z)


def predict(X: np.ndarray, weights: np.ndarray, bias: float, threshold: float = 0.5) -> np.ndarray:
    """返回二分类标签（0 或 1）。"""
    return (predict_proba(X, weights, bias) >= threshold).astype(int)


def fit(
    X: np.ndarray,
    y: np.ndarray,
    lr: float = 0.1,
    epochs: int = 1000,
    tol: float = 1e-6,
) -> tuple[np.ndarray, float, list[float]]:
    """使用梯度下降训练逻辑回归。返回 (weights, bias, loss_history)。"""
    n_features = X.shape[1]
    weights = np.zeros(n_features)
    bias = 0.0
    loss_history = []

    for _ in range(epochs):
        # 前向传播
        h = predict_proba(X, weights, bias)

        # 计算损失
        loss = compute_loss(h, y)
        loss_history.append(loss)

        # 梯度计算
        m = len(y)
        dw = (1 / m) * (X.T @ (h - y))
        db = (1 / m) * np.sum(h - y)

        # 参数更新
        weights -= lr * dw
        bias -= lr * db

        # 早停
        if len(loss_history) > 1 and abs(loss_history[-1] - loss_history[-2]) < tol:
            break

    return weights, bias, loss_history


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """分类准确率。"""
    return float(np.mean(y_true == y_pred))


if __name__ == "__main__":
    # 生成二分类演示数据
    rng = np.random.default_rng(0)
    n = 200
    # 两类高斯数据
    X1 = rng.normal(loc=[2, 3], scale=1.2, size=(n // 2, 2))
    X2 = rng.normal(loc=[6, 1], scale=1.2, size=(n // 2, 2))
    X = np.vstack([X1, X2])
    y = np.array([0] * (n // 2) + [1] * (n // 2))

    # 训练
    weights, bias, losses = fit(X, y, lr=0.1, epochs=500)

    # 评估
    preds = predict(X, weights, bias)
    print(f"训练准确率: {accuracy(y, preds):.2%}")
    print(f"模型参数: weights={weights.round(3)}, bias={bias:.3f}")
    print(f"最终损失: {losses[-1]:.4f}")

    # 预测新样本
    new_point = np.array([[4, 2]])
    prob = predict_proba(new_point, weights, bias)[0]
    print(f"新样本概率: {prob:.2f}  预测: {'正类' if prob >= 0.5 else '负类'}")