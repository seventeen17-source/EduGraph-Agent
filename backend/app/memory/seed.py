"""种子记忆 —— 为演示学生预填充学习记忆，让记忆 Agent 首次对话即可展现能力。"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.memory.schemas import MasterySignal, MemoryEntry


def seed_memories(student_id: str = "demo_student_001") -> list[MemoryEntry]:
    """生成演示学生的种子记忆（3-5 条）。时间戳设为模拟的过去几天。"""

    now = datetime.utcnow()

    return [
        MemoryEntry(
            id=f"seed_{student_id}_01",
            student_id=student_id,
            conversation_id="demo_conv_001",
            timestamp=now - timedelta(days=3),
            node_ids=["ml_gradient_descent", "ml_loss_function"],
            intent="concept_explain",
            student_question_summary="学生询问梯度下降的直观理解，说看了很多公式还是不太懂",
            agent_response_summary="用下山比喻和等高线图解释了梯度下降的直观含义，补充了学习率的影响",
            key_insight="学生对纯数学推导有抵触，但通过物理类比后理解速度明显加快——视觉型学习者",
            confusion_nodes=["ml_learning_rate"],
            mastery_signals=[
                MasterySignal(
                    node_id="ml_gradient_descent",
                    level="partial",
                    evidence="理解了梯度下降的直观含义，但尚不能推导参数更新公式",
                ).model_dump(),
            ],
            engagement_level="high",
            learning_preference_hint="强烈偏好图解和物理类比，对纯公式讲解容易走神",
            suggested_follow_up="下次可以从学习率调参入手，对比不同学习率的收敛曲线",
            caution_topics=["避免直接用偏导数符号开场，先画图建立直观感受"],
        ),
        MemoryEntry(
            id=f"seed_{student_id}_02",
            student_id=student_id,
            conversation_id="demo_conv_001",
            timestamp=now - timedelta(days=3, hours=2),
            node_ids=["ml_neural_network", "ml_activation_function"],
            intent="concept_explain",
            student_question_summary="学生想理解为什么神经网络需要激活函数，用线性模型不行吗",
            agent_response_summary="用 XOR 问题演示了没有激活函数的多层网络退化为线性模型的本质原因",
            key_insight="学生对'非线性'这个关键概念的理解很到位，但混淆了'线性模型'和'线性代数'",
            confusion_nodes=["ml_linear_model_basics"],
            mastery_signals=[],
            engagement_level="high",
            learning_preference_hint="喜欢看具体的反例和边界情况，对 what-if 问题很感兴趣",
            suggested_follow_up="可以引入不同激活函数的对比（ReLU vs Sigmoid vs Tanh），用代码示例展示",
            caution_topics=["注意区分'线性可分'和'线性变换'，学生可能混用这两个词"],
        ),
        MemoryEntry(
            id=f"seed_{student_id}_03",
            student_id=student_id,
            conversation_id="demo_conv_002",
            timestamp=now - timedelta(days=1),
            node_ids=["ml_backpropagation", "ml_chain_rule"],
            intent="exercise_help",
            student_question_summary="在做反向传播练习题时卡住了——不知道如何计算隐藏层的梯度",
            agent_response_summary="分三步讲解了链式法则在计算图上的应用：前向存值→反向传梯度→更新参数",
            key_insight="学生能正确完成前向传播，但反向推导时漏掉了中间节点的梯度累积——典型的'链式法则断链'问题",
            confusion_nodes=["ml_chain_rule"],
            mastery_signals=[
                MasterySignal(
                    node_id="ml_chain_rule",
                    level="partial",
                    evidence="理解单变量链式法则但不会拓展到矩阵/向量形式",
                ).model_dump(),
            ],
            engagement_level="medium",
            learning_preference_hint="对计算图的结构化表达反应很好，建议后续资源以计算图为基础",
            suggested_follow_up="准备一个从简单到复杂的计算图梯度推导练习序列",
            caution_topics=[
                "在讲反向传播前先确保链式法则的矩阵形式被理解了",
                "梯度累积部分需要多次强调——这是常见错误点",
            ],
        ),
        MemoryEntry(
            id=f"seed_{student_id}_04",
            student_id=student_id,
            conversation_id="demo_conv_002",
            timestamp=now - timedelta(days=1, hours=3),
            node_ids=["ml_overfitting_underfitting", "ml_regularization"],
            intent="resource_generate",
            student_question_summary="学生请求生成过拟合和正则化的学习资源，因为项目模型在验证集上表现很差",
            agent_response_summary="生成了 L1/L2 正则化的图解对比、过拟合检测的代码示例和交叉验证的数据划分示例",
            key_insight="学生能识别验证集性能下降→过拟合，但首次听说 L1 正则化可以做特征选择",
            confusion_nodes=["ml_feature_selection"],
            mastery_signals=[
                MasterySignal(
                    node_id="ml_overfitting_underfitting",
                    level="solid",
                    evidence="能独立判断自己的模型过拟合，并主动寻求正则化方法",
                ).model_dump(),
            ],
            engagement_level="high",
            learning_preference_hint="学以致用型——有实际项目驱动时学习效率最高，偏好可直接运行的代码案例",
            suggested_follow_up="可以引导学生把 L2 正则化加入项目，对比训练/验证曲线",
            caution_topics=[
                "学生可能低估了数据集划分的影响——只关注正则化可能治标不治本",
            ],
        ),
        MemoryEntry(
            id=f"seed_{student_id}_05",
            student_id=student_id,
            conversation_id="demo_conv_003",
            timestamp=now - timedelta(hours=12),
            node_ids=["ml_cross_validation", "ml_evaluation_methods"],
            intent="general_learning_chat",
            student_question_summary="学生说觉得自己学了很多概念但不知道掌握得怎么样，想评估一下",
            agent_response_summary="引导学生通过练习来诊断掌握度，建议优先验证几个核心概念：梯度下降→反向传播→过拟合→正则化",
            key_insight="学生的元认知意识很强——能感知到自己'知其然不知其所以然'，主动寻求诊断而非被动学习",
            confusion_nodes=[],
            mastery_signals=[],
            engagement_level="medium",
            learning_preference_hint="有自我评估意识，适合用间隔测试来巩固长期记忆",
            suggested_follow_up="准备一套涵盖梯度下降→反向传播→正则化的综合诊断练习",
            caution_topics=[
                "学生在概念间的连接处（如'梯度下降优化目标'和'正则化约束项'的关系）需要加强引导",
            ],
        ),
    ]
