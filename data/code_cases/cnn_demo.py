"""卷积神经网络（CNN）核心组件实现：卷积、池化与特征图可视化。

Related node: ml_cnn
Source IDs: book_deep_learning_ai, book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np


def im2col(image: np.ndarray, kernel_size: int, stride: int) -> np.ndarray:
    """
    将图像转换为列形式，方便批量卷积计算。

    Args:
        image: 输入图像，形状为 (height, width, channels)
        kernel_size: 卷积核尺寸
        stride: 步长

    Returns:
        转换后的列矩阵，形状为 (kh*kw*channels, output_h*output_w)
    """
    kh, kw = kernel_size, kernel_size
    c = image.shape[2] if image.ndim == 3 else 1
    h, w = image.shape[:2]

    # 计算输出尺寸
    out_h = (h - kh) // stride + 1
    out_w = (w - kw) // stride + 1

    # 将每个滑动窗口展平为列
    cols = np.zeros((kh * kw * c, out_h * out_w))

    for y in range(out_h):
        for x in range(out_w):
            patch = image[y*stride:y*stride+kh, x*stride:x*stride+kw]
            if c == 1:
                patch = patch.reshape(-1)
            else:
                patch = patch.reshape(-1)
            cols[:, y*out_w + x] = patch

    return cols


def conv2d(image: np.ndarray, kernel: np.ndarray, stride: int = 1, padding: int = 0) -> np.ndarray:
    """
    二维卷积实现（单通道）。

    Args:
        image: 输入图像 (H, W)
        kernel: 卷积核 (KH, KW)
        stride: 步长
        padding: 填充像素数

    Returns:
        卷积输出特征图
    """
    if padding > 0:
        image = np.pad(image, ((padding, padding), (padding, padding)), mode='constant')

    kh, kw = kernel.shape
    h, w = image.shape

    out_h = (h - kh) // stride + 1
    out_w = (w - kw) // stride + 1

    output = np.zeros((out_h, out_w))

    for y in range(0, out_h * stride, stride):
        for x in range(0, out_w * stride, stride):
            region = image[y:y+kh, x:x+kw]
            output[y//stride, x//stride] = np.sum(region * kernel)

    return output


def max_pool2d(image: np.ndarray, pool_size: int = 2, stride: int = 2) -> np.ndarray:
    """
    最大池化实现。

    Args:
        image: 输入特征图
        pool_size: 池化窗口大小
        stride: 步长

    Returns:
        池化后的特征图
    """
    h, w = image.shape
    out_h = (h - pool_size) // stride + 1
    out_w = (w - pool_size) // stride + 1

    output = np.zeros((out_h, out_w))

    for y in range(out_h):
        for x in range(out_w):
            region = image[y*stride:y*stride+pool_size, x*stride:x*stride+pool_size]
            output[y, x] = np.max(region)

    return output


def create_sobel_edge_detector() -> tuple[np.ndarray, np.ndarray]:
    """创建 Sobel 边缘检测卷积核。"""
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
    return sobel_x, sobel_y


class ConvLayer:
    """简化的卷积层：包含权重和偏置。"""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3):
        self.kernel_size = kernel_size
        # Xavier 初始化
        scale = np.sqrt(2.0 / (in_channels * kernel_size * kernel_size))
        self.kernels = np.random.randn(out_channels, in_channels, kernel_size, kernel_size) * scale
        self.bias = np.zeros(out_channels)

    def forward(self, X: np.ndarray) -> np.ndarray:
        """
        前向传播。

        Args:
            X: 输入张量 (batch, height, width, in_channels)

        Returns:
            输出特征图 (batch, out_height, out_width, out_channels)
        """
        batch_size, h, w, _ = X.shape
        out_h = (h - self.kernel_size) // 1 + 1
        out_w = (w - self.kernel_size) // 1 + 1

        output = np.zeros((batch_size, out_h, out_w, self.kernels.shape[0]))

        for b in range(batch_size):
            for oc in range(self.kernels.shape[0]):
                for ic in range(self.kernels.shape[1]):
                    output[b, :, :, oc] += conv2d(X[b, :, :, ic], self.kernels[oc, ic])
                output[b, :, :, oc] += self.bias[oc]
                # ReLU 激活
                output[b, :, :, oc] = np.maximum(0, output[b, :, :, oc])

        return output


class MaxPoolLayer:
    """最大池化层。"""

    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size

    def forward(self, X: np.ndarray) -> np.ndarray:
        """前向传播。"""
        batch_size, h, w, channels = X.shape
        out_h = (h - self.pool_size) // self.pool_size + 1
        out_w = (w - self.pool_size) // self.pool_size + 1

        output = np.zeros((batch_size, out_h, out_w, channels))

        for b in range(batch_size):
            for c in range(channels):
                output[b, :, :, c] = max_pool2d(X[b, :, :, c], self.pool_size, self.pool_size)

        return output


if __name__ == "__main__":
    # 创建测试图像（简单棋盘格）
    image = np.zeros((8, 8), dtype=np.float32)
    image[::2, ::2] = 1.0
    image[1::2, 1::2] = 1.0

    print("原始图像 (8x8 棋盘格):")
    print(image)

    # Sobel 边缘检测
    sobel_x, sobel_y = create_sobel_edge_detector()
    edge_x = conv2d(image, sobel_x)
    edge_y = conv2d(image, sobel_y)
    edge = np.sqrt(edge_x**2 + edge_y**2)

    print("\nSobel X 边缘检测结果:")
    print(edge_x.round(2))

    # 卷积层演示
    print("\n卷积层演示:")
    conv = ConvLayer(in_channels=1, out_channels=2, kernel_size=3)
    X_test = image.reshape(1, 8, 8, 1)
    output = conv.forward(X_test)
    print(f"输入形状: {X_test.shape}")
    print(f"卷积输出形状: {output.shape}")

    # 池化层演示
    pool = MaxPoolLayer(pool_size=2)
    pooled = pool.forward(output)
    print(f"池化后形状: {pooled.shape}")
    print(f"特征图尺寸从 6x6 降为 {pooled.shape[1]}x{pooled.shape[2]}")
