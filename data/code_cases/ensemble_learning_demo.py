"""集成学习完整实现：Bagging、Boosting、Stacking、Voting。

Related node: ml_ensemble_learning
Source IDs: book_hands_on_ml_3e_zh, book_zhou_ml
"""

from __future__ import annotations

import numpy as np
from typing import Callable


def bootstrap_sample(X: np.ndarray, y: np.ndarray = None) -> tuple:
    """Bootstrap 采样。"""
    n = len(X)
    indices = np.random.randint(0, n, size=n)
    if y is not None:
        return X[indices], y[indices]
    return X[indices]


def majority_vote(predictions: np.ndarray) -> np.ndarray:
    """多数投票。"""
    n_samples = predictions.shape[1]
    result = []
    for i in range(n_samples):
        votes = predictions[:, i]
        result.append(np.argmax(np.bincount(votes.astype(int))))
    return np.array(result)


def weighted_majority_vote(predictions: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """加权多数投票。"""
    n_samples = predictions.shape[1]
    result = []
    for i in range(n_samples):
        votes = predictions[:, i]
        weighted_scores = np.zeros(len(np.unique(votes)))
        for vote, weight in zip(votes, weights):
            weighted_scores[int(vote)] += weight
        result.append(np.argmax(weighted_scores))
    return np.array(result)


class BaggingClassifier:
    """
    Bagging（元学习器引导）。

    原理：
    1. 通过 Bootstrap 采样生成多个训练子集
    2. 在每个子集上训练基学习器
    3. 集成预测（投票）
    """

    def __init__(self, base_estimator, n_estimators: int = 10):
        self.base_estimator = base_estimator
        self.n_estimators = n_estimators
        self.estimators = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaggingClassifier":
        """训练 Bagging 集成。"""
        self.estimators = []

        for i in range(self.n_estimators):
            X_boot, y_boot = bootstrap_sample(X, y)

            # 克隆基学习器
            estimator = self.base_estimator()
            estimator.fit(X_boot, y_boot)
            self.estimators.append(estimator)

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测。"""
        predictions = np.array([est.predict(X) for est in self.estimators])
        return majority_vote(predictions)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率。"""
        probas = np.array([est.predict_proba(X) for est in self.estimators])
        return probas.mean(axis=0)


class AdaBoost:
    """
    AdaBoost（自适应提升）。

    原理：
    1. 初始化样本权重 w_i = 1/n
    2. 训练基学习器，计算误差 ε
    3. 更新权重：错误样本权重增加，正确样本权重减少
    4. 权重 α = 0.5 * log((1-ε)/ε)
    5. 重复直到达到 T 个学习器
    """

    def __init__(self, n_estimators: int = 50):
        self.n_estimators = n_estimators
        self.estimators = []
        self.estimator_weights = []
        self.estimator_errors = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "AdaBoost":
        """训练 AdaBoost。"""
        n_samples = len(X)
        weights = np.ones(n_samples) / n_samples

        self.estimators = []
        self.estimator_weights = []

        for t in range(self.n_estimators):
            # 训练弱分类器（这里用决策树桩）
            estimator = DecisionStump()
            estimator.fit(X, y, sample_weight=weights)

            # 预测
            predictions = estimator.predict(X)

            # 计算误差
            incorrect = predictions != y
            epsilon = np.sum(weights * incorrect)

            if epsilon > 0.5:
                # 误差太大，反转预测
                epsilon = 1 - epsilon
                predictions = ~predictions

            if epsilon == 0:
                epsilon = 1e-10
            if epsilon >= 0.5:
                break

            # 计算权重
            alpha = 0.5 * np.log((1 - epsilon) / epsilon)

            # 更新样本权重
            weights = weights * np.exp(-alpha * y * predictions)

            # 归一化
            weights = weights / weights.sum()

            self.estimators.append((estimator, alpha if epsilon < 0.5 else -alpha))
            self.estimator_weights.append(abs(alpha))

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测。"""
        n_samples = len(X)
        predictions = np.zeros(n_samples)

        for estimator, alpha in self.estimators:
            predictions += alpha * estimator.predict(X)

        return np.sign(predictions).astype(int)


class DecisionStump:
    """决策树桩（单层决策树）。"""

    def __init__(self):
        self.feature = None
        self.threshold = None
        self.direction = 1

    def fit(self, X: np.ndarray, y: np.ndarray, sample_weight: np.ndarray = None):
        """训练决策树桩。"""
        n_samples, n_features = X.shape

        if sample_weight is None:
            sample_weight = np.ones(n_samples) / n_samples

        best_error = float('inf')

        for feature in range(n_features):
            thresholds = np.percentile(X[:, feature], [25, 50, 75])

            for threshold in thresholds:
                for direction in [1, -1]:
                    if direction == 1:
                        predictions = (X[:, feature] <= threshold).astype(int) * 2 - 1
                    else:
                        predictions = (X[:, feature] > threshold).astype(int) * 2 - 1

                    error = np.sum(sample_weight * (predictions != y))

                    if error < best_error:
                        best_error = error
                        self.feature = feature
                        self.threshold = threshold
                        self.direction = direction

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测。"""
        if self.direction == 1:
            return (X[:, self.feature] <= self.threshold).astype(int) * 2 - 1
        else:
            return (X[:, self.feature] > self.threshold).astype(int) * 2 - 1


class StackingClassifier:
    """
    Stacking（堆叠）。

    原理：
    1. 用原始数据训练多个基学习器
    2. 用基学习器的预测作为元学习器的特征
    3. 在元特征上训练元学习器
    """

    def __init__(self, base_estimators: list, meta_estimator, n_folds: int = 5):
        self.base_estimators = base_estimators
        self.meta_estimator = meta_estimator
        self.n_folds = n_folds

    def fit(self, X: np.ndarray, y: np.ndarray) -> "StackingClassifier":
        """训练 Stacking 集成。"""
        n_samples = len(X)
        n_estimators = len(self.base_estimators)

        # 生成元特征（使用交叉验证避免过拟合）
        meta_features = np.zeros((n_samples, n_estimators))

        for i, estimator in enumerate(self.base_estimators):
            estimator.fit(X, y)

            # 使用交叉验证生成元特征
            for train_idx, val_idx in KFold(n_splits=self.n_folds).split(X):
                estimator_cv = self._clone_estimator(estimator)
                estimator_cv.fit(X[train_idx], y[train_idx])
                meta_features[val_idx, i] = estimator_cv.predict(X[val_idx])

        # 训练元学习器
        self.meta_estimator.fit(meta_features, y)

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测。"""
        meta_features = np.column_stack([est.predict(X) for est in self.base_estimators])
        return self.meta_estimator.predict(meta_features)

    def _clone_estimator(self, estimator):
        """克隆估计器（简化版本）。"""
        return type(estimator)()


class KFold:
    """简单的 K 折交叉验证。"""

    def __init__(self, n_splits: int = 5, shuffle: bool = True):
        self.n_splits = n_splits
        self.shuffle = shuffle

    def split(self, X: np.ndarray):
        """生成训练/验证集索引。"""
        n = len(X)
        indices = np.arange(n)

        if self.shuffle:
            np.random.shuffle(indices)

        fold_size = n // self.n_splits

        for i in range(self.n_splits):
            val_idx = indices[i * fold_size:(i + 1) * fold_size]
            train_idx = np.concatenate([indices[:i * fold_size], indices[(i + 1) * fold_size:]])
            yield train_idx, val_idx


def compare_ensemble_methods():
    """对比不同集成方法。"""
    print("=" * 60)
    print("集成学习方法对比")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据
    n = 500
    X = np.random.randn(n, 5)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)

    # 添加噪声
    y = (y + np.random.randint(0, 2, n)) % 2

    # 划分
    indices = np.random.permutation(n)
    train_idx = indices[:400]
    test_idx = indices[400:]
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    print(f"\n数据：{X_train.shape[0]} 训练样本，{X_test.shape[0]} 测试样本")

    # 1. 单个决策树
    print("\n1. 单个决策树")
    tree = SimpleDecisionTreeWrapper(max_depth=10)
    tree.fit(X_train, y_train)
    acc = np.mean(tree.predict(X_test) == y_test)
    print(f"   测试准确率: {acc:.2%}")

    # 2. Bagging
    print("\n2. Bagging (10 个决策树)")
    bagging = BaggingClassifier(lambda: SimpleDecisionTreeWrapper(max_depth=10), n_estimators=10)
    bagging.fit(X_train, y_train)
    acc = np.mean(bagging.predict(X_test) == y_test)
    print(f"   测试准确率: {acc:.2%}")

    # 3. AdaBoost
    print("\n3. AdaBoost (50 个决策树桩)")
    adaboost = AdaBoost(n_estimators=50)
    adaboost.fit(X_train, y_train)
    acc = np.mean(adaboost.predict(X_test) == y_test)
    print(f"   测试准确率: {acc:.2%}")


class SimpleDecisionTreeWrapper:
    """简化的决策树包装器。"""

    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.tree = self._build_tree(X, y, depth=0)
        return self

    def _build_tree(self, X: np.ndarray, y: np.ndarray, depth: int) -> dict:
        if depth >= self.max_depth or len(np.unique(y)) == 1:
            return {'value': np.argmax(np.bincount(y))}

        best_feature, best_threshold = self._find_best_split(X, y)
        if best_feature is None:
            return {'value': np.argmax(np.bincount(y))}

        left_mask = X[:, best_feature] <= best_threshold
        return {
            'feature': best_feature,
            'threshold': best_threshold,
            'left': self._build_tree(X[left_mask], y[left_mask], depth + 1),
            'right': self._build_tree(X[~left_mask], y[~left_mask], depth + 1),
        }

    def _find_best_split(self, X: np.ndarray, y: np.ndarray):
        from collections import Counter
        n_samples, n_features = X.shape
        best_gain = 0
        best_feature, best_threshold = None, None

        for f in range(n_features):
            thresholds = np.unique(X[:, f])
            for t in thresholds:
                left_mask = X[:, f] <= t
                if np.sum(left_mask) == 0 or np.sum(left_mask) == n_samples:
                    continue

                left_y = y[left_mask]
                right_y = y[~left_mask]

                left_entropy = Counter(left_y)
                right_entropy = Counter(right_y)

                gain = (len(left_y) * len(right_y) / n_samples**2)
                if gain > best_gain:
                    best_gain = gain
                    best_feature = f
                    best_threshold = t

        return best_feature, best_threshold

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([self._predict_single(x, self.tree) for x in X])

    def _predict_single(self, x: np.ndarray, node: dict) -> int:
        if 'value' in node:
            return node['value']
        if x[node['feature']] <= node['threshold']:
            return self._predict_single(x, node['left'])
        return self._predict_single(x, node['right'])


if __name__ == "__main__":
    compare_ensemble_methods()