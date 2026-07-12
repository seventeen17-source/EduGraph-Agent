"""过拟合与正则化完整演示：学习曲线、偏差方差分析、L1/L2 正则化对比。

Related node: ml_overfitting_underfitting
Source IDs: book_hands_on_ml_3e_zh, book_zhou_ml, book_deep_learning_ai
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from typing import Callable


def generate_data(n_samples: int = 100, noise: float = 0.5, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """生成带有噪声的二次数据。"""
    np.random.seed(seed)
    X = np.linspace(-3, 3, n_samples)
    y_true = X**2 - 2*X + 1
    y = y_true + np.random.randn(n_samples) * noise
    return X.reshape(-1, 1), y


class PolynomialFeatures:
    """多项式特征生成器。"""

    def __init__(self, degree: int = 2):
        self.degree = degree

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_poly = np.ones((X.shape[0], 1))
        for d in range(1, self.degree + 1):
            X_poly = np.hstack([X_poly, X**d])
        return X_poly


class RidgeRegression:
    """岭回归（L2 正则化线性回归）。"""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.weights: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RidgeRegression":
        n_features = X.shape[1]
        # (X^T X + αI)^{-1} X^T y
        I = np.eye(n_features)
        I[0, 0] = 0  # 不对偏置正则化
        XtX = X.T @ X
        Xty = X.T @ y
        self.weights = np.linalg.solve(XtX + self.alpha * I, Xty)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.weights


class LassoRegression:
    """Lasso 回归（L1 正则化线性回归）。"""

    def __init__(self, alpha: float = 0.1, lr: float = 0.01, n_iters: int = 1000):
        self.alpha = alpha
        self.lr = lr
        self.n_iters = n_iters
        self.weights: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LassoRegression":
        n_features = X.shape[1]
        self.weights = np.zeros(n_features)
        m = len(y)

        for _ in range(self.n_iters):
            predictions = X @ self.weights
            error = predictions - y

            # 梯度：原始梯度 + L1 正则项（用次梯度）
            gradient = (2 / m) * (X.T @ error) + self.alpha * np.sign(self.weights)
            # 不对偏置正则化
            gradient[0] = (2 / m) * (X[:, 0].T @ error)

            self.weights -= self.lr * gradient

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.weights


def compute_mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """计算均方误差。"""
    return np.mean((y_true - y_pred) ** 2)


def train_val_split(X: np.ndarray, y: np.ndarray, val_ratio: float = 0.2, seed: int = 42):
    """简单训练/验证集划分。"""
    np.random.seed(seed)
    indices = np.random.permutation(len(X))
    val_size = int(len(X) * val_ratio)
    val_idx, train_idx = indices[:val_size], indices[val_size:]
    return X[train_idx], X[val_idx], y[train_idx], y[val_idx]


def demonstrate_overfitting():
    """演示过拟合现象：随着模型复杂度增加，训练误差降低但验证误差先降后升。"""
    print("=" * 60)
    print("过拟合演示：模型复杂度 vs 泛化能力")
    print("=" * 60)

    # 生成数据
    X, y = generate_data(n_samples=50, noise=1.5)
    X_train, X_val, y_train, y_val = train_val_split(X, y, val_ratio=0.3)

    degrees = range(1, 15)
    train_errors = []
    val_errors = []

    print(f"\n{'Degree':<8} {'Train MSE':<15} {'Val MSE':<15} {'状态':<10}")
    print("-" * 50)

    for deg in degrees:
        poly = PolynomialFeatures(degree=deg)
        X_train_poly = poly.transform(X_train)
        X_val_poly = poly.transform(X_val)

        # 使用 Ridge 正则化防止数值问题
        model = RidgeRegression(alpha=0.001)
        model.fit(X_train_poly, y_train)

        train_pred = model.predict(X_train_poly)
        val_pred = model.predict(X_val_poly)

        train_mse = compute_mse(y_train, train_pred)
        val_mse = compute_mse(y_val, val_pred)

        train_errors.append(train_mse)
        val_errors.append(val_mse)

        # 判断状态
        if deg <= 3:
            status = "欠拟合"
        elif val_mse > train_mse * 1.5:
            status = "过拟合"
        else:
            status = "良好"

        print(f"{deg:<8} {train_mse:<15.4f} {val_mse:<15.4f} {status:<10}")

    print(f"\n观察：")
    print(f"  - 训练误差随复杂度增加而持续下降")
    print(f"  - 验证误差在某个点开始上升（过拟合）")
    print(f"  - 过拟合点附近是模型复杂度的最优选择")


def demonstrate_regularization():
    """演示 L1/L2 正则化的效果。"""
    print("\n" + "=" * 60)
    print("正则化效果演示：L1 (Lasso) vs L2 (Ridge)")
    print("=" * 60)

    # 生成高维数据（特征数 > 样本数）
    np.random.seed(42)
    n_samples, n_features = 50, 100
    X = np.random.randn(n_samples, n_features)
    y = X[:, 0] + 0.5 * X[:, 1] + np.random.randn(n_samples) * 0.5

    # 划分数据
    X_train, X_val, y_train, y_val = train_val_split(X, y)

    # 不同正则化强度的对比
    alphas = [0.001, 0.01, 0.1, 1.0, 10.0]

    print(f"\n{'Alpha':<10} {'Ridge Train':<15} {'Ridge Val':<15} "
          f"{'Lasso Train':<15} {'Lasso Val':<15}")
    print("-" * 75)

    ridge_train_errors = []
    ridge_val_errors = []
    lasso_train_errors = []
    lasso_val_errors = []

    for alpha in alphas:
        # Ridge
        ridge = RidgeRegression(alpha=alpha)
        ridge.fit(X_train, y_train)
        ridge_train = compute_mse(y_train, ridge.predict(X_train))
        ridge_val = compute_mse(y_val, ridge.predict(X_val))
        ridge_train_errors.append(ridge_train)
        ridge_val_errors.append(ridge_val)

        # Lasso
        lasso = LassoRegression(alpha=alpha, lr=0.01, n_iters=2000)
        lasso.fit(X_train, y_train)
        lasso_train = compute_mse(y_train, lasso.predict(X_train))
        lasso_val = compute_mse(y_val, lasso.predict(X_val))
        lasso_train_errors.append(lasso_train)
        lasso_val_errors.append(lasso_val)

        print(f"{alpha:<10} {ridge_train:<15.4f} {ridge_val:<15.4f} "
              f"{lasso_train:<15.4f} {lasso_val:<15.4f}")

    print(f"\n观察：")
    print(f"  - alpha 太小：过拟合，训练误差低但验证误差高")
    print(f"  - alpha 太大：欠拟合，训练和验证误差都高")
    print(f"  - Lasso 可以产生稀疏权重（部分特征权重为 0）")
    print(f"  - Ridge 只能缩小权重但不能归零")


def demonstrate_bias_variance():
    """演示偏差-方差分解。"""
    print("\n" + "=" * 60)
    print("偏差-方差分解演示")
    print("=" * 60)

    # 真实函数：y = sin(2πx)
    def true_function(x):
        return np.sin(2 * np.pi * x)

    np.random.seed(42)

    # 在不同训练集上训练相同模型
    n_datasets = 100
    n_test = 1000
    degrees = [1, 3, 10]

    x_test = np.linspace(0, 1, n_test)
    y_test = true_function(x_test) + np.random.randn(n_test) * 0.1

    print(f"\n{'Degree':<8} {'Bias²':<15} {'Variance':<15} {'Noise':<15} {'Total':<15}")
    print("-" * 70)

    for deg in degrees:
        predictions_all = []

        for _ in range(n_datasets):
            # 生成新训练集
            X_train = np.sort(np.random.rand(20))
            y_train = true_function(X_train) + np.random.randn(20) * 0.2

            # 训练模型
            poly = PolynomialFeatures(degree=deg)
            X_train_poly = poly.transform(X_train)
            model = RidgeRegression(alpha=0.1)
            model.fit(X_train_poly, y_train)

            # 预测
            X_test_poly = poly.transform(x_test.reshape(-1, 1))
            pred = model.predict(X_test_poly)
            predictions_all.append(pred)

        predictions_all = np.array(predictions_all)

        # 计算偏差²和方差
        mean_pred = predictions_all.mean(axis=0)
        bias_squared = np.mean((mean_pred - y_test) ** 2)
        variance = np.mean(np.var(predictions_all, axis=0))
        noise = 0.1 ** 2  # 已知噪声方差

        total = bias_squared + variance + noise

        print(f"{deg:<8} {bias_squared:<15.4f} {variance:<15.4f} {noise:<15.4f} {total:<15.4f}")

    print(f"\n观察：")
    print(f"  - 低阶多项式：高偏差、低方差（欠拟合）")
    print(f"  - 高阶多项式：低偏差、高方差（过拟合）")
    print(f"  - 最优模型在偏差²和方差之间取得平衡")


def early_stopping_demo():
    """演示早停法防止过拟合。"""
    print("\n" + "=" * 60)
    print("早停法（Early Stopping）演示")
    print("=" * 60)

    # 生成数据
    X, y = generate_data(n_samples=100, noise=2.0)
    X_train, X_val, y_train, y_val = train_val_split(X, y, val_ratio=0.3)

    poly = PolynomialFeatures(degree=10)
    X_train_poly = poly.transform(X_train)
    X_val_poly = poly.transform(X_val)

    # 训练并记录每轮误差
    max_epochs = 500
    train_losses = []
    val_losses = []

    # 使用较小的正则化 + 梯度下降模拟
    from sklearn.linear_model import SGDRegressor

    model = SGDRegressor(
        penalty='l2',
        alpha=0.001,
        learning_rate='constant',
        eta0=0.01,
        random_state=42,
        warm_start=True
    )

    best_val_loss = float('inf')
    best_epoch = 0
    patience = 20
    wait = 0

    print(f"\n{'Epoch':<8} {'Train Loss':<15} {'Val Loss':<15} {'Best Epoch':<15}")
    print("-" * 55)

    for epoch in range(1, max_epochs + 1):
        model.fit(X_train_poly, y_train)

        train_pred = model.predict(X_train_poly)
        val_pred = model.predict(X_val_poly)

        train_loss = compute_mse(y_train, train_pred)
        val_loss = compute_mse(y_val, val_pred)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        # 早停检查
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            wait = 0
        else:
            wait += 1

        if epoch % 100 == 0 or wait == patience:
            print(f"{epoch:<8} {train_loss:<15.4f} {val_loss:<15.4f} {best_epoch:<15}")

        if wait >= patience:
            print(f"\n早停触发！最佳 epoch: {best_epoch}, 验证损失: {best_val_loss:.4f}")
            break


if __name__ == "__main__":
    demonstrate_overfitting()
    demonstrate_regularization()
    demonstrate_bias_variance()
    early_stopping_demo()
