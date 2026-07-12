"""特征工程完整实现：标准化、编码、特征选择、特征组合。

Related node: ml_feature_selection
Source IDs: book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np
from typing import Callable


def min_max_scale(X: np.ndarray, feature_range: tuple = (0, 1)) -> tuple[np.ndarray, dict]:
    """
    最小-最大缩放：归一化到 [min, max] 范围。

    X_norm = (X - X_min) / (X_max - X_min) * (max - min) + min
    """
    min_val, max_val = feature_range
    X_min = X.min(axis=0)
    X_max = X.max(axis=0)

    # 防止除零
    X_range = X_max - X_min
    X_range[X_range == 0] = 1

    X_scaled = (X - X_min) / X_range * (max_val - min_val) + min_val

    params = {'min': X_min, 'max': X_max, 'feature_range': feature_range}
    return X_scaled, params


def standardize(X: np.ndarray) -> tuple[np.ndarray, dict]:
    """
    标准化（Z-score）：均值为 0，标准差为 1。

    X_norm = (X - μ) / σ
    """
    mean = X.mean(axis=0)
    std = X.std(axis=0)

    # 防止除零
    std[std == 0] = 1

    X_scaled = (X - mean) / std

    params = {'mean': mean, 'std': std}
    return X_scaled, params


def robust_scale(X: np.ndarray) -> tuple[np.ndarray, dict]:
    """
    鲁棒缩放：使用中位数和四分位距，对异常值鲁棒。

    X_norm = (X - median) / IQR
    """
    median = np.median(X, axis=0)
    q75 = np.percentile(X, 75, axis=0)
    q25 = np.percentile(X, 25, axis=0)

    iqr = q75 - q25
    iqr[iqr == 0] = 1

    X_scaled = (X - median) / iqr

    params = {'median': median, 'iqr': iqr}
    return X_scaled, params


def one_hot_encode(y: np.ndarray) -> tuple[np.ndarray, list]:
    """
    独热编码：类别转二进制向量。
    """
    classes = np.unique(y)
    n_classes = len(classes)
    n_samples = len(y)

    encoded = np.zeros((n_samples, n_classes), dtype=int)
    for i, c in enumerate(classes):
        encoded[y == c, i] = 1

    return encoded, classes.tolist()


def label_encode(y: np.ndarray) -> tuple[np.ndarray, list]:
    """
    标签编码：类别转整数。
    """
    classes = np.unique(y)
    encoded = np.zeros(len(y), dtype=int)

    for i, c in enumerate(classes):
        encoded[y == c] = i

    return encoded, classes.tolist()


def polynomial_features(X: np.ndarray, degree: int = 2) -> np.ndarray:
    """
    生成多项式特征。
    """
    n_samples, n_features = X.shape
    features = [X]  # 原始特征

    for d in range(2, degree + 1):
        # 计算所有 d 次多项式组合
        from itertools import combinations_with_replacement
        for combo in combinations_with_replacement(range(n_features), d):
            features.append(np.prod(X[:, combo], axis=1).reshape(-1, 1))

    return np.hstack(features)


def feature_interactions(X: np.ndarray, feature_names: list[str] = None) -> tuple[np.ndarray, list[str]]:
    """
    生成特征交互项。
    """
    n_features = X.shape[1]
    interactions = []

    for i in range(n_features):
        for j in range(i + 1, n_features):
            interactions.append(X[:, i] * X[:, j])

    if feature_names:
        interaction_names = []
        for i in range(n_features):
            for j in range(i + 1, n_features):
                interaction_names.append(f"{feature_names[i]}*{feature_names[j]}")
        return np.column_stack(interactions), feature_names + interaction_names

    return np.column_stack(interactions)


def mutual_information(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    计算互信息：衡量特征和目标之间的依赖关系。
    """
    n_features = X.shape[1]
    mi_scores = np.zeros(n_features)

    for i in range(n_features):
        # 离散化连续特征
        feature_bins = np.histogram_bin_edges(X[:, i], bins='auto')
        feature_binned = np.digitize(X[:, i], feature_bins) - 1

        # 计算互信息的简化版本
        # I(X; Y) = H(Y) - H(Y|X)
        n_bins = len(np.unique(feature_binned))

        # H(Y)
        classes, class_counts = np.unique(y, return_counts=True)
        p_y = class_counts / len(y)
        H_y = -np.sum(p_y * np.log(p_y + 1e-10))

        # H(Y|X)
        H_y_given_x = 0
        for b in range(n_bins):
            mask = feature_binned == b
            if np.sum(mask) > 0:
                y_in_bin = y[mask]
                classes_b, counts_b = np.unique(y_in_bin, return_counts=True)
                p_y_given_x = counts_b / len(y_in_bin)
                H_y_given_x += (len(y_in_bin) / len(y)) * (-np.sum(p_y_given_x * np.log(p_y_given_x + 1e-10)))

        mi_scores[i] = H_y - H_y_given_x

    return mi_scores


def chi2_selection(X: np.ndarray, y: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """
    卡方检验特征选择：选择与目标最相关的特征。
    """
    n_features = X.shape[1]

    # 离散化
    X_binned = np.zeros_like(X)
    for i in range(n_features):
        bins = np.percentile(X[:, i], [0, 25, 50, 75, 100])
        X_binned[:, i] = np.digitize(X[:, i], bins)

    # 计算卡方统计量
    chi2_scores = np.zeros(n_features)

    for i in range(n_features):
        observed = np.zeros((len(np.unique(X_binned[:, i])), len(np.unique(y))))
        for j, xi in enumerate(np.unique(X_binned[:, i])):
            for k, yi in enumerate(np.unique(y)):
                observed[j, k] = np.sum((X_binned[:, i] == xi) & (y == yi))

        # 期望频率
        row_sums = observed.sum(axis=1, keepdims=True)
        col_sums = observed.sum(axis=0, keepdims=True)
        expected = row_sums * col_sums / observed.sum()

        chi2 = np.sum((observed - expected) ** 2 / (expected + 1e-10))
        chi2_scores[i] = chi2

    # 选择 top-k
    top_k_indices = np.argsort(chi2_scores)[-k:]
    return top_k_indices, chi2_scores


def demonstrate_feature_scaling():
    """演示不同特征缩放方法。"""
    print("=" * 60)
    print("特征缩放方法对比")
    print("=" * 60)

    np.random.seed(42)

    # 原始数据：不同尺度的特征
    X = np.array([
        [1000, 0.001, 50],
        [2000, 0.002, 30],
        [1500, 0.0015, 40],
    ])

    print("\n原始数据:")
    print(X)

    # 最小-最大缩放
    X_minmax, _ = min_max_scale(X)
    print("\n最小-最大缩放 [0, 1]:")
    print(X_minmax.round(4))

    # 标准化
    X_std, _ = standardize(X)
    print("\n标准化 (Z-score):")
    print(X_std.round(4))

    # 鲁棒缩放
    X_robust, _ = robust_scale(X)
    print("\n鲁棒缩放:")
    print(X_robust.round(4))


def demonstrate_encoding():
    """演示类别编码。"""
    print("\n" + "=" * 60)
    print("类别特征编码")
    print("=" * 60)

    # 标签编码
    y = np.array(['cat', 'dog', 'bird', 'cat', 'bird'])
    y_encoded, classes = label_encode(y)
    print("\n标签编码:")
    print(f"原始: {y}")
    print(f"编码: {y_encoded}")
    print(f"类别: {classes}")

    # 独热编码
    y_onehot, classes = one_hot_encode(y)
    print("\n独热编码:")
    print(f"原始: {y}")
    print(f"编码:\n{y_onehot}")


def demonstrate_polynomial_features():
    """演示多项式特征。"""
    print("\n" + "=" * 60)
    print("多项式特征生成")
    print("=" * 60)

    X = np.array([[1, 2], [2, 3], [3, 4]])
    print(f"\n原始特征 (3 样本, 2 特征):\n{X}")

    X_poly = polynomial_features(X, degree=2)
    print(f"\n2 次多项式特征:\n{X_poly}")

    X_poly3 = polynomial_features(X, degree=3)
    print(f"\n3 次多项式特征形状: {X_poly3.shape}")


def demonstrate_feature_selection():
    """演示特征选择方法。"""
    print("\n" + "=" * 60)
    print("特征选择")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据：只有前 3 个特征与目标相关
    n = 100
    X = np.random.randn(n, 10)
    # 前 3 个特征与 y 相关
    y = (X[:, 0] + 0.5 * X[:, 1] - 0.3 * X[:, 2] > 0).astype(int)
    # 后 7 个是噪声

    print("\n互信息得分:")
    mi_scores = mutual_information(X, y)
    for i, score in enumerate(mi_scores):
        marker = "***" if i < 3 else ""
        print(f"  特征 {i+1}: {'█' * int(score * 10):20} {score:.4f} {marker}")

    print("\n观察：")
    print("  - 与目标相关的特征互信息得分更高")
    print("  - 噪声特征互信息得分接近 0")


if __name__ == "__main__":
    demonstrate_feature_scaling()
    demonstrate_encoding()
    demonstrate_polynomial_features()
    demonstrate_feature_selection()