"""朴素贝叶斯分类器完整实现：GaussianNB、MultinomialNB、BernoulliNB。

Related node: ml_bayesian_classifier
Source IDs: book_zhou_ml, book_prml_bishop
"""

from __future__ import annotations

import numpy as np
from typing import Callable


def gaussian_pdf(x: float, mean: float, var: float) -> float:
    """
    高斯概率密度函数。

    P(x|c) = 1 / sqrt(2πσ²) * exp(-(x-μ)² / 2σ²)
    """
    return np.exp(-0.5 * (x - mean) ** 2 / var) / np.sqrt(2 * np.pi * var)


class GaussianNB:
    """
    高斯朴素贝叶斯：假设特征服从高斯分布。

    适用于连续特征。
    """

    def __init__(self):
        self.classes: np.ndarray | None = None
        self.class_prior_: np.ndarray | None = None
        self.theta_: np.ndarray | None = None  # 每个类每个特征的均值
        self.var_: np.ndarray | None = None   # 每个类每个特征的方差
        self.epsilon_: float = 1e-9  # 防止方差为 0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "GaussianNB":
        """训练模型。"""
        n_samples, n_features = X.shape

        # 获取所有类别
        self.classes = np.unique(y)
        n_classes = len(self.classes)

        # 先验概率 P(y)
        self.class_prior_ = np.array([np.sum(y == c) for c in self.classes]) / n_samples

        # 计算每个类每个特征的均值和方差
        self.theta_ = np.zeros((n_classes, n_features))
        self.var_ = np.zeros((n_classes, n_features))

        for i, c in enumerate(self.classes):
            X_c = X[y == c]
            self.theta_[i] = X_c.mean(axis=0)
            self.var_[i] = X_c.var(axis=0) + self.epsilon_

        return self

    def _compute_log_likelihood(self, X: np.ndarray) -> np.ndarray:
        """计算对数似然 log P(x|y)。"""
        n_samples = X.shape[0]
        n_classes = len(self.classes)
        log_likelihood = np.zeros((n_samples, n_classes))

        for i in range(n_classes):
            for j in range(X.shape[1]):
                # log P(x_j|y,c) = -0.5 * log(2πvar) - (x-μ)²/2var
                log_likelihood[:, i] += (
                    -0.5 * np.log(2 * np.pi * self.var_[i, j])
                    - 0.5 * (X[:, j] - self.theta_[i, j]) ** 2 / self.var_[i, j]
                )

        return log_likelihood

    def predict_log_proba(self, X: np.ndarray) -> np.ndarray:
        """预测对数概率。"""
        log_likelihood = self._compute_log_likelihood(log_likelihood)
        log_prior = np.log(self.class_prior_)
        log_posterior = log_likelihood + log_prior
        return log_posterior - np.log(np.sum(np.exp(log_posterior)))

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测类别。"""
        log_likelihood = self._compute_log_likelihood(X)
        log_prior = np.log(self.class_prior_)
        log_posterior = log_likelihood + log_prior
        return self.classes[np.argmax(log_posterior, axis=1)]


class MultinomialNB:
    """
    多项式朴素贝叶斯：适用于离散特征（词频）。

    假设特征是计数数据，服从多项式分布。
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha  # 拉普拉斯平滑参数
        self.classes: np.ndarray | None = None
        self.class_log_prior_: np.ndarray | None = None
        self.feature_log_prob_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MultinomialNB":
        """训练模型。"""
        n_samples, n_features = X.shape
        self.classes = np.unique(y)
        n_classes = len(self.classes)

        # 计算类别计数
        class_counts = np.array([np.sum(y == c) for c in self.classes])

        # 先验概率（对数）
        self.class_log_prior_ = np.log(class_counts / n_samples)

        # 计算每个类每个特征的条件概率（对数）
        self.feature_log_prob_ = np.zeros((n_classes, n_features))

        for i, c in enumerate(self.classes):
            X_c = X[y == c]
            # 加拉普拉斯平滑
            counts = X_c.sum(axis=0) + self.alpha
            total = counts.sum() + self.alpha * n_features
            self.feature_log_prob_[i] = np.log(counts / total)

        return self

    def predict_log_proba(self, X: np.ndarray) -> np.ndarray:
        """预测对数概率。"""
        return X @ self.feature_log_prob_.T + self.class_log_prior_

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测类别。"""
        log_proba = self.predict_log_proba(X)
        return self.classes[np.argmax(log_proba, axis=1)]


class BernoulliNB:
    """
    伯努利朴素贝叶斯：适用于二元特征。

    假设特征是二元的（0 或 1）。
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.classes: np.ndarray | None = None
        self.class_log_prior_: np.ndarray | None = None
        self.feature_log_prob_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BernoulliNB":
        """训练模型。"""
        n_samples, n_features = X.shape
        self.classes = np.unique(y)
        n_classes = len(self.classes)

        # 先验
        class_counts = np.array([np.sum(y == c) for c in self.classes])
        self.class_log_prior_ = np.log(class_counts / n_samples)

        # 特征为 1 时的条件概率
        self.feature_log_prob_ = np.zeros((n_classes, n_features))

        for i, c in enumerate(self.classes):
            X_c = X[y == c]
            # P(x=1|y=c) + 平滑
            p = (X_c.sum(axis=0) + self.alpha) / (len(X_c) + 2 * self.alpha)
            self.feature_log_prob_[i] = np.log(p)

        return self

    def predict_log_proba(self, X: np.ndarray) -> np.ndarray:
        """预测对数概率。"""
        # 伯努利 NB 只考虑特征为 1 的情况
        return (X * self.feature_log_prob_).sum(axis=1).reshape(-1, 1) + self.class_log_prior_

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测类别。"""
        log_proba = self.predict_log_proba(X)
        return self.classes[np.argmax(log_proba, axis=1)]


def compare_naive_bayes():
    """对比三种朴素贝叶斯模型。"""
    print("=" * 60)
    print("朴素贝叶斯模型对比")
    print("=" * 60)

    np.random.seed(42)

    # 示例 1：连续特征（鸢尾花）
    print("\n1. 高斯朴素贝叶斯（连续特征）")
    print("-" * 40)

    from sklearn.datasets import load_iris

    iris = load_iris()
    X, y = iris.data, iris.target

    # 划分数据
    np.random.seed(42)
    indices = np.random.permutation(len(y))
    train_idx = indices[:120]
    test_idx = indices[120:]

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # 训练 Gaussian NB
    gnb = GaussianNB()
    gnb.fit(X_train, y_train)
    y_pred = gnb.predict(X_test)
    acc = np.mean(y_pred == y_test)
    print(f"准确率: {acc:.2%}")

    # 示例 2：离散特征（文本分类）
    print("\n2. 多项式朴素贝叶斯（离散特征/词频）")
    print("-" * 40)

    # 模拟词频数据：20 个文档，100 个词
    n_docs, n_words = 200, 500
    X_text = np.random.randint(0, 10, size=(n_docs, n_words))  # 词频
    y_text = np.array([0] * 100 + [1] * 100)  # 两类文档

    # 划分
    mnb = MultinomialNB(alpha=1.0)
    mnb.fit(X_text[:150], y_text[:150])
    y_pred_mnb = mnb.predict(X_text[150:])
    acc_mnb = np.mean(y_pred_mnb == y_text[150:])
    print(f"准确率: {acc_mnb:.2%}")

    # 示例 3：二元特征
    print("\n3. 伯努利朴素贝叶斯（二元特征）")
    print("-" * 40)

    # 模拟二元数据
    X_binary = np.random.randint(0, 2, size=(200, 20))
    y_binary = np.array([0] * 100 + [1] * 100)

    bnb = BernoulliNB()
    bnb.fit(X_binary[:150], y_binary[:150])
    y_pred_bnb = bnb.predict(X_binary[150:])
    acc_bnb = np.mean(y_pred_bnb == y_binary[150:])
    print(f"准确率: {acc_bnb:.2%}")


def naive_bayes_text_classification():
    """演示朴素贝叶斯文本分类。"""
    print("\n" + "=" * 60)
    print("朴素贝叶斯文本分类演示")
    print("=" * 60)

    # 简单词汇表
    vocabulary = ['great', 'excellent', 'good', 'bad', 'terrible', 'awful', 'worst', 'best']

    # 训练文档（词频）
    documents = [
        [5, 3, 0, 0, 0, 0, 0, 1],  # 正面
        [2, 4, 1, 0, 0, 0, 0, 0],  # 正面
        [0, 0, 3, 2, 0, 0, 0, 0],  # 中性
        [0, 0, 1, 4, 2, 1, 0, 0],  # 负面
        [0, 0, 0, 0, 3, 4, 1, 0],  # 负面
        [0, 0, 0, 0, 1, 2, 5, 2],  # 负面
    ]
    labels = [1, 1, 0, 0, 0, 0]  # 1=正面, 0=负面

    X_train = np.array(documents)
    y_train = np.array(labels)

    # 训练
    mnb = MultinomialNB(alpha=1.0)
    mnb.fit(X_train, y_train)

    # 测试文档
    test_doc = np.array([[3, 2, 0, 0, 0, 0, 0, 0]])  # "great excellent"
    log_proba = mnb.predict_log_proba(test_doc)
    pred = mnb.predict(test_doc)

    print(f"\n测试文档: great excellent")
    print(f"预测类别: {'正面' if pred[0] == 1 else '负面'}")
    print(f"预测概率: 正面={np.exp(log_proba[0, 1]):.2%}, 负面={np.exp(log_proba[0, 0]):.2%}")


def naive_bayes_conditional_independence():
    """演示条件独立性假设。"""
    print("\n" + "=" * 60)
    print("条件独立性假设的影响")
    print("=" * 60)

    # 演示为什么独立性假设有时会导致问题
    np.random.seed(42)

    # 创建高度相关的数据
    n = 500
    # X2 = X1 + 噪声
    X1 = np.random.randn(n)
    X2 = X1 + np.random.randn(n) * 0.1

    y = (X1 + X2 > 0).astype(int)

    X = np.column_stack([X1, X2])

    # 训练 Gaussian NB
    gnb = GaussianNB()
    gnb.fit(X, y)

    # 预测概率
    X_test = np.array([[1, 1]])
    log_proba = gnb.predict_log_proba(X_test)
    prob = np.exp(log_proba[0, 1])

    print(f"\n测试点: X1=1, X2=1")
    print(f"P(正类|X1,X2) = {prob:.4f}")

    # 独立假设下的估计（实际会偏高）
    print(f"\n问题：X1 和 X2 高度相关，独立性假设失效")
    print(f"      朴素贝叶斯可能高估或低估真实概率")


if __name__ == "__main__":
    compare_naive_bayes()
    naive_bayes_text_classification()
    naive_bayes_conditional_independence()