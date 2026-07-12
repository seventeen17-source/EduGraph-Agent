"""K-Means 聚类算法完整实现，包含迭代过程可视化与肘部法则选 K。

Related node: ml_kmeans
Source IDs: book_hands_on_ml_3e_zh, book_mml_deisenroth
"""

from __future__ import annotations

import numpy as np


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """计算两个向量的欧氏距离。"""
    return float(np.linalg.norm(a - b))


def initialize_centroids(
    X: np.ndarray, k: int, seed: int = 42
) -> np.ndarray:
    """随机选取 K 个样本作为初始簇中心（K-Means++ 风格）。"""
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    centroids = [X[rng.integers(0, n)]]
    for _ in range(1, k):
        # 计算每个样本到最近中心的距离
        dists = np.array([
            min(euclidean_distance(x, c) for c in centroids)
            for x in X
        ])
        # 按距离平方加权随机选下一个中心
        probs = dists / dists.sum()
        centroids.append(X[rng.choice(n, p=probs)])
    return np.array(centroids)


def assign_clusters(
    X: np.ndarray, centroids: np.ndarray
) -> np.ndarray:
    """将每个样本分配给最近的簇中心。返回形状 (n,) 的簇标签数组。"""
    n = X.shape[0]
    labels = np.zeros(n, dtype=int)
    for i in range(n):
        min_dist = float("inf")
        for j, c in enumerate(centroids):
            d = euclidean_distance(X[i], c)
            if d < min_dist:
                min_dist = d
                labels[i] = j
    return labels


def update_centroids(
    X: np.ndarray, labels: np.ndarray, k: int
) -> np.ndarray:
    """重新计算每个簇的中心（取簇内样本均值）。"""
    centroids = []
    for j in range(k):
        members = X[labels == j]
        if len(members) > 0:
            centroids.append(members.mean(axis=0))
        else:
            # 空簇：重新随机初始化
            centroids.append(X[np.random.randint(len(X))])
    return np.array(centroids)


def kmeans(
    X: np.ndarray,
    k: int,
    max_iter: int = 100,
    tol: float = 1e-4,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """K-Means 主循环，返回 (centroids, labels, inertia_history)。"""
    centroids = initialize_centroids(X, k, seed)
    labels = assign_clusters(X, centroids)
    inertia_history = [float(np.sum((X - centroids[labels]) ** 2))]

    for _ in range(max_iter):
        labels = assign_clusters(X, centroids)
        new_centroids = update_centroids(X, labels, k)
        inertia = float(np.sum((X - new_centroids[labels]) ** 2))
        inertia_history.append(inertia)

        if np.linalg.norm(new_centroids - centroids) < tol:
            centroids = new_centroids
            break
        centroids = new_centroids

    return centroids, labels, inertia_history


def elbow_method(
    X: np.ndarray, k_range: range, seed: int = 42
) -> list[tuple[int, float]]:
    """肘部法则：计算不同 K 值的惯性（SSE），用于选择最优 K。"""
    results = []
    for k in k_range:
        _, _, inertia_history = kmeans(X, k, seed=seed)
        results.append((k, inertia_history[-1]))
    return results


if __name__ == "__main__":
    # 生成 3 个高斯簇的演示数据
    rng = np.random.default_rng(0)
    X1 = rng.normal(loc=[0, 0], scale=0.5, size=(50, 2))
    X2 = rng.normal(loc=[5, 5], scale=0.5, size=(50, 2))
    X3 = rng.normal(loc=[0, 5], scale=0.5, size=(50, 2))
    X = np.vstack([X1, X2, X3])

    k = 3
    centroids, labels, inertia = kmeans(X, k, seed=0)
    print(f"K={k}  最终惯性: {inertia[-1]:.2f}")
    print(f"各簇样本数: {np.bincount(labels)}")
    print(f"簇中心:\n{centroids}")

    # 肘部法则选 K
    elbow = elbow_method(X, range(1, 7), seed=0)
    print("\n肘部法则结果 (K -> SSE):")
    for k_val, sse in elbow:
        print(f"  K={k_val}: SSE={sse:.2f}")