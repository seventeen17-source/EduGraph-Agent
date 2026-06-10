import json
from pathlib import Path

root = Path(r"d:/Code/EduGraph-Agent")
kp_path = root / "data/course/knowledge_points.json"
items = json.loads(kp_path.read_text(encoding="utf-8"))

node_type_map = {
    "ml_basic_terms": "foundation",
    "ml_supervised_unsupervised": "concept",
    "ml_dataset_split": "evaluation",
    "ml_generalization": "evaluation",
    "ml_overfitting_underfitting": "evaluation",
    "ml_evaluation_methods": "evaluation",
    "ml_performance_metrics": "evaluation",
    "ml_bias_variance": "theory",
    "ml_linear_algebra_basic": "foundation",
    "ml_probability_statistics_basic": "foundation",
    "ml_calculus_optimization_basic": "foundation",
    "ml_loss_function": "concept",
    "ml_gradient_optimization_basic": "method",
    "ml_linear_regression": "model",
    "ml_logistic_regression": "model",
    "ml_linear_discriminant_analysis": "model",
    "ml_gradient_descent": "method",
    "ml_sgd_minibatch": "method",
    "ml_decision_tree": "model",
    "ml_svm": "model",
    "ml_bayesian_classifier": "model",
    "ml_ensemble_learning": "method",
    "ml_random_forest": "model",
    "ml_clustering": "concept",
    "ml_kmeans": "model",
    "ml_dimensionality_reduction": "method",
    "ml_metric_learning": "method",
    "ml_feature_selection": "method",
    "ml_sparse_learning": "method",
    "ml_regularization": "training_technique",
    "ml_perceptron": "model",
    "ml_multilayer_neural_network": "model",
    "ml_activation_function": "training_technique",
    "ml_backpropagation": "method",
    "ml_dropout": "training_technique",
    "ml_batchnorm": "training_technique",
    "ml_cnn": "model",
    "ml_rnn": "model",
    "ml_lstm": "model",
    "ml_attention_mechanism": "method",
    "ml_transformer": "model",
    "ml_pac_learning": "theory",
    "ml_vc_dimension": "theory",
    "ml_semi_supervised_learning": "method",
    "ml_bayesian_network": "model",
    "ml_markov_network": "model",
    "ml_rule_learning": "method",
    "ml_reinforcement_learning": "concept",
    "ml_mdp": "theory",
    "ml_q_learning": "method"
}

role_map = {
    "ml_basic_terms": "entry",
    "ml_supervised_unsupervised": "entry",
    "ml_dataset_split": "entry",
    "ml_generalization": "bridge",
    "ml_overfitting_underfitting": "core",
    "ml_evaluation_methods": "bridge",
    "ml_performance_metrics": "bridge",
    "ml_bias_variance": "advanced",
    "ml_linear_algebra_basic": "entry",
    "ml_probability_statistics_basic": "entry",
    "ml_calculus_optimization_basic": "entry",
    "ml_loss_function": "bridge",
    "ml_gradient_optimization_basic": "bridge",
    "ml_linear_regression": "core",
    "ml_logistic_regression": "core",
    "ml_linear_discriminant_analysis": "support",
    "ml_gradient_descent": "core",
    "ml_sgd_minibatch": "core",
    "ml_decision_tree": "core",
    "ml_svm": "advanced",
    "ml_bayesian_classifier": "support",
    "ml_ensemble_learning": "support",
    "ml_random_forest": "support",
    "ml_clustering": "core",
    "ml_kmeans": "core",
    "ml_dimensionality_reduction": "support",
    "ml_metric_learning": "advanced",
    "ml_feature_selection": "support",
    "ml_sparse_learning": "advanced",
    "ml_regularization": "bridge",
    "ml_perceptron": "entry",
    "ml_multilayer_neural_network": "core",
    "ml_activation_function": "bridge",
    "ml_backpropagation": "core",
    "ml_dropout": "support",
    "ml_batchnorm": "support",
    "ml_cnn": "support",
    "ml_rnn": "support",
    "ml_lstm": "advanced",
    "ml_attention_mechanism": "bridge",
    "ml_transformer": "advanced",
    "ml_pac_learning": "extension",
    "ml_vc_dimension": "extension",
    "ml_semi_supervised_learning": "extension",
    "ml_bayesian_network": "extension",
    "ml_markov_network": "extension",
    "ml_rule_learning": "extension",
    "ml_reinforcement_learning": "extension",
    "ml_mdp": "extension",
    "ml_q_learning": "extension"
}

recommended = {
    "foundation": ["document", "diagram", "exercise"],
    "concept": ["document", "diagram", "exercise", "video_script"],
    "evaluation": ["document", "diagram", "exercise"],
    "method": ["document", "diagram", "exercise", "code_case", "video_script"],
    "model": ["document", "diagram", "exercise", "code_case"],
    "training_technique": ["document", "diagram", "exercise", "code_case"],
    "theory": ["document", "diagram", "exercise"]
}

aliases = {
    "ml_basic_terms": ["ML 基本术语", "机器学习术语"],
    "ml_supervised_unsupervised": ["有监督学习与无监督学习", "监督 vs 无监督"],
    "ml_dataset_split": ["数据集划分", "训练验证测试划分"],
    "ml_generalization": ["泛化", "generalization"],
    "ml_overfitting_underfitting": ["过拟合欠拟合", "overfitting and underfitting"],
    "ml_evaluation_methods": ["模型验证方法", "交叉验证方法"],
    "ml_performance_metrics": ["评估指标", "metrics"],
    "ml_bias_variance": ["偏差方差权衡", "bias-variance tradeoff"],
    "ml_linear_algebra_basic": ["线性代数", "矩阵基础"],
    "ml_probability_statistics_basic": ["概率统计基础", "概率论基础"],
    "ml_calculus_optimization_basic": ["微积分基础", "优化基础"],
    "ml_loss_function": ["目标函数", "损失"],
    "ml_gradient_optimization_basic": ["梯度优化基础", "gradient basics"],
    "ml_linear_regression": ["Linear Regression", "线回归"],
    "ml_logistic_regression": ["Logistic Regression", "LR 分类"],
    "ml_linear_discriminant_analysis": ["LDA", "Linear Discriminant Analysis"],
    "ml_gradient_descent": ["GD", "Gradient Descent", "梯度法"],
    "ml_sgd_minibatch": ["SGD", "Mini-batch SGD", "随机梯度下降"],
    "ml_decision_tree": ["Decision Tree", "树模型"],
    "ml_svm": ["Support Vector Machine", "支持向量机分类"],
    "ml_bayesian_classifier": ["朴素贝叶斯", "Naive Bayes"],
    "ml_ensemble_learning": ["集成方法", "Ensemble Methods"],
    "ml_random_forest": ["Random Forest", "RF"],
    "ml_clustering": ["聚类分析", "clustering"],
    "ml_kmeans": ["K-Means 聚类", "kmeans"],
    "ml_dimensionality_reduction": ["降维方法", "PCA/降维"],
    "ml_metric_learning": ["距离度量学习", "metric learning"],
    "ml_feature_selection": ["特征筛选", "feature selection"],
    "ml_sparse_learning": ["稀疏表示学习", "sparse learning"],
    "ml_regularization": ["正则项", "L1/L2 正则化"],
    "ml_perceptron": ["Perceptron", "单层感知机"],
    "ml_multilayer_neural_network": ["MLP", "多层感知机"],
    "ml_activation_function": ["非线性激活函数", "activation"],
    "ml_backpropagation": ["BP", "Backpropagation", "反向传播算法"],
    "ml_dropout": ["神经元随机失活", "dropout regularization"],
    "ml_batchnorm": ["BN", "Batch Normalization"],
    "ml_cnn": ["卷积神经网络", "Convolutional Neural Network"],
    "ml_rnn": ["循环神经网络", "Recurrent Neural Network"],
    "ml_lstm": ["长短期记忆网络", "Long Short-Term Memory"],
    "ml_attention_mechanism": ["Attention", "注意力"],
    "ml_transformer": ["自注意力模型", "Transformer 架构"],
    "ml_pac_learning": ["PAC", "Probably Approximately Correct"],
    "ml_vc_dimension": ["VC 维度", "VC dimension"],
    "ml_semi_supervised_learning": ["半监督方法", "semi-supervised"],
    "ml_bayesian_network": ["Bayesian Network", "贝叶斯网络"],
    "ml_markov_network": ["Markov Network", "马尔可夫随机场"],
    "ml_rule_learning": ["基于规则学习", "rule-based learning"],
    "ml_reinforcement_learning": ["RL", "Reinforcement Learning"],
    "ml_mdp": ["Markov Decision Process", "MDP"],
    "ml_q_learning": ["Q Learning", "Q 值学习"]
}

common_queries = {
    "ml_gradient_descent": ["梯度下降是什么", "为什么沿负梯度方向更新", "学习率太大会怎么样", "GD 和 SGD 有什么区别"],
    "ml_logistic_regression": ["逻辑回归为什么能做分类", "逻辑回归和线性回归有什么区别", "为什么叫回归却做分类"],
    "ml_loss_function": ["损失函数是什么", "目标函数和损失函数有什么区别", "为什么训练要最小化损失"],
    "ml_backpropagation": ["反向传播怎么理解", "反向传播和梯度下降是什么关系", "BP 为什么能训练神经网络"],
    "ml_attention_mechanism": ["注意力机制是什么", "QKV 是什么意思", "为什么注意力比 RNN 更强"],
    "ml_transformer": ["Transformer 为什么这么重要", "自注意力怎么工作", "Transformer 和 RNN 有什么区别"],
    "ml_overfitting_underfitting": ["怎么判断过拟合", "欠拟合是什么意思", "过拟合怎么解决"],
    "ml_regularization": ["L1 和 L2 有什么区别", "正则化为什么能防过拟合"],
    "ml_kmeans": ["K-Means 怎么迭代", "K 值怎么选", "K-Means 为什么会局部最优"],
    "ml_svm": ["SVM 为什么最大间隔", "核函数有什么用"],
    "ml_performance_metrics": ["准确率和召回率怎么选", "AUC 是什么", "F1 为什么重要"],
    "ml_dataset_split": ["为什么要验证集", "训练集和测试集有什么区别"],
    "ml_cnn": ["卷积层在做什么", "池化层为什么有用"],
    "ml_rnn": ["RNN 为什么适合序列", "RNN 为什么梯度消失"],
    "ml_lstm": ["LSTM 比 RNN 强在哪", "门控机制怎么理解"]
}

misconceptions = {
    "ml_gradient_descent": ["学习率越大收敛越快", "梯度下降总能找到全局最优"],
    "ml_logistic_regression": ["逻辑回归是回归任务而不是分类任务", "逻辑回归必须使用线性可分数据"],
    "ml_overfitting_underfitting": ["训练集准确率高就说明模型一定好", "欠拟合只和数据量少有关"],
    "ml_regularization": ["正则化只会让模型变差", "L1 和 L2 只是名字不同"],
    "ml_backpropagation": ["反向传播就是梯度下降", "反向传播只能用于很深的网络"],
    "ml_batchnorm": ["BatchNorm 就是正则化", "BatchNorm 只在推理阶段起作用"],
    "ml_dropout": ["Dropout 在测试时也要随机丢弃神经元", "Dropout 可以替代所有正则化方法"],
    "ml_kmeans": ["K-Means 一定能找到真实簇", "K 值随便设都一样"],
    "ml_svm": ["核函数越复杂越好", "支持向量机只适合小数据集"],
    "ml_attention_mechanism": ["注意力机制不需要任何位置关系信息"],
    "ml_transformer": ["Transformer 不需要训练数据就能工作", "Transformer 一定比所有 RNN 更适合任何任务"]
}

mastery = {
    "ml_gradient_descent": ["能解释梯度下降的参数更新公式", "能比较 GD、SGD 和 Mini-batch 的差异", "能通过代码观察学习率对收敛过程的影响"],
    "ml_logistic_regression": ["能解释逻辑回归用于分类的原因", "能说明 Sigmoid/Softmax 与概率输出的关系", "能判断逻辑回归适合的任务类型"],
    "ml_loss_function": ["能区分损失函数与评估指标", "能解释为什么训练过程要最小化损失"],
    "ml_backpropagation": ["能说明反向传播如何利用链式法则计算梯度", "能解释反向传播与参数更新的关系"],
    "ml_attention_mechanism": ["能解释 Q、K、V 的基本作用", "能说明注意力为何有助于长程依赖建模"],
    "ml_transformer": ["能概述 Transformer 的核心组成部分", "能说明自注意力和位置编码的作用"],
    "ml_overfitting_underfitting": ["能根据训练/验证表现判断过拟合或欠拟合", "能提出至少两种缓解过拟合的方法"],
    "ml_regularization": ["能比较 L1 与 L2 的差异", "能解释正则化如何影响模型复杂度"],
    "ml_kmeans": ["能描述 K-Means 的迭代过程", "能解释初始中心和 K 值对结果的影响"],
    "ml_performance_metrics": ["能根据任务选择合适指标", "能解释准确率、召回率、F1 和 AUC 的区别"]
}

for item in items:
    nid = item["node_id"]
    ntype = node_type_map[nid]
    item["aliases"] = aliases.get(nid, [])
    item["node_type"] = ntype
    item["role_in_path"] = role_map[nid]
    item["recommended_resource_types"] = recommended[ntype]
    item["common_queries"] = common_queries.get(nid, [])
    item["common_misconceptions"] = misconceptions.get(nid, [])
    item["mastery_objectives"] = mastery.get(nid, [])
    item["doc_chunk_ids"] = []
    item["exercise_ids"] = []
    item["code_case_ids"] = []

kp_path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("knowledge_points.json upgraded")
