"""机器学习评估指标完整实现：混淆矩阵、精确率、召回率、F1、AUC、ROC。

Related node: ml_evaluation_methods
Source IDs: book_zhou_ml, book_hands_on_ml_3e_zh
"""

from __future__ import annotations

import numpy as np
from typing import NamedTuple


class ConfusionMatrix(NamedTuple):
    """混淆矩阵的四个基本元素。"""
    tp: int  # True Positive
    tn: int  # True Negative
    fp: int  # False Positive
    fn: int  # False Negative


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> ConfusionMatrix:
    """
    计算二分类混淆矩阵。

    Args:
        y_true: 真实标签
        y_pred: 预测标签

    Returns:
        ConfusionMatrix 对象
    """
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    return ConfusionMatrix(tp=tp, tn=tn, fp=fp, fn=fn)


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """准确率：正确预测占总样本的比例。"""
    cm = confusion_matrix(y_true, y_pred)
    total = cm.tp + cm.tn + cm.fp + cm.fn
    return (cm.tp + cm.tn) / total if total > 0 else 0.0


def precision(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    精确率（查准率）：预测为正类中真正为正的比例。
    关注「预测为正的有多少是对的」。
    """
    cm = confusion_matrix(y_true, y_pred)
    return cm.tp / (cm.tp + cm.fp) if (cm.tp + cm.fp) > 0 else 0.0


def recall(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    召回率（查全率）：所有正类中被正确预测的比例。
    关注「所有正类中找出了多少」。
    """
    cm = confusion_matrix(y_true, y_pred)
    return cm.tp / (cm.tp + cm.fn) if (cm.tp + cm.fn) > 0 else 0.0


def f1_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """F1 分数：精确率和召回率的调和平均。"""
    p = precision(y_true, y_pred)
    r = recall(y_true, y_pred)
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def specificity(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """特异度：所有负类中被正确预测的比例。"""
    cm = confusion_matrix(y_true, y_pred)
    return cm.tn / (cm.tn + cm.fp) if (cm.tn + cm.fp) > 0 else 0.0


def fpr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """假阳性率（FPR）：所有负类中被错误预测为正的比例。"""
    return 1 - specificity(y_true, y_pred)


def tpr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """真阳性率（TPR）：与召回率相同。"""
    return recall(y_true, y_pred)


def roc_curve(y_true: np.ndarray, y_scores: np.ndarray, num_thresholds: int = 100) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    计算 ROC 曲线。

    Args:
        y_true: 真实标签 (0 或 1)
        y_scores: 预测概率分数
        num_thresholds: 阈值数量

    Returns:
        (fprs, tprs, thresholds)
    """
    thresholds = np.linspace(y_scores.min(), y_scores.max(), num_thresholds)
    fprs = np.zeros(num_thresholds)
    tprs = np.zeros(num_thresholds)

    for i, thresh in enumerate(thresholds):
        y_pred = (y_scores >= thresh).astype(int)
        fprs[i] = fpr(y_true, y_pred)
        tprs[i] = tpr(y_true, y_pred)

    return fprs, tprs, thresholds


def auc(fprs: np.ndarray, tprs: np.ndarray) -> float:
    """
    计算 AUC（ROC 曲线下面积）。

    使用梯形法则近似积分。
    """
    # 按 FPR 排序
    sorted_indices = np.argsort(fprs)
    fprs_sorted = fprs[sorted_indices]
    tprs_sorted = tprs[sorted_indices]

    # 梯形法则
    auc_value = np.trapz(tprs_sorted, fprs_sorted)
    return auc_value


def roc_auc_score(y_true: np.ndarray, y_scores: np.ndarray) -> float:
    """直接计算 AUC。"""
    fprs, tprs, _ = roc_curve(y_true, y_scores)
    return auc(fprs, tprs)


def precision_recall_curve(y_true: np.ndarray, y_scores: np.ndarray, num_thresholds: int = 100) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """计算 Precision-Recall 曲线。"""
    thresholds = np.linspace(y_scores.min(), y_scores.max(), num_thresholds)
    precisions = np.zeros(num_thresholds)
    recalls = np.zeros(num_thresholds)

    for i, thresh in enumerate(thresholds):
        y_pred = (y_scores >= thresh).astype(int)
        precisions[i] = precision(y_true, y_pred)
        recalls[i] = recall(y_true, y_pred)

    return precisions, recalls, thresholds


def average_precision(y_true: np.ndarray, y_scores: np.ndarray) -> float:
    """计算平均精度（PR 曲线下面积）。"""
    precisions, recalls, _ = precision_recall_curve(y_true, y_scores)
    # 从高召回到低召回排序（通常 PR 曲线按此顺序）
    sorted_indices = np.argsort(recalls)[::-1]
    return np.trapz(precisions[sorted_indices], recalls[sorted_indices])


def confusion_matrix_visual(cm: ConfusionMatrix) -> str:
    """生成混淆矩阵的文本可视化。"""
    total = cm.tp + cm.tn + cm.fp + cm.fn
    width = max(len(str(total)), 10)

    def fmt(n):
        return str(n).rjust(width)

    lines = [
        "",
        "混淆矩阵：",
        f"              预测 Positive  预测 Negative",
        f"真实 Positive      {fmt(cm.tp)}          {fmt(cm.fn)}",
        f"真实 Negative      {fmt(cm.fp)}          {fmt(cm.tn)}",
        "",
    ]
    return "\n".join(lines)


def multiclass_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """多分类准确率。"""
    return np.mean(y_true == y_pred)


def macro_precision(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """宏精确率：每个类别的精确率求平均。"""
    classes = np.unique(y_true)
    precisions = []

    for c in classes:
        y_true_binary = (y_true == c).astype(int)
        y_pred_binary = (y_pred == c).astype(int)
        precisions.append(precision(y_true_binary, y_pred_binary))

    return np.mean(precisions)


def micro_precision(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """微精确率：汇总所有 TP、FP、FN 后计算。"""
    classes = np.unique(y_true)
    total_tp = 0
    total_fp = 0

    for c in classes:
        y_true_binary = (y_true == c).astype(int)
        y_pred_binary = (y_pred == c).astype(int)
        cm = confusion_matrix(y_true_binary, y_pred_binary)
        total_tp += cm.tp
        total_fp += cm.fp

    return total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """平均绝对误差（MAE）。"""
    return np.mean(np.abs(y_true - y_pred))


def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """均方误差（MSE）。"""
    return np.mean((y_true - y_pred) ** 2)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """均方根误差（RMSE）。"""
    return np.sqrt(mse(y_true, y_pred))


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """R² 决定系数。"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else 0.0


if __name__ == "__main__":
    print("=" * 60)
    print("评估指标演示")
    print("=" * 60)

    # 示例 1：癌症检测
    print("\n示例 1：癌症检测（类别不平衡）")
    print("-" * 40)

    # 1000 个样本，1% 是癌症
    np.random.seed(42)
    n_samples = 1000
    y_true = np.array([1] * 10 + [0] * 990)  # 10 个癌症，990 个正常
    np.random.shuffle(y_true)

    # 模型预测：识别出 8 个癌症，误报了 50 个正常人
    y_pred = y_true.copy()
    # 把 2 个癌症漏检
    cancer_indices = np.where(y_true == 1)[0]
    y_pred[cancer_indices[0]] = 0
    y_pred[cancer_indices[1]] = 0
    # 误报 50 个正常人
    normal_indices = np.where(y_true == 0)[0]
    y_pred[normal_indices[:50]] = 1

    cm = confusion_matrix(y_true, y_pred)
    print(confusion_matrix_visual(cm))
    print(f"准确率:   {accuracy(y_true, y_pred):.2%}")
    print(f"精确率:   {precision(y_true, y_pred):.2%}")
    print(f"召回率:   {recall(y_true, y_pred):.2%}")
    print(f"F1 分数:  {f1_score(y_true, y_pred):.2%}")
    print(f"\n分析：准确率高但召回率低！说明模型漏检了 2 个癌症患者。")

    # 示例 2：ROC 和 AUC
    print("\n" + "=" * 60)
    print("示例 2：ROC 曲线和 AUC")
    print("-" * 40)

    # 生成模拟预测分数
    y_true = np.array([1] * 50 + [0] * 50)
    y_scores = np.concatenate([
        np.random.uniform(0.5, 1.0, 50),  # 正类分数较高
        np.random.uniform(0.0, 0.6, 50)   # 负类分数较低
    ])
    np.random.shuffle(y_true)
    np.random.seed(42)
    y_scores_shuffled = np.concatenate([
        np.random.uniform(0.5, 1.0, 50),
        np.random.uniform(0.0, 0.6, 50)
    ])

    auc_value = roc_auc_score(y_true, y_scores_shuffled)
    print(f"AUC: {auc_value:.4f}")
    print(f"AUC = 1.0 表示完美分类")
    print(f"AUC = 0.5 表示随机猜测")

    # 示例 3：回归指标
    print("\n" + "=" * 60)
    print("示例 3：回归任务评估指标")
    print("-" * 40)

    y_true_reg = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y_pred_reg = np.array([1.1, 1.9, 3.2, 3.8, 5.1])

    print(f"真实值:  {y_true_reg}")
    print(f"预测值:  {y_pred_reg}")
    print(f"MAE:     {mae(y_true_reg, y_pred_reg):.4f}")
    print(f"MSE:     {mse(y_true_reg, y_pred_reg):.4f}")
    print(f"RMSE:    {rmse(y_true_reg, y_pred_reg):.4f}")
    print(f"R²:      {r2_score(y_true_reg, y_pred_reg):.4f}")

    # 示例 4：多分类指标
    print("\n" + "=" * 60)
    print("示例 4：多分类指标")
    print("-" * 40)

    y_true_multi = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 2])
    y_pred_multi = np.array([0, 1, 1, 0, 2, 2, 0, 1, 2, 2])

    print(f"准确率:     {multiclass_accuracy(y_true_multi, y_pred_multi):.2%}")
    print(f"宏精确率:   {macro_precision(y_true_multi, y_pred_multi):.2%}")
    print(f"微精确率:   {micro_precision(y_true_multi, y_pred_multi):.2%}")
