"""批归一化（Batch Normalization）完整实现：前向传播、反向传播与训练/推理对比。

Related node: ml_batchnorm
Source IDs: book_deep_learning_ai, book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np


class BatchNorm1d:
    """
    一维批归一化层。

    训练时：使用当前 batch 的均值和方差，并更新 running 均值和方差。
    推理时：使用训练时累积的 running 均值和方差。
    """

    def __init__(self, num_features: int, momentum: float = 0.9, eps: float = 1e-5):
        """
        Args:
            num_features: 特征维度（即神经元数量）
            momentum: 滑动平均动量
            eps: 防止除零的小常数
        """
        self.num_features = num_features
        self.momentum = momentum
        self.eps = eps

        # 可学习参数
        self.gamma = np.ones(num_features)  # scale
        self.beta = np.zeros(num_features)  # shift

        # Running 统计量（用于推理）
        self.running_mean = np.zeros(num_features)
        self.running_var = np.ones(num_features)

        # 训练/推理模式
        self.training = True

    def forward(self, X: np.ndarray, training: bool = True) -> np.ndarray:
        """
        前向传播。

        Args:
            X: 输入，形状为 (batch_size, num_features)
            training: 是否在训练模式

        Returns:
            归一化后的输出
        """
        self.training = training
        self.X = X  # 保存用于反向传播

        if training:
            # 计算当前 batch 的均值和方差
            self.batch_mean = X.mean(axis=0)
            self.batch_var = X.var(axis=0)

            # 更新 running 统计量
            self.running_mean = self.momentum * self.running_mean + (1 - self.momentum) * self.batch_mean
            self.running_var = self.momentum * self.running_var + (1 - self.momentum) * self.batch_var
        else:
            # 推理时使用 running 统计量
            self.batch_mean = self.running_mean
            self.batch_var = self.running_var

        # 归一化
        self.X_norm = (X - self.batch_mean) / np.sqrt(self.batch_var + self.eps)

        # 缩放和平移
        output = self.gamma * self.X_norm + self.beta

        return output

    def backward(self, dout: np.ndarray) -> np.ndarray:
        """
        反向传播。

        Args:
            dout: 上游梯度，形状为 (batch_size, num_features)

        Returns:
            输入的梯度
        """
        m = dout.shape[0]

        # 计算 gamma 和 beta 的梯度
        dgamma = (dout * self.X_norm).sum(axis=0)
        dbeta = dout.sum(axis=0)

        # 计算输入梯度的核心部分
        dx_norm = dout * self.gamma

        # 方差梯度和均值梯度
        dvar = (-0.5 * (dx_norm * (self.X - self.batch_mean)).sum(axis=0)) / \
               (self.batch_var + self.eps) ** 1.5

        dmean = -dx_norm.sum(axis=0) / np.sqrt(self.batch_var + self.eps) - \
                2 * dvar * (self.X - self.batch_mean).sum(axis=0) / m

        # 最终输入梯度
        dx = dx_norm / np.sqrt(self.batch_var + self.eps) + \
             dvar * 2 * (self.X - self.batch_mean) / m + \
             dmean / m

        return dx


class BatchNorm2d:
    """
    二维批归一化层（适用于卷积神经网络的特征图）。

    对 (batch_size, height, width, channels) 的张量，
    在 channels 维度上做归一化。
    """

    def __init__(self, num_channels: int, momentum: float = 0.9, eps: float = 1e-5):
        self.num_channels = num_channels
        self.momentum = momentum
        self.eps = eps

        # 可学习参数
        self.gamma = np.ones(num_channels)
        self.beta = np.zeros(num_channels)

        # Running 统计量
        self.running_mean = np.zeros(num_channels)
        self.running_var = np.ones(num_channels)

        self.training = True

    def forward(self, X: np.ndarray, training: bool = True) -> np.ndarray:
        """
        前向传播。

        Args:
            X: 输入，形状为 (batch_size, height, width, channels)

        Returns:
            归一化后的输出
        """
        self.X = X

        if training:
            # 计算每个通道的均值和方差
            # shape: (channels,)
            self.batch_mean = X.mean(axis=(0, 1, 2))
            self.batch_var = X.var(axis=(0, 1, 2))
        else:
            self.batch_mean = self.running_mean
            self.batch_var = self.running_var

        # 更新 running 统计量
        if training:
            self.running_mean = self.momentum * self.running_mean + (1 - self.momentum) * self.batch_mean
            self.running_var = self.momentum * self.running_var + (1 - self.momentum) * self.batch_var

        # 归一化
        X_norm = (X - self.batch_mean) / np.sqrt(self.batch_var + self.eps)

        # 缩放和平移
        output = self.gamma * X_norm + self.beta

        return output


def compare_bn_training_vs_inference():
    """对比 BatchNorm 在训练和推理阶段的行为差异。"""
    print("=" * 60)
    print("BatchNorm 训练 vs 推理 对比")
    print("=" * 60)

    # 创建测试数据（模拟 4 个 batch，每 batch 3 个特征）
    np.random.seed(42)
    X = np.random.randn(100, 3) * 2 + np.array([10, -5, 3])  # 偏移的数据

    bn = BatchNorm1d(num_features=3, momentum=0.9)

    print("\n初始 running 统计量:")
    print(f"  Running mean: {bn.running_mean}")
    print(f"  Running var:  {bn.running_var}")

    # 模拟多个训练 batch
    print("\n训练阶段（5 个 batch）:")
    for i in range(5):
        batch = X[i*20:(i+1)*20]
        output = bn.forward(batch, training=True)
        print(f"  Batch {i+1}: mean={bn.batch_mean.round(3)}, var={bn.batch_var.round(3)}")

    print(f"\n5 个 batch 后的 running 统计量:")
    print(f"  Running mean: {bn.running_mean.round(3)}")
    print(f"  Running var:  {bn.running_var.round(3)}")

    # 推理阶段
    print("\n推理阶段（单个样本）:")
    single_sample = X[0:1]  # shape: (1, 3)
    output = bn.forward(single_sample, training=False)
    print(f"  输入: {single_sample.flatten()}")
    print(f"  Running mean used: {bn.batch_mean}")
    print(f"  Running var used: {bn.batch_var}")
    print(f"  输出: {output.flatten()}")


def visualize_bn_effect():
    """可视化 BatchNorm 对激活分布的影响。"""
    print("\n" + "=" * 60)
    print("BatchNorm 对激活分布的影响")
    print("=" * 60)

    # 模拟没有归一化的深层网络：每层逐渐偏移
    np.random.seed(42)
    layers = []
    activations = []

    x = np.random.randn(1000, 10)

    for i in range(5):
        # 每层权重逐渐增大，模拟内部协变量偏移
        w = np.random.randn(10, 10) * (1 + 0.3 * i)
        b = np.zeros(10) + 0.5 * i
        x = x @ w + b
        activations.append(x.copy())

    print("没有 BatchNorm 时，各层激活分布:")
    for i, act in enumerate(activations):
        print(f"  Layer {i+1}: mean={act.mean():.2f}, std={act.std():.2f}, "
              f"range=[{act.min():.1f}, {act.max():.1f}]")

    # 带 BatchNorm
    print("\n带 BatchNorm 时，各层激活分布:")
    x = np.random.randn(1000, 10)
    for i in range(5):
        w = np.random.randn(10, 10) * (1 + 0.3 * i)
        b = np.zeros(10) + 0.5 * i
        x = x @ w + b

        bn = BatchNorm1d(10)
        x = bn.forward(x, training=True)

        print(f"  Layer {i+1}: mean={bn.batch_mean.mean():.2f}, std={bn.batch_var.mean():.4f}, "
              f"range=[{x.min():.2f}, {x.max():.2f}]")


def gamma_beta_effect():
    """演示 gamma（scale）和 beta（shift）的作用。"""
    print("\n" + "=" * 60)
    print("Gamma 和 Beta 参数的作用")
    print("=" * 60)

    np.random.seed(42)
    X = np.random.randn(100, 5)

    bn = BatchNorm1d(5)

    # 标准 BatchNorm
    output1 = bn.forward(X, training=True)
    print(f"标准归一化: mean={output1.mean():.4f}, std={output1.std():.4f}")

    # 学习恢复原始分布
    bn.gamma = bn.running_var ** 0.5  # gamma = std
    bn.beta = bn.running_mean  # beta = mean
    output2 = bn.forward(X, training=True)
    print(f"gamma=var^0.5, beta=mean: mean={output2.mean():.4f}, std={output2.std():.4f}")

    # 自定义缩放和平移
    bn.gamma = np.array([2.0, 0.5, 1.0, 1.5, 0.8])
    bn.beta = np.array([0.5, -0.5, 0.0, 1.0, -1.0])
    output3 = bn.forward(X, training=True)
    print(f"自定义 gamma=[2,0.5,1,1.5,0.8], beta=[0.5,-0.5,0,1,-1]")
    print(f"  输出: mean={output3.mean():.4f}, std={output3.std():.4f}")


if __name__ == "__main__":
    compare_bn_training_vs_inference()
    visualize_bn_effect()
    gamma_beta_effect()
