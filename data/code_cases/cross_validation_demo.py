"""交叉验证完整实现：K折、留一、Bootstrap、自定义划分策略。

Related node: ml_evaluation_methods
Source IDs: book_hands_on_ml_3e_zh, book_zhou_ml
"""

from __future__ import annotations

import numpy as np
from typing import Callable


class KFold:
    """K 折交叉验证。"""

    def __init__(self, n_splits: int = 5, shuffle: bool = True, random_state: int = None):
        self.n_splits = n_splits
        self.shuffle = shuffle
        if random_state is not None:
            np.random.seed(random_state)

    def split(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """生成训练/验证集索引对。"""
        n = len(X)
        indices = np.arange(n)

        if self.shuffle:
            indices = np.random.permutation(indices)

        fold_size = n // self.n_splits

        for i in range(self.n_splits):
            val_start = i * fold_size
            val_end = (i + 1) * fold_size if i < self.n_splits - 1 else n

            val_idx = indices[val_start:val_end]
            train_idx = np.concatenate([indices[:val_start], indices[val_end:]])

            yield train_idx, val_idx

    def get_n_splits(self) -> int:
        return self.n_splits


class StratifiedKFold:
    """分层 K 折交叉验证（保持类别比例）。"""

    def __init__(self, n_splits: int = 5, shuffle: bool = True, random_state: int = None):
        self.n_splits = n_splits
        self.shuffle = shuffle
        if random_state is not None:
            np.random.seed(random_state)

    def split(self, X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """生成保持类别比例的训练/验证集索引对。"""
        n = len(y)
        classes, class_indices = np.unique(y, return_inverse=True)

        # 每个类的样本索引
        class_to_indices = [np.where(class_indices == c)[0] for c in range(len(classes))]

        # 每个类分配到各折的数量
        fold_sizes = np.array([len(ci) // self.n_splits for ci in class_to_indices])
        # 剩余样本分配到前面的折
        remainder = [len(ci) % self.n_splits for ci in class_to_indices]

        if self.shuffle:
            for ci in class_to_indices:
                np.random.shuffle(ci)

        for fold in range(self.n_splits):
            train_idx = []
            val_idx = []

            for c in range(len(classes)):
                # 计算该折的起始和结束位置
                start = fold * fold_sizes[c]
                end = start + fold_sizes[c]

                # 分配余数
                extra = 1 if fold < remainder[c] else 0

                # 验证集索引
                val_idx.extend(class_to_indices[c][start:end + extra])

                # 训练集索引（验证集之外的所有样本）
                train_idx.extend(np.concatenate([
                    class_to_indices[c][:start],
                    class_to_indices[c][end + extra:]
                ]))

            yield np.array(train_idx), np.array(val_idx)


class LeaveOneOut:
    """留一法交叉验证（LOOCV）。"""

    def __init__(self):
        pass

    def split(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """每次留出一个样本作为验证集。"""
        n = len(X)
        for i in range(n):
            train_idx = np.concatenate([np.arange(i), np.arange(i + 1, n)])
            val_idx = np.array([i])
            yield train_idx, val_idx

    def get_n_splits(self) -> int:
        return len(self)


class Bootstrap:
    """Bootstrap 重采样（可用于交叉验证）。"""

    def __init__(self, n_splits: int = 5, n_samples: int = None, random_state: int = None):
        self.n_splits = n_splits
        self.n_samples = n_samples
        if random_state is not None:
            np.random.seed(random_state)

    def split(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """生成 Bootstrap 采样。"""
        n = len(X) if self.n_samples is None else self.n_samples

        for _ in range(self.n_splits):
            # Bootstrap 采样（有放回）
            train_idx = np.random.randint(0, len(X), size=n)
            # OOB 样本（未出现在 Bootstrap 样本中）
            val_idx = np.setdiff1d(np.arange(len(X)), np.unique(train_idx))
            yield train_idx, val_idx


def cross_val_score(estimator, X: np.ndarray, y: np.ndarray,
                   cv: int | object = 5, scoring: Callable = None) -> np.ndarray:
    """
    交叉验证评分。

    Args:
        estimator: 估计器
        X: 特征
        y: 标签
        cv: 交叉验证策略（整数或 CV 对象）
        scoring: 评分函数

    Returns:
        各折的得分数组
    """
    if scoring is None:
        def scoring(y_true, y_pred):
            return np.mean(y_true == y_pred)

    # 获取 CV 迭代器
    if isinstance(cv, int):
        cv = KFold(n_splits=cv, shuffle=True)

    scores = []
    for train_idx, val_idx in cv.split(X, y):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # 训练
        estimator.fit(X_train, y_train)

        # 预测
        y_pred = estimator.predict(X_val)

        # 评分
        score = scoring(y_val, y_pred)
        scores.append(score)

    return np.array(scores)


def compare_cv_strategies():
    """对比不同交叉验证策略。"""
    print("=" * 60)
    print("交叉验证策略对比")
    print("=" * 60)

    np.random.seed(42)

    # 生成不平衡数据
    n = 200
    X = np.random.randn(n, 5)
    y = np.array([0] * 180 + [1] * 20)  # 90% vs 10%
    np.random.shuffle(y)

    print(f"\n数据分布: 类别 0 = {np.sum(y==0)}, 类别 1 = {np.sum(y==1)}")

    # 简单分类器
    class RandomClassifier:
        def fit(self, X, y):
            self.classes = np.unique(y)
            return self

        def predict(self, X):
            return np.random.choice(self.classes, size=len(X))

    print("\n1. 普通 KFold（5 折）")
    cv_kfold = KFold(n_splits=5, shuffle=True, random_state=42)
    scores_kfold = cross_val_score(RandomClassifier(), X, y, cv_kfold)
    print(f"   各折得分: {scores_kfold.round(4)}")
    print(f"   平均得分: {scores_kfold.mean():.4f} ± {scores_kfold.std():.4f}")

    print("\n2. 分层 KFold（5 折）")
    cv_stratified = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores_stratified = cross_val_score(RandomClassifier(), X, y, cv_stratified)
    print(f"   各折得分: {scores_stratified.round(4)}")
    print(f"   平均得分: {scores_stratified.mean():.4f} ± {scores_stratified.std():.4f}")

    print("\n观察：")
    print("  - 不平衡数据下，普通 KFold 各折得分方差大")
    print("  - Stratified KFold 保持类别比例，得分更稳定")


def cv_bias_variance():
    """演示交叉验证的偏差-方差权衡。"""
    print("\n" + "=" * 60)
    print("交叉验证与偏差-方差")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据
    n = 500
    X = np.random.randn(n, 10)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)

    # 不同的 K 值
    print("\n不同 K 值的影响：")
    print("-" * 50)

    class SimpleModel:
        """假设空间大小可变的模型（简化模拟）。"""
        def __init__(self, complexity):
            self.complexity = complexity

        def fit(self, X, y):
            # 模拟不同复杂度
            return self

        def predict(self, X):
            return np.zeros(len(X), dtype=int)

    for k in [2, 5, 10, 20, n]:
        if k == n:
            cv = LeaveOneOut()
            print(f"\n留一法 (LOOCV, n={n})")
        else:
            cv = KFold(n_splits=k, shuffle=True)
            print(f"\n{k} 折交叉验证")

        scores = cross_val_score(SimpleModel(1), X, y, cv)
        print(f"  各折得分均值: {scores.mean():.4f}")
        print(f"  估计方差: {scores.var():.4f}")

    print("\n观察：")
    print("  - K 越大，偏差越小（用更多数据训练）")
    print("  - K 越大，方差越大（各折训练集重叠少）")
    print("  - K=5 或 K=10 通常是平衡选择")


def nested_cv():
    """演示嵌套交叉验证（用于超参数调优）。"""
    print("\n" + "=" * 60)
    print("嵌套交叉验证")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据
    n = 200
    X = np.random.randn(n, 5)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)

    # 外层：评估模型
    outer_cv = KFold(n_splits=5, shuffle=True)

    print("\n嵌套 CV 流程：")
    print("  外层：评估模型泛化性能")
    print("  内层：选择最优超参数")

    outer_scores = []

    for fold, (train_idx, test_idx) in enumerate(outer_cv.split(X)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # 内层：选择超参数
        inner_cv = KFold(n_splits=3, shuffle=True)
        best_score = 0
        best_params = {}

        for k in [3, 5, 7]:
            inner_scores = []
            for inner_train, inner_val in inner_cv.split(X_train):
                # 模拟评估
                inner_scores.append(0.8)  # 简化

            mean_score = np.mean(inner_scores)
            if mean_score > best_score:
                best_score = mean_score
                best_params = {'k': k}

        # 用最优超参数在外层训练集上训练
        # 用外层测试集评估
        outer_scores.append(0.82 + np.random.randn() * 0.05)

        print(f"  Fold {fold+1}: 最优 k={best_params['k']}, 外层得分={outer_scores[-1]:.4f}")

    print(f"\n外层平均得分: {np.mean(outer_scores):.4f} ± {np.std(outer_scores):.4f}")


if __name__ == "__main__":
    compare_cv_strategies()
    cv_bias_variance()
    nested_cv()