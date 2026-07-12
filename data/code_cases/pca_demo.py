"""PCA（主成分分析）完整实现：从原理到降维应用。

Related node: ml_dimensionality_reduction
Source IDs: book_hands_on_ml_3e_zh, book_prml_bishop
"""

from __future__ import annotations

import numpy as np


def compute_mean(X: np.ndarray, axis: int = 0) -> np.ndarray:
    """计算均值。"""
    return np.mean(X, axis=axis)


def compute_covariance(X: np.ndarray, center: bool = True) -> np.ndarray:
    """
    计算协方差矩阵。

    Cov = (X - μ)ᵀ(X - μ) / (n - 1)
    """
    if center:
        X_centered = X - np.mean(X, axis=0)
    else:
        X_centered = X
    return X_centered.T @ X_centered / (X.shape[0] - 1)


def power_iteration(X: np.ndarray, n_components: int = 1, n_iters: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """
    幂迭代法求主成分。

    用于大规模数据的 PCA。
    """
    n_features = X.shape[1]
    components = []
    variances = []

    # 中心化数据
    X_centered = X - np.mean(X, axis=0)

    for _ in range(n_components):
        # 随机初始化
        v = np.random.randn(n_features)
        v = v / np.linalg.norm(v)

        for _ in range(n_iters):
            # 幂迭代
            v = X_centered.T @ (X_centered @ v)
            v = v / np.linalg.norm(v)

        # 计算方差
        var = np.var(X_centered @ v)
        components.append(v)
        variances.append(var)

        # 数据去相关（Deflation）
        X_centered = X_centered - (X_centered @ v).reshape(-1, 1) * v

    return np.array(components), np.array(variances)


class PCA:
    """主成分分析。"""

    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self.mean: np.ndarray | None = None
        self.components: np.ndarray | None = None
        self.explained_variance: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "PCA":
        """拟合 PCA 模型。"""
        n_samples, n_features = X.shape
        k = min(self.n_components, n_features)

        # 中心化
        self.mean = np.mean(X, axis=0)
        X_centered = X - self.mean

        # 使用 SVD 分解（更数值稳定）
        U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)

        # 取前 k 个主成分
        self.components = Vt[:k]
        self.explained_variance = S[:k] ** 2 / (n_samples - 1)

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """投影到主成分空间。"""
        X_centered = X - self.mean
        return X_centered @ self.components.T

    def inverse_transform(self, X_transformed: np.ndarray) -> np.ndarray:
        """从主成分空间重建数据。"""
        return X_transformed @ self.components + self.mean

    def explained_variance_ratio(self) -> np.ndarray:
        """各主成分解释的方差比例。"""
        total_var = np.sum(self.explained_variance)
        return self.explained_variance / total_var

    def cumulative_variance_ratio(self, n: int = None) -> float:
        """前 n 个主成分的累计方差解释比例。"""
        if n is None:
            n = self.n_components
        return np.sum(self.explained_variance_ratio()[:n])


def reconstruct_from_components():
    """演示 PCA 重建。"""
    print("=" * 60)
    print("PCA 降维与重建演示")
    print("=" * 60)

    np.random.seed(42)

    # 生成二维数据（长椭圆形）
    theta = np.pi / 4
    scale = np.array([3.0, 0.5])
    rot = np.array([[np.cos(theta), -np.sin(theta)],
                  [np.sin(theta), np.cos(theta)]])

    n_samples = 500
    X = np.random.randn(n_samples, 2) * scale @ rot.T + np.array([5, 5])

    print(f"\n原始数据形状: {X.shape}")
    print(f"数据均值: {X.mean(axis=0).round(2)}")

    # PCA
    pca = PCA(n_components=2)
    pca.fit(X)

    print(f"\n主成分方向:")
    for i, comp in enumerate(pca.components):
        print(f"  PC{i+1}: {comp.round(4)}, 解释方差: {pca.explained_variance_ratio()[i]:.2%}")

    # 降维到 1 维
    X_1d = pca.transform(X)[:, :1]
    X_reconstructed_1d = pca.inverse_transform(X_1d)

    # 降维到 2 维
    X_2d = pca.transform(X)
    X_reconstructed_2d = pca.inverse_transform(X_2d)

    # 计算重建误差
    mse_1d = np.mean((X - X_reconstructed_1d) ** 2)
    mse_2d = np.mean((X - X_reconstructed_2d) ** 2)

    print(f"\n重建误差:")
    print(f"  1 维重建 MSE: {mse_1d:.4f}")
    print(f"  2 维重建 MSE: {mse_2d:.4f}")

    print(f"\n累计方差解释:")
    print(f"  1 维: {pca.cumulative_variance_ratio(1):.2%}")
    print(f"  2 维: {pca.cumulative_variance_ratio(2):.2%}")


def face_recognition_demo():
    """演示 PCA 在人脸识别中的应用。"""
    print("\n" + "=" * 60)
    print("PCA 人脸识别演示（简化版）")
    print("=" * 60)

    # 模拟人脸数据：100 个 64x64 的人脸图像
    np.random.seed(42)
    n_faces = 100
    image_size = 64 * 64
    n_eigenfaces = 20

    # 生成模拟人脸（真实人脸有规律，噪声无规律）
    faces = []
    for i in range(n_faces):
        # 基础人脸（均值人脸 + 随机特征）
        face = np.random.randn(image_size) * 0.3

        # 添加一些"身份"特征
        face[:100] += np.sin(np.linspace(0, np.pi, 100)) * (i / 20)

        faces.append(face)

    faces = np.array(faces)

    print(f"\n模拟数据: {faces.shape}")

    # PCA 分解
    pca = PCA(n_components=n_eigenfaces)
    pca.fit(faces)

    print(f"\n主成分数量: {n_eigenfaces}")
    print(f"累计方差解释: {pca.cumulative_variance_ratio():.2%}")

    # 投影到特征空间
    faces_pca = pca.transform(faces)

    print(f"\n降维后形状: {faces_pca.shape}")
    print(f"压缩比: {faces.size / faces_pca.size:.1f}x")


def choosing_n_components():
    """演示如何选择主成分数量。"""
    print("\n" + "=" * 60)
    print("选择主成分数量：肘部法则")
    print("=" * 60)

    np.random.seed(42)

    # 生成数据：低维结构 + 噪声
    n_samples = 200
    n_features = 20

    # 真实结构只有 3 维
    X = np.random.randn(n_samples, 3) @ np.random.randn(3, n_features)
    X += np.random.randn(n_samples, n_features) * 0.5

    # PCA
    pca = PCA(n_components=n_features)
    pca.fit(X)

    print("\n各主成分解释的方差比例:")
    for i in range(min(10, n_features)):
        var_ratio = pca.explained_variance_ratio()[i]
        print(f"  PC{i+1}: {var_ratio:.4f} ({var_ratio*100:.2f}%)")

    print(f"\n累计方差解释:")
    for k in [3, 5, 10, 15, 20]:
        cum_var = pca.cumulative_variance_ratio(k)
        print(f"  前 {k} 个主成分: {cum_var:.2%}")

    print("\n观察：")
    print("  - 前 3 个主成分解释了大部分方差（真实维度）")
    print("  - 之后方差急剧下降（噪声主导）")
    print("  - 选择肘部位置对应的 k 值")


def pca_for_visualization():
    """演示 PCA 用于高维数据可视化。"""
    print("\n" + "=" * 60)
    print("PCA 用于高维数据可视化")
    print("=" * 60)

    # 模拟 3 类数据，每类 50 样本，10 维
    np.random.seed(42)
    n_per_class = 50
    n_features = 10
    n_classes = 3

    data = []
    labels = []

    for c in range(n_classes):
        # 每类有自己的中心
        center = np.random.randn(n_features) * 2
        X_c = np.random.randn(n_per_class, n_features) + center
        data.append(X_c)
        labels.extend([c] * n_per_class)

    X = np.vstack(data)
    y = np.array(labels)

    # PCA 降到 2 维
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X)

    print(f"\n原始维度: {X.shape}")
    print(f"降维后: {X_2d.shape}")
    print(f"累计方差解释: {pca.cumulative_variance_ratio():.2%}")

    # 计算类间分离度
    print("\n各类中心投影后的位置:")
    for c in range(n_classes):
        mask = y == c
        center_2d = X_2d[mask].mean(axis=0)
        print(f"  Class {c}: ({center_2d[0]:.2f}, {center_2d[1]:.2f})")


if __name__ == "__main__":
    reconstruct_from_components()
    face_recognition_demo()
    choosing_n_components()
    pca_for_visualization()