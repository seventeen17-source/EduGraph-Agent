"""决策树完整实现：ID3/CART 算法、剪枝、可视化与特征重要性分析。

Related node: ml_decision_tree
Source IDs: book_zhou_ml, book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Callable


@dataclass
class TreeNode:
    """决策树节点。"""
    feature_index: int | None = None  # 分裂特征索引
    threshold: float | None = None     # 分裂阈值（数值特征用）
    value: float | None = None         # 叶节点预测值
    left: "TreeNode | None" = None     # 左子节点
    right: "TreeNode | None" = None    # 右子节点
    is_leaf: bool = False
    samples: int = 0                   # 该节点样本数


def entropy(y: np.ndarray) -> float:
    """计算信息熵。"""
    if len(y) == 0:
        return 0.0

    _, counts = np.unique(y, return_counts=True)
    probs = counts / len(y)

    # 避免 log(0)
    entropy_val = 0.0
    for p in probs:
        if p > 0:
            entropy_val -= p * np.log2(p)

    return entropy_val


def gini(y: np.ndarray) -> float:
    """计算基尼系数。"""
    if len(y) == 0:
        return 0.0

    _, counts = np.unique(y, return_counts=True)
    probs = counts / len(y)

    return 1.0 - np.sum(probs ** 2)


def information_gain(y: np.ndarray, y_left: np.ndarray, y_right: np.ndarray, criterion: str = "entropy") -> float:
    """
    计算信息增益。

    Args:
        y: 父节点所有样本
        y_left: 左子节点样本
        y_right: 右子节点样本
        criterion: "entropy" 或 "gini"

    Returns:
        信息增益
    """
    parent_entropy = entropy(y) if criterion == "entropy" else gini(y)
    n = len(y)

    if criterion == "entropy":
        left_entropy = entropy(y_left)
        right_entropy = entropy(y_right)
        child_entropy = (len(y_left) / n) * left_entropy + (len(y_right) / n) * right_entropy
    else:
        left_gini = gini(y_left)
        right_gini = gini(y_right)
        child_entropy = (len(y_left) / n) * left_gini + (len(y_right) / n) * right_gini

    return parent_entropy - child_entropy


def best_split(X: np.ndarray, y: np.ndarray, criterion: str = "entropy") -> tuple[int, float, float]:
    """
    找到最佳分裂特征和阈值。

    Returns:
        (best_feature, best_threshold, best_gain)
    """
    best_gain = 0.0
    best_feature = 0
    best_threshold = 0.0

    n_features = X.shape[1]
    current_impurity = entropy(y) if criterion == "entropy" else gini(y)

    for feature_idx in range(n_features):
        # 获取该特征的所有唯一值作为候选阈值
        thresholds = np.unique(X[:, feature_idx])

        if len(thresholds) <= 1:
            continue

        # 尝试所有相邻值的中点
        for i in range(len(thresholds) - 1):
            threshold = (thresholds[i] + thresholds[i + 1]) / 2

            left_mask = X[:, feature_idx] <= threshold
            right_mask = ~left_mask

            if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
                continue

            gain = information_gain(y, y[left_mask], y[right_mask], criterion)

            if gain > best_gain:
                best_gain = gain
                best_feature = feature_idx
                best_threshold = threshold

    return best_feature, best_threshold, best_gain


class DecisionTreeClassifier:
    """决策树分类器（ID3/CART 算法）。"""

    def __init__(self, max_depth: int = 10, min_samples_split: int = 2, criterion: str = "entropy"):
        """
        Args:
            max_depth: 最大深度
            min_samples_split: 分裂所需最小样本数
            criterion: "entropy" 或 "gini"
        """
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.criterion = criterion
        self.root: TreeNode | None = None

    def _most_common_label(self, y: np.ndarray) -> float:
        """返回出现最多的标签。"""
        unique, counts = np.unique(y, return_counts=True)
        return unique[np.argmax(counts)]

    def _build_tree(self, X: np.ndarray, y: np.ndarray, depth: int) -> TreeNode:
        """递归构建决策树。"""
        node = TreeNode(samples=len(y))
        node.value = self._most_common_label(y)

        # 停止条件
        if (depth >= self.max_depth or
            len(y) < self.min_samples_split or
            len(np.unique(y)) == 1):
            node.is_leaf = True
            return node

        # 找最佳分裂
        feature_idx, threshold, gain = best_split(X, y, self.criterion)

        if gain <= 0:
            node.is_leaf = True
            return node

        node.feature_index = feature_idx
        node.threshold = threshold

        # 分裂
        left_mask = X[:, feature_idx] <= threshold
        right_mask = ~left_mask

        node.left = self._build_tree(X[left_mask], y[left_mask], depth + 1)
        node.right = self._build_tree(X[right_mask], y[right_mask], depth + 1)

        return node

    def fit(self, X: np.ndarray, y: np.ndarray) -> "DecisionTreeClassifier":
        """训练决策树。"""
        self.root = self._build_tree(X, y, depth=0)
        return self

    def _predict_single(self, x: np.ndarray, node: TreeNode) -> float:
        """预测单个样本。"""
        if node.is_leaf:
            return node.value

        if x[node.feature_index] <= node.threshold:
            return self._predict_single(x, node.left)
        else:
            return self._predict_single(x, node.right)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测。"""
        return np.array([self._predict_single(x, self.root) for x in X])

    def print_tree(self, node: TreeNode = None, depth: int = 0, prefix: str = "Root: "):
        """打印决策树结构。"""
        if node is None:
            node = self.root

        indent = "  " * depth

        if node.is_leaf:
            print(f"{indent}{prefix}Leaf: class={node.value}, samples={node.samples}")
        else:
            print(f"{indent}{prefix}Feature[{node.feature_index}] <= {node.threshold:.3f}, samples={node.samples}")
            self.print_tree(node.left, depth + 1, "L: ")
            self.print_tree(node.right, depth + 1, "R: ")


def cross_val_error(X: np.ndarray, y: np.ndarray, tree: DecisionTreeClassifier, n_folds: int = 5) -> float:
    """
    使用交叉验证估计树的泛化误差。

    用于后剪枝决策。
    """
    n = len(y)
    indices = np.random.permutation(n)
    fold_size = n // n_folds

    errors = []

    for i in range(n_folds):
        val_start = i * fold_size
        val_end = (i + 1) * fold_size if i < n_folds - 1 else n

        val_idx = indices[val_start:val_end]
        train_idx = np.concatenate([indices[:val_start], indices[val_end:]])

        tree_copy = DecisionTreeClassifier(
            max_depth=tree.max_depth,
            min_samples_split=tree.min_samples_split,
            criterion=tree.criterion
        )
        tree_copy.fit(X[train_idx], y[train_idx])

        preds = tree_copy.predict(X[val_idx])
        error = np.mean(preds != y[val_idx])
        errors.append(error)

    return np.mean(errors)


def feature_importance(X: np.ndarray, y: np.ndarray, tree: DecisionTreeClassifier) -> np.ndarray:
    """
    计算特征重要性（基于信息增益）。

    Returns:
        归一化的特征重要性数组
    """
    n_features = X.shape[1]
    importance = np.zeros(n_features)

    def traverse(node: TreeNode):
        if node.is_leaf:
            return

        # 该节点分裂带来的信息增益
        feature_idx = node.feature_index
        gain = information_gain(
            y, y[X[:, feature_idx] <= node.threshold],
            y[X[:, feature_idx] > node.threshold],
            tree.criterion
        )

        # 加权到特征（乘以该节点的样本比例）
        importance[feature_idx] += gain * (node.samples / tree.root.samples)

        traverse(node.left)
        traverse(node.right)

    traverse(tree.root)

    # 归一化
    if importance.sum() > 0:
        importance = importance / importance.sum()

    return importance


def prune_tree(tree: DecisionTreeClassifier, X_val: np.ndarray, y_val: np.ndarray) -> DecisionTreeClassifier:
    """
    基于验证集的后剪枝。

    使用 Reduced Error Pruning (REP) 算法。
    """
    def prune_node(node: TreeNode) -> bool:
        """尝试剪枝节点，返回是否剪枝成功。"""
        if node.is_leaf:
            return False

        # 递归剪枝子树
        prune_node(node.left)
        prune_node(node.right)

        # 尝试将子树替换为叶节点
        if node.left.is_leaf and node.right.is_leaf:
            # 计算当前错误率
            left_mask = X_val[:, node.feature_index] <= node.threshold
            right_mask = ~left_mask
            current_errors = (
                np.sum(node.left.value != y_val[left_mask]) +
                np.sum(node.right.value != y_val[right_mask])
            )

            # 计算剪枝后错误率
            all_mask = left_mask | right_mask
            most_common = tree._most_common_label(y_val[all_mask])
            pruned_errors = np.sum(most_common != y_val[all_mask])

            # 如果剪枝后错误率不增加，则剪枝
            if pruned_errors <= current_errors:
                node.is_leaf = True
                node.value = most_common
                node.left = None
                node.right = None
                node.feature_index = None
                node.threshold = None
                return True

        return False

    prune_node(tree.root)
    return tree


if __name__ == "__main__":
    print("=" * 60)
    print("决策树实现演示")
    print("=" * 60)

    # 示例 1：鸢尾花数据集
    print("\n示例 1：鸢尾花分类")
    print("-" * 40)

    from sklearn.datasets import load_iris
    iris = load_iris()
    X = iris.data
    y = iris.target

    # 划分训练测试集
    np.random.seed(42)
    indices = np.random.permutation(len(y))
    train_idx = indices[:120]
    test_idx = indices[120:]

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # 训练决策树
    tree = DecisionTreeClassifier(max_depth=5, criterion="entropy")
    tree.fit(X_train, y_train)

    # 预测
    y_pred = tree.predict(X_test)
    accuracy = np.mean(y_pred == y_test)
    print(f"测试准确率: {accuracy:.2%}")

    # 特征重要性
    importance = feature_importance(X_train, y_train, tree)
    print("\n特征重要性:")
    for i, imp in enumerate(importance):
        print(f"  {iris.feature_names[i]}: {imp:.4f}")

    # 打印树结构（只显示前几层）
    print("\n决策树结构（前 3 层）:")
    tree.print_tree()

    # 示例 2：信息增益 vs 基尼系数
    print("\n" + "=" * 60)
    print("示例 2：Entropy vs Gini")
    print("-" * 40)

    # 生成不平衡数据
    np.random.seed(42)
    X_demo = np.random.randn(100, 2)
    # 类别分布：80% 是 0，20% 是 1
    y_demo = np.array([0] * 80 + [1] * 20)
    X_demo[:80] += np.array([2, 2])
    X_demo[80:] += np.array([4, 4])

    for criterion in ["entropy", "gini"]:
        tree_demo = DecisionTreeClassifier(max_depth=3, criterion=criterion)
        tree_demo.fit(X_demo, y_demo)
        preds = tree_demo.predict(X_demo)
        acc = np.mean(preds == y_demo)
        print(f"{criterion.capitalize()} - 训练准确率: {acc:.2%}")

    # 示例 3：剪枝效果
    print("\n" + "=" * 60)
    print("示例 3：剪枝效果")
    print("-" * 40)

    # 不同深度的决策树
    depths = [1, 3, 5, 10, 20]
    print(f"\n{'深度':<8} {'训练错误率':<15} {'测试错误率':<15}")
    print("-" * 40)

    for depth in depths:
        tree_d = DecisionTreeClassifier(max_depth=depth, criterion="entropy")
        tree_d.fit(X_train, y_train)

        train_pred = tree_d.predict(X_train)
        test_pred = tree_d.predict(X_test)

        train_err = np.mean(train_pred != y_train)
        test_err = np.mean(test_pred != y_test)

        print(f"{depth:<8} {train_err:<15.2%} {test_err:<15.2%}")
