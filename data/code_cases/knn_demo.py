"""KNN（K近邻）完整实现：分类与回归。

Related node: ml_metric_learning
Source IDs: book_hands_on_ml_3e_zh, book_zhou_ml
"""

from __future__ import annotations

import numpy as np
from collections import Counter


def euclidean_distance(x1: np.ndarray, x2: np.ndarray) -> float:
    """欧氏距离：||x1 - x2||₂。"""
    return np.sqrt(np.sum((x1 - x2) ** 2))


def manhattan_distance(x1: np.ndarray, x2: np.ndarray) -> float:
    """曼哈顿距离：Σ|x1_i - x2_i|。"""
    return np.sum(np.abs(x1 - x2))


def cosine_similarity(x1: np.ndarray, x2: np.ndarray) -> float:
    """余弦相似度：(x1·x2) / (||x1|| * ||x2||)。"""
    dot = np.dot(x1, x2)
    norm1 = np.linalg.norm(x1)
    norm2 = np.linalg.norm(x2)
    return dot / (norm1 * norm2)


def minkowski_distance(x1: np.ndarray, x2: np.ndarray, p: float = 3) -> float:
    """Minkowski 距离：Σ|x1_i - x2_i|^p 的 p 次方根。"""
    return np.power(np.sum(np.abs(x1 - x2) ** p), 1/p)


def find_k_nearest(X_train: np.ndarray, x_test: np.ndarray, k: int,
                 distance_fn: Callable = euclidean_distance) -> tuple[np.ndarray, np.ndarray]:
    """
    找到 K 近邻。

    Returns:
        (distances, indices): 距离和对应的训练集索引
    """
    distances = np.array([distance_fn(x_test, x_train[i]) for i in range(len(X_train))])
    k_nearest_idx = np.argsort(distances)[:k]
    return distances[k_nearest_idx], k_nearest_idx


class KNNClassifier:
    """K 近邻分类器。"""

    def __init__(self, k: int = 5, distance: str = 'euclidean'):
        self.k = k
        self.distance = distance
        self.X_train: np.ndarray | None = None
        self.y_train: np.ndarray | None = None

        # 距离函数映射
        self.distance_fns = {
            'euclidean': euclidean_distance,
            'manhattan': manhattan_distance,
            'cosine': lambda x1, x2: 1 - cosine_similarity(x1, x2),  # 转换为距离
        }
        self.distance_fn = self.distance_fns.get(distance, euclidean_distance)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "KNNClassifier":
        """训练（实际上是存储训练数据）。"""
        self.X_train = X
        self.y_train = y
        return self

    def predict_single(self, x: np.ndarray) -> int:
        """预测单个样本。"""
        distances, indices = find_k_nearest(self.X_train, x, self.k, self.distance_fn)

        # 获取 K 近邻的标签
        k_labels = self.y_train[indices]

        # 加权投票（距离加权）
        weights = 1 / (distances + 1e-10)  # 避免除零
        weighted_votes = {}

        for label, weight in zip(k_labels, weights):
            weighted_votes[label] = weighted_votes.get(label, 0) + weight

        # 返回权重最大的类别
        return max(weighted_votes, key=weighted_votes.get)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测多个样本。"""
        return np.array([self.predict_single(x) for x in X])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率。"""
        probs = np.zeros((len(X), len(np.unique(self.y_train))))

        for i, x in enumerate(X):
            distances, indices = find_k_nearest(self.X_train, x, self.k, self.distance_fn)
            k_labels = self.y_train[indices]

            # 统计各类权重
            weights = 1 / (distances + 1e-10)
            for label, weight in zip(k_labels, weights):
                probs[i, label] += weight

            # 归一化
            probs[i] /= probs[i].sum()

        return probs


class KNNRegressor:
    """K 近邻回归器。"""

    def __init__(self, k: int = 5):
        self.k = k
        self.X_train: np.ndarray | None = None
        self.y_train: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "KNNRegressor":
        self.X_train = X
        self.y_train = y
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测。"""
        predictions = []
        for x in X:
            distances, indices = find_k_nearest(self.X_train, x, self.k)
            k_y = self.y_train[indices]

            # 距离加权平均
            weights = 1 / (distances + 1e-10)
            pred = np.sum(k_y * weights) / np.sum(weights)
            predictions.append(pred)

        return np.array(predictions)


def compare_k_values():
    """对比不同 K 值的效果。"""
    print("=" * 60)
    print("K 值选择对比")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据：两个类别
    n_per_class = 50
    X1 = np.random.randn(n_per_class, 2) + np.array([1, 1])
    X2 = np.random.randn(n_per_class, 2) + np.array([3, 3])
    X = np.vstack([X1, X2])
    y = np.array([0] * n_per_class + [1] * n_per_class)

    # 测试不同 K
    k_values = [1, 3, 5, 7, 15, 25]
    accuracies = []

    print(f"\n{'K':<8} {'准确率':<15} {'状态':<15}")
    print("-" * 40)

    for k in k_values:
        knn = KNNClassifier(k=k)
        knn.fit(X, y)

        # 留一交叉验证
        correct = 0
        for i in range(len(X)):
            X_test = X[i:i+1]
            y_test = y[i:i+1]
            X_train = np.delete(X, i, axis=0)
            y_train = np.delete(y, i)

            knn_temp = KNNClassifier(k=k)
            knn_temp.fit(X_train, y_train)
            pred = knn_temp.predict(X_test)
            if pred[0] == y_test[0]:
                correct += 1

        acc = correct / len(X)
        accuracies.append(acc)

        status = "可能过拟合" if k == 1 else "良好" if k <= 7 else "可能欠拟合"
        print(f"{k:<8} {acc:<15.2%} {status:<15}")

    print("\n观察：")
    print("  - K=1：决策边界复杂，可能过拟合")
    print("  - K 增大：决策边界更平滑，泛化能力增强")
    print("  - K 过大：可能欠拟合")


def knn_curse_of_dimensionality():
    """演示维度灾难。"""
    print("\n" + "=" * 60)
    print("维度灾难演示")
    print("=" * 60)

    np.random.seed(42)

    # 不同维度下的最近邻分布
    dims = [2, 5, 10, 20, 50, 100]
    n_samples = 1000

    print(f"\n{'维度':<8} {'最近邻平均距离':<20} {'距离比':<15}")
    print("-" * 50)

    reference_dist = None

    for d in dims:
        # 生成数据
        X = np.random.randn(n_samples, d)

        # 计算每个点的最近邻距离
        nearest_dists = []
        for i in range(min(100, n_samples)):
            dists = np.linalg.norm(X - X[i], axis=1)
            dists[i] = np.inf  # 排除自己
            nearest_dists.append(np.min(dists))

        mean_dist = np.mean(nearest_dists)

        if reference_dist is None:
            reference_dist = mean_dist
            ratio = 1.0
        else:
            ratio = mean_dist / reference_dist

        print(f"{d:<8} {mean_dist:<20.4f} {ratio:<15.2f}")

    print("\n观察：")
    print("  - 维度越高，最近邻之间的距离越接近")
    print("  - KNN 在高维空间中效果急剧下降")
    print("  - 解决方案：降维、特征选择、适当的距离度量")


def knn_for_regression():
    """演示 KNN 回归。"""
    print("\n" + "=" * 60)
    print("KNN 回归演示")
    print("=" * 60)

    np.random.seed(42)

    # 生成回归数据
    X = np.sort(np.random.rand(100, 1) * 10, axis=0)
    y = np.sin(X).flatten() + np.random.randn(100) * 0.2

    # KNN 回归
    knn = KNNRegressor(k=5)
    knn.fit(X, y)

    # 预测
    X_test = np.linspace(0, 10, 50).reshape(-1, 1)
    y_pred = knn.predict(X_test)

    # 计算误差
    mse = np.mean((y_pred - np.sin(X_test).flatten()) ** 2)
    print(f"\nMSE: {mse:.4f}")

    # 不同 K 的效果
    print("\n不同 K 值的效果:")
    for k in [1, 3, 5, 10]:
        knn_k = KNNRegressor(k=k)
        knn_k.fit(X, y)
        y_pred_k = knn_k.predict(X_test)
        mse_k = np.mean((y_pred_k - np.sin(X_test).flatten()) ** 2)
        print(f"  K={k}: MSE={mse_k:.4f}")


def weighted_knn():
    """演示距离加权 KNN。"""
    print("\n" + "=" * 60)
    print("距离加权 KNN")
    print("=" * 60)

    np.random.seed(42)

    # 创建不平衡数据
    X = np.array([
        [1, 1], [1.2, 1.1], [1.1, 1.3],  # 类别 0 (近)
        [3, 3], [3.2, 3.1], [3.1, 3.2],  # 类别 1 (近)
        [0.5, 4.5],  # 类别 1 (远但权重低)
    ])
    y = np.array([0, 0, 0, 1, 1, 1, 1])

    # 测试点
    test_point = np.array([1.5, 2])

    print(f"\n测试点: {test_point}")

    for k in [3, 5]:
        knn = KNNClassifier(k=k)
        knn.fit(X, y)
        distances, indices = find_k_nearest(X, test_point, k)

        print(f"\nK={k}:")
        print(f"  最近邻距离: {distances}")
        print(f"  最近邻类别: {y[indices]}")
        print(f"  预测: {knn.predict_single(test_point)}")


if __name__ == "__main__":
    compare_k_values()
    knn_curse_of_dimensionality()
    knn_for_regression()
    weighted_knn()