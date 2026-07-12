"""支持向量机（SVM）完整实现：硬间隔、软间隔与核函数。

Related node: ml_svm
Source IDs: book_hands_on_ml_3e_zh, book_zhou_ml, book_lihang_statistical_learning
"""

from __future__ import annotations

import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler


class LinearSVM:
    """线性支持向量机（使用合页损失，直接优化间隔）。"""

    def __init__(self, lr: float = 0.001, C: float = 1.0, n_iters: int = 1000):
        self.lr = lr
        self.C = C  # 正则化参数
        self.n_iters = n_iters
        self.weights: np.ndarray | None = None
        self.bias: float = 0.0

    def _hinge_loss(self, scores: np.ndarray, y: np.ndarray) -> float:
        """合页损失：max(0, 1 - y * score)。"""
        return np.mean(np.maximum(0, 1 - y * scores))

    def _gradient(self, X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
        """计算权重和偏置的梯度。"""
        scores = X @ self.weights + self.bias
        margins = y * scores

        # 找出违反间隔约束的样本（margin < 1）
        violations = margins < 1

        # 权重梯度：L2 正则化项 + 合页损失项
        dw = self.weights - (self.C / len(y)) * np.sum(
            X[violations] * y[violations].reshape(-1, 1), axis=0
        )
        db = -(self.C / len(y)) * np.sum(y[violations])

        return dw, db

    def fit(self, X: np.ndarray, y: np.ndarray, verbose: bool = False):
        """训练 SVM。"""
        n_features = X.shape[1]
        self.weights = np.zeros(n_features)
        self.bias = 0.0

        for i in range(self.n_iters):
            dw, db = self._gradient(X, y)

            self.weights -= self.lr * dw
            self.bias -= self.lr * db

            if verbose and (i + 1) % 100 == 0:
                loss = self._hinge_loss(X @ self.weights + self.bias, y)
                print(f"Iter {i+1}: Hinge Loss = {loss:.4f}")

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        scores = X @ self.weights + self.bias
        return np.sign(scores)

    def support_vector_indices(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """找出支持向量的索引（margin 在 0 到 1 之间的样本）。"""
        scores = X @ self.weights + self.bias
        margins = y * scores
        # 支持向量：0 < margin < 1（在间隔边界上或内部）
        return np.where((margins > 0) & (margins < 1))[0]


def rbf_kernel(X1: np.ndarray, X2: np.ndarray, gamma: float = 0.1) -> np.ndarray:
    """
    径向基函数（RBF）核，也称高斯核。

    K(x, z) = exp(-gamma * ||x - z||^2)
    """
    sq_dists = np.sum(X1**2, axis=1).reshape(-1, 1) + np.sum(X2**2, axis=1) - 2 * X1 @ X2.T
    return np.exp(-gamma * sq_dists)


def polynomial_kernel(X1: np.ndarray, X2: np.ndarray, degree: int = 3, coef0: float = 1.0) -> np.ndarray:
    """
    多项式核。

    K(x, z) = (coef0 + x·z)^degree
    """
    return (coef0 + X1 @ X2.T) ** degree


class KernelSVM:
    """基于核函数的 SVM（使用高斯核）。"""

    def __init__(self, C: float = 1.0, gamma: float = 0.1, n_iters: int = 200):
        self.C = C
        self.gamma = gamma
        self.n_iters = n_iters
        self.alphas: np.ndarray | None = None
        self.support_vectors: np.ndarray | None = None
        self.support_vector_labels: np.ndarray | None = None
        self.bias: float = 0.0

    def _compute_kernel(self, X: np.ndarray) -> np.ndarray:
        """计算核矩阵。"""
        return rbf_kernel(X, X, self.gamma)

    def _compute_bias(self, X: np.ndarray, y: np.ndarray) -> float:
        """计算偏置 b。"""
        # 选择一个支持向量计算偏置
        sv_idx = np.where(self.alphas > 1e-5)[0][0]
        sv_x = self.support_vectors[sv_idx]
        sv_y = self.support_vector_labels[sv_idx]

        kernel_sv = rbf_kernel(sv_x.reshape(1, -1), self.support_vectors, self.gamma).flatten()
        return sv_y - np.sum(self.alphas * self.support_vector_labels * kernel_sv)

    def fit(self, X: np.ndarray, y: np.ndarray, verbose: bool = False):
        """训练核 SVM（使用简化版 SMO 算法思想）。"""
        n_samples = len(y)

        # 将标签转换为 +1/-1
        y_binary = np.where(y == 0, -1, 1)

        # 初始化
        self.alphas = np.zeros(n_samples)
        self.bias = 0.0

        K = self._compute_kernel(X)

        for iteration in range(self.n_iters):
            alpha_changed = 0

            for i in range(n_samples):
                # 简化的坐标下降：选择 i，更新 alpha_i
                Ei = np.sum(self.alphas * y_binary * K[i]) + self.bias - y_binary[i]

                if (y_binary[i] * Ei < -0.001 and self.alphas[i] < self.C) or \
                   (y_binary[i] * Ei > 0.001 and self.alphas[i] > 0):

                    # 随机选择 j != i
                    j = np.random.choice([k for k in range(n_samples) if k != i])

                    Ej = np.sum(self.alphas * y_binary * K[j]) + self.bias - y_binary[j]

                    alpha_i_old = self.alphas[i]
                    alpha_j_old = self.alphas[j]

                    # 计算边界
                    if y_binary[i] != y_binary[j]:
                        L = max(0, self.alphas[j] - self.alphas[i])
                        H = min(self.C, self.C + self.alphas[j] - self.alphas[i])
                    else:
                        L = max(0, self.alphas[i] + self.alphas[j] - self.C)
                        H = min(self.C, self.alphas[i] + self.alphas[j])

                    if L == H:
                        continue

                    # 更新 alpha_j
                    eta = 2 * K[i, j] - K[i, i] - K[j, j]
                    if eta >= 0:
                        continue

                    self.alphas[j] -= (y_binary[j] * (Ei - Ej)) / eta
                    self.alphas[j] = np.clip(self.alphas[j], L, H)

                    if abs(self.alphas[j] - alpha_j_old) < 1e-5:
                        continue

                    # 更新 alpha_i
                    self.alphas[i] += y_binary[i] * y_binary[j] * (alpha_j_old - self.alphas[j])

                    # 更新 bias
                    b1 = self.bias - Ei - y_binary[i] * (self.alphas[i] - alpha_i_old) * K[i, i] \
                         - y_binary[j] * (self.alphas[j] - alpha_j_old) * K[i, j]
                    b2 = self.bias - Ej - y_binary[i] * (self.alphas[i] - alpha_i_old) * K[i, j] \
                         - y_binary[j] * (self.alphas[j] - alpha_j_old) * K[j, j]

                    if 0 < self.alphas[i] < self.C:
                        self.bias = b1
                    elif 0 < self.alphas[j] < self.C:
                        self.bias = b2
                    else:
                        self.bias = (b1 + b2) / 2

                    alpha_changed += 1

            if verbose and (iteration + 1) % 50 == 0:
                print(f"Iter {iteration+1}: {alpha_changed} alphas changed")

        # 保存支持向量
        sv_mask = self.alphas > 1e-5
        self.support_vectors = X[sv_mask]
        self.support_vector_labels = y_binary[sv_mask]
        self.alphas = self.alphas[sv_mask]
        self.bias = self._compute_bias(X, y_binary)

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测新样本。"""
        K = rbf_kernel(X, self.support_vectors, self.gamma)
        scores = np.sum(self.alphas * self.support_vector_labels * K, axis=1) + self.bias
        return np.where(scores > 0, 1, 0)


if __name__ == "__main__":
    from sklearn.datasets import make_moons, make_circles

    # 测试线性可分数据
    print("=" * 50)
    print("1. 线性 SVM 测试（线性可分数据）")
    print("=" * 50)

    X1, y1 = make_circles(n_samples=100, factor=0.5, noise=0.1, random_state=42)

    # 使用 sklearn SVC 验证
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X1)

    svm_rbf = SVC(kernel='rbf', C=1.0, gamma='scale')
    svm_rbf.fit(X_scaled, y1)
    acc = svm_rbf.score(X_scaled, y1)
    print(f"sklearn RBF-SVM 准确率: {acc:.2%}")
    print(f"支持向量数量: {len(svm_rbf.support_vectors_)}")

    # 测试我们自己的线性 SVM
    print("\n" + "=" * 50)
    print("2. 线性 SVM（自己实现）")
    print("=" * 50)

    X2 = np.array([[1, 2], [2, 3], [3, 3], [2, 1], [3, 1], [4, 2]])
    y2 = np.array([1, 1, 1, -1, -1, -1])

    svm = LinearSVM(lr=0.001, C=1.0, n_iters=500)
    svm.fit(X2, y2, verbose=False)

    print(f"权重: {svm.weights}")
    print(f"偏置: {svm.bias:.4f}")
    print(f"预测: {svm.predict(X2)}")
    print(f"真实: {y2}")

    sv_idx = svm.support_vector_indices(X2, y2)
    print(f"支持向量索引: {sv_idx}")
    print(f"支持向量:\n{X2[sv_idx]}")
