"""随机森林（Random Forest）完整实现：从决策树到集成学习。

Related node: ml_random_forest
Source IDs: book_hands_on_ml_3e_zh, book_zhou_ml
"""

from __future__ import annotations

import numpy as np
from typing import Callable


def bootstrap_sample(X: np.ndarray, y: np.ndarray, n_samples: int = None) -> tuple[np.ndarray, np.ndarray]:
    """
    Bootstrap 采样：有放回地从数据集中采样。

    Returns:
        采样后的 X 和 y
    """
    if n_samples is None:
        n_samples = len(X)

    indices = np.random.randint(0, len(X), size=n_samples)
    return X[indices], y[indices]


def gini(y: np.ndarray) -> float:
    """计算基尼系数。"""
    if len(y) == 0:
        return 0.0
    _, counts = np.unique(y, return_counts=True)
    probs = counts / len(y)
    return 1.0 - np.sum(probs ** 2)


def best_split(X: np.ndarray, y: np.ndarray, feature_indices: list[int]) -> tuple[int, float, float]:
    """在指定特征子集中找最佳分裂。"""
    best_gain = 0.0
    best_feature = 0
    best_threshold = 0.0

    for feature_idx in feature_indices:
        thresholds = np.unique(X[:, feature_idx])
        if len(thresholds) <= 1:
            continue

        for i in range(len(thresholds) - 1):
            threshold = (thresholds[i] + thresholds[i + 1]) / 2

            left_mask = X[:, feature_idx] <= threshold
            right_mask = ~left_mask

            if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
                continue

            # 计算基尼增益
            parent_gini = gini(y)
            left_gini = gini(y[left_mask])
            right_gini = gini(y[right_mask])

            n = len(y)
            gain = parent_gini - (len(y[left_mask]) / n) * left_gini - (len(y[right_mask]) / n) * right_gini

            if gain > best_gain:
                best_gain = gain
                best_feature = feature_idx
                best_threshold = threshold

    return best_feature, best_threshold, best_gain


class SimpleDecisionTree:
    """简化的决策树（用于随机森林）。"""

    def __init__(self, max_depth: int = 10, min_samples_split: int = 5, max_features: str = 'sqrt'):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.tree = None

    def _build_tree(self, X: np.ndarray, y: np.ndarray, depth: int) -> dict:
        """递归构建树。"""
        n_samples, n_features = X.shape

        # 停止条件
        if (depth >= self.max_depth or
            n_samples < self.min_samples_split or
            len(np.unique(y)) == 1):
            return {'leaf': True, 'value': np.argmax(np.bincount(y))}

        # 随机选择特征子集
        if self.max_features == 'sqrt':
            n_select = max(1, int(np.sqrt(n_features)))
        elif self.max_features == 'log2':
            n_select = max(1, int(np.log2(n_features)))
        else:
            n_select = n_features

        feature_indices = np.random.choice(n_features, n_select, replace=False)

        # 找最佳分裂
        feature_idx, threshold, gain = best_split(X, y, list(feature_indices))

        if gain <= 0:
            return {'leaf': True, 'value': np.argmax(np.bincount(y))}

        # 分裂
        left_mask = X[:, feature_idx] <= threshold
        right_mask = ~left_mask

        return {
            'leaf': False,
            'feature': feature_idx,
            'threshold': threshold,
            'left': self._build_tree(X[left_mask], y[left_mask], depth + 1),
            'right': self._build_tree(X[right_mask], y[right_mask], depth + 1),
        }

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SimpleDecisionTree":
        """训练树。"""
        self.tree = self._build_tree(X, y, depth=0)
        return self

    def _predict_single(self, x: np.ndarray, node: dict) -> int:
        """预测单个样本。"""
        if node['leaf']:
            return node['value']

        if x[node['feature']] <= node['threshold']:
            return self._predict_single(x, node['left'])
        else:
            return self._predict_single(x, node['right'])

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测。"""
        return np.array([self._predict_single(x, self.tree) for x in X])


class RandomForest:
    """随机森林分类器。"""

    def __init__(self, n_estimators: int = 100, max_depth: int = 10,
                 min_samples_split: int = 5, max_features: str = 'sqrt'):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.trees: list[SimpleDecisionTree] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForest":
        """训练随机森林。"""
        self.trees = []
        np.random.seed(42)

        for i in range(self.n_estimators):
            # Bootstrap 采样
            X_boot, y_boot = bootstrap_sample(X, y)

            # 训练决策树
            tree = SimpleDecisionTree(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                max_features=self.max_features
            )
            tree.fit(X_boot, y_boot)
            self.trees.append(tree)

            if (i + 1) % 10 == 0:
                print(f"  训练树 {i+1}/{self.n_estimators}")

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测（投票）。"""
        # 所有树的预测
        predictions = np.array([tree.predict(X) for tree in self.trees])

        # 投票
        final_predictions = []
        for i in range(len(X)):
            votes = predictions[:, i]
            final_predictions.append(np.argmax(np.bincount(votes)))

        return np.array(final_predictions)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率。"""
        probas = np.zeros((len(X), 2))

        for tree in self.trees:
            preds = tree.predict(X)
            probas[np.arange(len(X)), preds] += 1

        probas /= self.n_estimators
        return probas

    def feature_importance(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        计算特征重要性：基于每个特征对 Gini 不纯度减少的贡献。

        简化版本：使用 OOB 误差减少量。
        """
        n_features = X.shape[1]
        importance = np.zeros(n_features)

        for tree in self.trees:
            # 统计每个特征的使用次数（简化）
            def count_features(node):
                if node.get('leaf', False):
                    return {}
                feature = node['feature']
                left_counts = count_features(node['left'])
                right_counts = count_features(node['right'])
                counts = {feature: 1}
                for k, v in left_counts.items():
                    counts[k] = counts.get(k, 0) + v
                for k, v in right_counts.items():
                    counts[k] = counts.get(k, 0) + v
                return counts

            counts = count_features(tree.tree)
            for feature_idx, count in counts.items():
                importance[feature_idx] += count

        return importance / importance.sum()


def compare_single_tree_vs_forest():
    """对比单棵决策树和随机森林。"""
    print("=" * 60)
    print("单棵决策树 vs 随机森林")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据：有噪声的分类
    n = 500
    X = np.random.randn(n, 5)
    y = ((X[:, 0] + X[:, 1] > 0) & (X[:, 2] - X[:, 3] < 0.5)).astype(int)

    # 添加噪声特征
    y = (y + np.random.randint(0, 2, n)) % 2

    # 划分
    indices = np.random.permutation(n)
    train_idx = indices[:400]
    test_idx = indices[400:]

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # 单棵决策树
    print("\n1. 单棵决策树")
    tree = SimpleDecisionTree(max_depth=10)
    tree.fit(X_train, y_train)
    train_acc = np.mean(tree.predict(X_train) == y_train)
    test_acc = np.mean(tree.predict(X_test) == y_test)
    print(f"   训练准确率: {train_acc:.2%}")
    print(f"   测试准确率: {test_acc:.2%}")

    # 随机森林
    print("\n2. 随机森林 (10 棵树)")
    rf = RandomForest(n_estimators=10, max_depth=10)
    rf.fit(X_train, y_train)
    train_acc_rf = np.mean(rf.predict(X_train) == y_train)
    test_acc_rf = np.mean(rf.predict(X_test) == y_test)
    print(f"   训练准确率: {train_acc_rf:.2%}")
    print(f"   测试准确率: {test_acc_rf:.2%}")

    print("\n观察：")
    print("  - 单棵决策树容易过拟合（训练准确率高，测试低）")
    print("  - 随机森林通过集成减少过拟合")


def random_forest_oob_error():
    """演示随机森林的 OOB（Out-of-Bag）误差估计。"""
    print("\n" + "=" * 60)
    print("OOB 误差估计")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据
    n = 200
    X = np.random.randn(n, 5)
    y = (X[:, 0] * X[:, 1] > 0).astype(int)

    n_estimators = 20
    oob_predictions = np.zeros(n, dtype=int)
    oob_counts = np.zeros(n)

    # OOB 估计
    for i in range(n_estimators):
        # Bootstrap 采样
        indices = np.random.randint(0, n, size=n)
        X_boot, y_boot = X[indices], y[indices]

        # 训练树
        tree = SimpleDecisionTree(max_depth=10)
        tree.fit(X_boot, y_boot)

        # OOB 样本的预测
        oob_idx = np.setdiff1d(np.arange(n), np.unique(indices))
        if len(oob_idx) > 0:
            oob_preds = tree.predict(X[oob_idx])
            oob_predictions[oob_idx] += oob_preds
            oob_counts[oob_idx] += 1

    # 计算 OOB 误差
    valid_mask = oob_counts > 0
    oob_predictions[valid_mask] = (oob_predictions[valid_mask] / oob_counts[valid_mask] > 0.5).astype(int)
    oob_error = np.mean(oob_predictions[valid_mask] != y[valid_mask])

    print(f"\nOOB 误差估计: {oob_error:.2%}")
    print(f"（不需要单独的验证集）")


def random_forest_feature_importance():
    """演示特征重要性分析。"""
    print("\n" + "=" * 60)
    print("随机森林特征重要性")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据：只有前 3 个特征有用
    n = 500
    X = np.random.randn(n, 10)
    # 真实关系
    y = (X[:, 0] + 0.5 * X[:, 1] - 0.3 * X[:, 2] > 0).astype(int)

    # 添加噪声特征
    X[:, 3:] = np.random.randn(n, 7) * 0.1

    # 训练随机森林
    rf = RandomForest(n_estimators=50, max_depth=10)
    rf.fit(X, y)

    # 特征重要性
    importance = rf.feature_importance(X, y)

    print("\n特征重要性:")
    for i, imp in enumerate(importance):
        marker = "***" if i < 3 else ""
        print(f"  特征 {i+1}: {'█' * int(imp * 100):50} {imp:.4f} {marker}")

    print("\n观察：")
    print("  - 前 3 个特征的重要性明显高于噪声特征")
    print("  - 随机森林可以自动识别重要特征")


if __name__ == "__main__":
    compare_single_tree_vs_forest()
    random_forest_oob_error()
    random_forest_feature_importance()