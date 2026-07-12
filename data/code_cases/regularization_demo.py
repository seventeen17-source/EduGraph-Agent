"""L1/L2 正则化完整实现：从原理到实践。

Related node: ml_regularization
Source IDs: book_hands_on_ml_3e_zh, book_zhou_ml
"""

from __future__ import annotations

import numpy as np


def l2_penalty(weights: np.ndarray, lambda_: float = 1.0) -> float:
    """
    L2 正则化惩罚项：λ * ||w||² / 2

    也称为权重衰减（Weight Decay）。
    """
    return lambda_ * np.sum(weights ** 2) / 2


def l2_gradient(weights: np.ndarray, lambda_: float = 1.0) -> np.ndarray:
    """L2 正则化的梯度：λ * w。"""
    return lambda_ * weights


def l1_penalty(weights: np.ndarray, lambda_: float = 1.0) -> float:
    """
    L1 正则化惩罚项：λ * ||w||₁

    会产生稀疏解（很多权重变为 0）。
    """
    return lambda_ * np.sum(np.abs(weights))


def l1_gradient(weights: np.ndarray, lambda_: float = 1.0) -> np.ndarray:
    """
    L1 正则化的次梯度：λ * sign(w)

    sign(0) = 0。
    """
    return lambda_ * np.sign(weights)


def elastic_net_penalty(weights: np.ndarray, lambda_: float = 1.0, l1_ratio: float = 0.5) -> float:
    """
    Elastic Net：L1 和 L2 的组合。

    penalty = λ * (l1_ratio * ||w||₁ + (1 - l1_ratio) * ||w||² / 2)
    """
    l1_part = l1_ratio * np.sum(np.abs(weights))
    l2_part = (1 - l1_ratio) * np.sum(weights ** 2) / 2
    return lambda_ * (l1_part + l2_part)


def elastic_net_gradient(weights: np.ndarray, lambda_: float = 1.0, l1_ratio: float = 0.5) -> np.ndarray:
    """Elastic Net 的次梯度。"""
    l1_grad = l1_ratio * np.sign(weights)
    l2_grad = (1 - l1_ratio) * weights
    return lambda_ * (l1_grad + l2_grad)


class RegularizedLinearRegression:
    """带正则化的线性回归。"""

    def __init__(self, reg_lambda: float = 1.0, reg_type: str = 'l2', l1_ratio: float = 0.5):
        """
        Args:
            reg_lambda: 正则化强度
            reg_type: 'l1', 'l2', 或 'elastic_net'
            l1_ratio: Elastic Net 中 L1 的比例
        """
        self.reg_lambda = reg_lambda
        self.reg_type = reg_type
        self.l1_ratio = l1_ratio
        self.weights: np.ndarray | None = None
        self.bias: float = 0.0

    def _mse_loss(self, X: np.ndarray, y: np.ndarray) -> float:
        """计算 MSE 损失。"""
        predictions = X @ self.weights + self.bias
        return np.mean((predictions - y) ** 2)

    def _gradients(self, X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
        """计算权重和偏置的梯度（不含正则化项）。"""
        m = len(y)
        predictions = X @ self.weights + self.bias
        errors = predictions - y

        dw = (2 / m) * (X.T @ errors)
        db = (2 / m) * np.sum(errors)

        # 添加正则化梯度
        if self.reg_type == 'l2':
            dw += l2_gradient(self.weights, self.reg_lambda)
        elif self.reg_type == 'l1':
            dw += l1_gradient(self.weights, self.reg_lambda)
        elif self.reg_type == 'elastic_net':
            dw += elastic_net_gradient(self.weights, self.reg_lambda, self.l1_ratio)

        return dw, db

    def fit(self, X: np.ndarray, y: np.ndarray, lr: float = 0.01, n_iters: int = 1000, verbose: bool = False):
        """训练模型。"""
        n_features = X.shape[1]
        self.weights = np.zeros(n_features)
        self.bias = 0.0

        for i in range(n_iters):
            dw, db = self._gradients(X, y)
            self.weights -= lr * dw
            self.bias -= lr * db

            if verbose and (i + 1) % 200 == 0:
                mse = self._mse_loss(X, y)
                reg = self._get_reg_penalty()
                print(f"Iter {i+1}: MSE={mse:.4f}, Reg={reg:.4f}, Total={mse + reg:.4f}")

        return self

    def _get_reg_penalty(self) -> float:
        """获取当前权重下的正则化惩罚。"""
        if self.reg_type == 'l2':
            return l2_penalty(self.weights, self.reg_lambda)
        elif self.reg_type == 'l1':
            return l1_penalty(self.weights, self.reg_lambda)
        elif self.reg_type == 'elastic_net':
            return elastic_net_penalty(self.weights, self.reg_lambda, self.l1_ratio)
        return 0.0

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.weights + self.bias

    def get_sparse_weights(self, threshold: float = 0.01) -> dict[int, float]:
        """获取稀疏权重（非零权重）。"""
        return {i: w for i, w in enumerate(self.weights) if abs(w) > threshold}


def compare_regularization_methods():
    """对比不同正则化方法的效果。"""
    print("=" * 60)
    print("L1 vs L2 vs Elastic Net 正则化对比")
    print("=" * 60)

    np.random.seed(42)

    # 创建高维数据（特征数 > 样本数）
    n_samples, n_features = 50, 20
    X = np.random.randn(n_samples, n_features)
    true_weights = np.array([1.0, 0.5, -0.3, 0.0] + [0.0] * 16)  # 只有前4个特征有效
    y = X @ true_weights + np.random.randn(n_samples) * 0.5

    print(f"\n数据维度: {X.shape}")
    print(f"真实有效权重（非零）: {np.where(np.abs(true_weights) > 0.1)[0].tolist()}")

    # 不同正则化强度
    lambdas = [0.001, 0.01, 0.1, 1.0]

    print("\n" + "-" * 70)
    print(f"{'Lambda':<10} {'L2 Norm':<15} {'L1 Norm':<15} {'L2 Non-zero':<15} {'L1 Non-zero':<15}")
    print("-" * 70)

    for lam in lambdas:
        # L2 正则化
        model_l2 = RegularizedLinearRegression(lam, 'l2')
        model_l2.fit(X, y, lr=0.01, n_iters=1000)
        l2_norm = np.linalg.norm(model_l2.weights)
        l2_nonzero = np.sum(np.abs(model_l2.weights) > 0.01)

        # L1 正则化
        model_l1 = RegularizedLinearRegression(lam, 'l1')
        model_l1.fit(X, y, lr=0.01, n_iters=1000)
        l1_norm = np.sum(np.abs(model_l1.weights))
        l1_nonzero = np.sum(np.abs(model_l1.weights) > 0.01)

        print(f"{lam:<10} {l2_norm:<15.4f} {l1_norm:<15.4f} {l2_nonzero:<15} {l1_nonzero:<15}")

    print("\n观察：")
    print("  - L2 正则化：权重趋向小值但不为零，所有特征都参与预测")
    print("  - L1 正则化：产生稀疏解，将不重要特征的权重设为零")
    print("  - λ 越大，正则化越强，权重越接近零")


def elastic_net_path():
    """演示 Elastic Net 的 L1/L2 路径。"""
    print("\n" + "=" * 60)
    print("Elastic Net 路径分析")
    print("=" * 60)

    np.random.seed(42)
    n_samples, n_features = 100, 5
    X = np.random.randn(n_samples, n_features)
    true_weights = np.array([3.0, 1.5, 0.0, 0.0, 0.0])
    y = X @ true_weights + np.random.randn(n_samples) * 0.5

    l1_ratios = [0.1, 0.5, 0.9]  # L1 比例
    lambda_ = 0.5

    print(f"\n固定 λ={lambda_}，改变 L1/L2 比例：")
    print("-" * 60)

    for ratio in l1_ratios:
        model = RegularizedLinearRegression(lambda_, 'elastic_net', l1_ratio=ratio)
        model.fit(X, y, lr=0.01, n_iters=2000)

        print(f"\nl1_ratio={ratio} (L1 为主)" if ratio > 0.5 else f"\nl1_ratio={ratio} (L2 为主)")
        print(f"  权重: {model.weights.round(4)}")
        print(f"  L2范数: {np.linalg.norm(model.weights):.4f}")
        print(f"  L1范数: {np.sum(np.abs(model.weights)):.4f}")
        print(f"  非零权重数: {np.sum(np.abs(model.weights) > 0.01)}")


def regularization_bias_variance():
    """演示正则化如何平衡偏差和方差。"""
    print("\n" + "=" * 60)
    print("正则化与偏差-方差权衡")
    print("=" * 60)

    np.random.seed(42)

    # 真实函数：y = sin(2πx)
    def true_func(x):
        return np.sin(2 * np.pi * x)

    # 多次采样不同训练集
    n_datasets = 50
    n_train = 30
    test_x = np.linspace(0, 1, 100)

    # 不同正则化强度
    lambdas = [0.0, 0.001, 0.01, 0.1, 1.0]

    print("\n测试不同正则化强度对泛化能力的影响：")
    print("-" * 60)

    for lam in lambdas:
        predictions = []

        for _ in range(n_datasets):
            # 采样训练数据
            train_x = np.sort(np.random.rand(n_train))
            train_y = true_func(train_x) + np.random.randn(n_train) * 0.3

            # 多项式特征
            poly_degree = 15
            X_train = np.column_stack([train_x ** d for d in range(poly_degree + 1)])
            X_test = np.column_stack([test_x ** d for d in range(poly_degree + 1)])

            # 训练模型
            model = RegularizedLinearRegression(lam, 'l2')
            model.fit(X_train, train_y, lr=0.001, n_iters=5000)
            pred = model.predict(X_test)
            predictions.append(pred)

        predictions = np.array(predictions)
        mean_pred = predictions.mean(axis=0)
        var_pred = predictions.var(axis=0)
        bias_sq = (mean_pred - true_func(test_x)) ** 2
        noise = 0.3 ** 2

        bias_sq_mean = np.mean(bias_sq)
        var_mean = np.mean(var_pred)
        total = bias_sq_mean + var_mean + noise

        print(f"λ={lam:<8} Bias²={bias_sq_mean:.4f}, Var={var_mean:.4f}, "
              f"Total={total:.4f} (噪声={noise:.4f})")

    print("\n观察：")
    print("  - λ=0 时：低偏差，高方差（过拟合）")
    print("  - λ 增大时：偏差增加，方差减小")
    print("  - 最优 λ 平衡偏差和方差，总泛化误差最小")


if __name__ == "__main__":
    compare_regularization_methods()
    elastic_net_path()
    regularization_bias_variance()
