# 机器学习课程知识库收集指南

## 1. 指南目标

本指南用于指导 EduGraph-Agent 项目的机器学习课程知识库收集工作，目标不是做一个大而全的课程资料仓库，而是构建一个**可用于知识图谱、GraphRAG、资源生成、学习路径规划和学习效果评估**的结构化课程知识库。

知识库需要同时服务以下 5 个能力：

1. 课程知识图谱构建
2. GraphRAG 检索增强
3. 多智能体资源生成
4. 个性化学习路径规划
5. 智能辅导与学习效果评估

因此，收集的数据必须既能支撑检索，又能支撑结构化建模。

---

## 2. 收集原则

### 2.1 先闭环，后扩展

优先收集能够打通比赛演示主线的数据，不追求一开始就覆盖整门课程所有细节。

优先顺序：

1. 知识点骨架
2. 讲义类文本
3. 练习题与答案
4. 代码案例
5. 常见问题与误区
6. 拓展阅读

### 2.2 先结构化，后大规模

先确定知识点、章节、关系和字段格式，再大量收集资料。否则后续很难挂载到知识图谱和向量库。

### 2.3 先可解释，后自动化

初赛版本优先使用人工整理或半自动整理的数据，保证图谱关系、引用来源和资源挂载过程可解释。

### 2.4 一切围绕演示场景

比赛版本的核心演示对象是一个机器学习基础薄弱、偏好图解和代码的学生，因此优先收集以下主题：

- 监督学习与无监督学习
- 线性回归
- 逻辑回归
- 梯度下降
- 随机梯度下降与 Mini-batch
- 过拟合与正则化
- 感知机
- 多层神经网络
- 激活函数
- 反向传播
- CNN
- Transformer / 注意力机制

---

## 3. 知识库需要的数据类型

知识库至少需要 6 类数据。

## 3.1 课程元数据

用于描述整门课程的基本信息。

建议字段：

```json
{
  "course_id": "ml_course",
  "name": "机器学习",
  "description": "面向本科阶段的机器学习课程知识库",
  "target_audience": "计算机相关专业本科生",
  "difficulty_range": "1-5",
  "chapters": 6
}
```

## 3.2 章节数据

用于组织课程结构。

建议字段：

```json
{
  "chapter_id": "ch03",
  "course_id": "ml_course",
  "title": "线性模型与梯度优化",
  "order": 3,
  "priority": "P0",
  "difficulty": 3,
  "estimated_hours": 5,
  "summary": "对应《机器学习》线性模型，并结合梯度下降、随机梯度下降与 Mini-batch，作为比赛演示主线。",
  "learning_objectives": [
    "理解线性回归和逻辑回归的基本思想",
    "掌握损失函数、梯度下降和参数更新的关系",
    "能够使用代码演示梯度下降的收敛过程"
  ],
  "key_node_ids": ["ml_linear_regression", "ml_gradient_descent", "ml_sgd_minibatch"],
  "prerequisite_chapter_ids": ["ch02"],
  "doc_file": "data/docs/ch03_linear_models_optimization.md",
  "source_ids": ["book_zhou_ml", "course_stanford_cs229"],
  "recommended_resource_types": ["document", "diagram", "exercise", "video_script", "code_case"],
  "assessment_focus": ["concept", "calculation", "coding", "application"],
  "demo_usage": "main_flow",
  "collection_status": "skeleton",
  "tags": ["linear-model", "gradient-descent", "optimization", "demo-core", "p0"]
}
```

字段用途：

| 字段 | 说明 |
| --- | --- |
| `chapter_id` | 章节稳定 ID，用于知识点和图谱边挂载。 |
| `course_id` | 所属课程 ID，为后续多课程扩展预留。 |
| `title` | 章节标题。 |
| `order` | 章节顺序。 |
| `priority` | 收集与开发优先级，使用 `P0 / P1 / P2`。 |
| `difficulty` | 章节整体难度，使用 `1-5`。 |
| `estimated_hours` | 建议学习时长，用于学习路径规划。 |
| `summary` | 章节摘要。 |
| `learning_objectives` | 学习目标，可用于资源生成和学习效果评估。 |
| `key_node_ids` | 本章核心知识点 ID，后续随 `knowledge_points.json` 逐步补齐。 |
| `prerequisite_chapter_ids` | 前置章节 ID，用于章节级学习路径规划。 |
| `doc_file` | 章节 Markdown 讲义路径。 |
| `source_ids` | 主要参考来源，指向 `data/sources/sources.json`。 |
| `recommended_resource_types` | 本章适合生成的资源类型：`document / diagram / exercise / video_script / code_case`。 |
| `assessment_focus` | 本章适合测评的侧重点：`concept / calculation / coding / application`。 |
| `demo_usage` | 演示中的定位：`main_flow / support / extension`。 |
| `collection_status` | 收集进度：`skeleton / collecting / drafted / reviewed / ready`。 |
| `tags` | 用于筛选、检索和前端展示的标签。 |

## 3.3 知识点数据

这是最核心的数据。知识点不能只是一条课程提纲，而要能够同时驱动知识图谱、GraphRAG 检索、资源生成、学习路径规划、智能辅导和学习效果评估。

每个知识点建议使用增强结构：

```json
{
  "node_id": "ml_gradient_descent",
  "name": "梯度下降",
  "aliases": ["GD", "Gradient Descent", "梯度法"],
  "node_type": "method",
  "role_in_path": "core",
  "chapter_id": "ch03",
  "difficulty": 3,
  "estimated_minutes": 30,
  "summary": "通过沿损失函数梯度反方向迭代更新参数来最小化目标函数的优化方法。",
  "keywords": ["梯度", "学习率", "损失函数", "参数更新", "收敛"],
  "prerequisites": ["ml_loss_function", "ml_gradient_optimization_basic", "ml_linear_regression"],
  "related": ["ml_sgd_minibatch", "ml_backpropagation"],
  "recommended_resource_types": ["document", "diagram", "exercise", "code_case", "video_script"],
  "common_queries": [
    "梯度下降是什么",
    "为什么沿负梯度方向更新",
    "学习率太大会怎么样",
    "GD 和 SGD 有什么区别"
  ],
  "common_misconceptions": [
    "学习率越大收敛越快",
    "梯度下降总能找到全局最优"
  ],
  "mastery_objectives": [
    "能解释梯度下降的参数更新公式",
    "能比较 GD、SGD 和 Mini-batch 的差异",
    "能通过代码观察学习率对收敛过程的影响"
  ],
  "doc_chunk_ids": [],
  "exercise_ids": [],
  "code_case_ids": []
}
```

字段说明补充：

| 字段 | 说明 |
| --- | --- |
| `aliases` | 知识点别名、英文名、缩写，提升 GraphRAG 节点定位召回率。 |
| `node_type` | 知识点类型，建议使用 `foundation / concept / method / model / training_technique / evaluation / theory`。 |
| `role_in_path` | 在学习路径中的角色，建议使用 `entry / core / bridge / support / advanced / extension`。 |
| `recommended_resource_types` | 最适合该知识点的资源形式，避免所有节点平均生成 5 类资源。 |
| `common_queries` | 学生最常见的自然语言提问，用于检索增强和智能辅导。 |
| `common_misconceptions` | 学生最常见误区，用于错题归因、辅导解释和风险提示。 |
| `mastery_objectives` | 学完该知识点后应具备的可验证能力，用于学习效果评估。 |
| `doc_chunk_ids` / `exercise_ids` / `code_case_ids` | 讲义片段、题目和代码案例的挂载入口，初期可以先留空。 |

最少要保证 P0 主线知识点（如损失函数、梯度下降、逻辑回归、反向传播、注意力机制、Transformer）优先补齐这些增强字段。

## 3.4 讲义与说明性文本

这是 GraphRAG 检索的主要文本来源。

每个核心知识点最好至少有：

1. 核心概念说明
2. 为什么需要这个方法
3. 与前置知识的关系
4. 常见误区
5. 典型应用场景

推荐使用 Markdown 文件按章节组织。

## 3.5 练习题与答案

用于：

- 练习测试页
- 错题归因
- 学习效果评估
- 画像更新

每个核心知识点建议至少准备：

- 2 道选择题
- 1 道简答题
- 1 道编程题或应用题

题库采用**按章节拆分 + 增强版 Exercise Schema**。题目不仅用于展示，还要支持自动/半自动判题、错题归因、画像更新和 `ASSESSES` 图谱边生成。

推荐目录：

```text
data/exercises/
  exercises_index.json
  ch01_intro_evaluation.json
  ch02_math_optimization.json
  ch03_linear_models_optimization.json
  ch04_supervised_algorithms.json
  ch05_unsupervised_representation.json
  ch06_neural_deep_learning.json
  ch07_learning_theory.json
  ch08_semi_supervised.json
  ch09_probabilistic_graphical_models.json
  ch10_rule_learning.json
  ch11_reinforcement_learning.json
```

`exercises_index.json` 用于记录章节题库文件、目标数量、当前数量、优先级和状态。每个章节题库文件使用以下结构：

```json
{
  "chapter_id": "ch03",
  "chapter_title": "线性模型与梯度优化",
  "exercise_schema_version": "v1",
  "status": "drafted",
  "target_count": 12,
  "exercises": []
}
```

单道题目建议使用增强结构：

```json
{
  "exercise_id": "ex_ch03_gd_001",
  "version": "v1",
  "title": "学习率过大的影响",
  "type": "choice",
  "chapter_id": "ch03",
  "related_node_id": "ml_gradient_descent",
  "assesses": ["ml_gradient_descent"],
  "also_assesses": ["ml_loss_function"],
  "prerequisite_node_ids": ["ml_loss_function", "ml_gradient_optimization_basic"],
  "difficulty": 2,
  "estimated_minutes": 3,
  "cognitive_level": "understand",
  "assessment_focus": ["concept"],
  "question": "梯度下降中学习率过大最可能导致什么？",
  "options": [
    {"label": "A", "text": "收敛更快且一定更稳定"},
    {"label": "B", "text": "震荡或发散"}
  ],
  "answer": {
    "correct": "B",
    "explanation": "学习率过大时，参数更新步长过大，可能反复跨过最优点，导致震荡甚至发散。"
  },
  "rubric": [],
  "grading": {
    "method": "rule",
    "max_score": 1,
    "auto_gradable": true
  },
  "test_cases": [],
  "adaptive_feedback": {
    "default": "请回顾学习率如何影响参数更新步长。"
  },
  "profile_update_policy": {
    "on_correct": {
      "mastery_delta": 0.05,
      "confidence_delta": 0.03
    },
    "on_wrong": {
      "mastery_delta": -0.05,
      "add_weak_points": ["ml_gradient_descent"],
      "recommend_review_nodes": ["ml_loss_function", "ml_gradient_optimization_basic"]
    }
  },
  "misconception_tags": ["learning_rate_bigger_is_always_better"],
  "source_ids": ["book_zhou_ml", "course_stanford_cs229"],
  "created_by": "human",
  "review_status": "draft",
  "quality_score": null,
  "demo_usage": "main_flow",
  "tags": ["gradient-descent", "learning-rate", "p0"]
}
```

关键枚举：

| 字段 | 推荐取值 |
| --- | --- |
| `type` | `choice / multiple_choice / short_answer / coding / case_analysis` |
| `cognitive_level` | `remember / understand / apply / analyze` |
| `assessment_focus` | `concept / calculation / coding / application` |
| `grading.method` | `rule / rubric / unit_test / llm / hybrid` |
| `created_by` | `human / llm / agent` |
| `review_status` | `draft / reviewed / ready` |
| `demo_usage` | `main_flow / support / extension` |

第一轮优先补：

- `ch03_linear_models_optimization.json`
- `ch06_neural_deep_learning.json`
- `ch01_intro_evaluation.json`
- `ch02_math_optimization.json`

## 3.6 代码案例

用于：

- Code Agent 生成
- 智能辅导代码示例
- 资源生成页展示

优先准备以下主题的代码案例：

- 线性回归
- 逻辑回归
- 梯度下降
- KNN
- 决策树
- K-Means
- 多层神经网络前向传播
- 反向传播可视化
- CNN 图像分类最小示例

## 3.7 常见问题与误区

用于：

- 智能辅导
- 类比解释
- 错题归因
- 风险点提示

例如：

- 梯度下降为什么沿负梯度方向更新？
- 学习率太大和太小分别会怎样？
- 逻辑回归为什么叫回归却用于分类？
- 反向传播和梯度下降是什么关系？

---

## 4. 推荐的数据规模

## 4.1 最小可用版（MVP）

适合先打通比赛闭环。

| 数据类型 | 建议规模 |
| --- | --- |
| 章节数 | 6 章 |
| 知识点数 | 20-30 个 |
| 前置/关联关系 | 30-50 条 |
| 讲义片段 | 40-60 段 |
| 练习题 | 50-80 题 |
| 代码案例 | 6-10 个 |
| 常见问题/误区 | 20-40 条 |

## 4.2 标准演示版

适合提升展示完整度。

| 数据类型 | 建议规模 |
| --- | --- |
| 章节数 | 6-8 章 |
| 知识点数 | 35-50 个 |
| 前置/关联关系 | 60-100 条 |
| 讲义片段 | 80-150 段 |
| 练习题 | 100-150 题 |
| 代码案例 | 10-15 个 |
| 常见问题/误区 | 50-80 条 |

当前建议先按 **MVP 版** 收集。

---

## 5. 推荐的课程章节结构

课程章节采用“周志华《机器学习》主线 + 比赛演示优化”的结构。完整知识库先建 11 章骨架，但第一轮收集重心放在前 6 章；后 5 章先保留章节入口，后续有时间再补。

| 章节 | 标题 | 优先级 | 说明 |
| --- | --- | --- | --- |
| 第1章 | 机器学习导论与模型评估 | P0 | 对应绪论、模型评估与选择，支撑基础概念、过拟合、评估方法、性能度量和偏差方差 |
| 第2章 | 数学基础与优化基础 | P0 | 项目补充章节，支撑梯度下降、线性模型、反向传播和学习路径规划 |
| 第3章 | 线性模型与梯度优化 | P0 | 对应线性模型，并结合梯度下降、SGD、Mini-batch，是演示主线 |
| 第4章 | 经典监督学习算法 | P0 | 对应决策树、支持向量机、贝叶斯分类器、集成学习等内容 |
| 第5章 | 无监督学习与特征表示 | P0 | 对应聚类、降维与度量学习、特征选择与稀疏学习 |
| 第6章 | 神经网络与深度学习基础 | P0 | 对应神经网络，并补充 CNN、RNN、LSTM、Transformer、注意力机制 |
| 第7章 | 计算学习理论 | P2 | 扩展章节，第一轮只建骨架 |
| 第8章 | 半监督学习 | P2 | 扩展章节，第一轮只建骨架 |
| 第9章 | 概率图模型 | P2 | 扩展章节，第一轮只建骨架 |
| 第10章 | 规则学习 | P2 | 扩展章节，第一轮只建骨架 |
| 第11章 | 强化学习 | P2 | 扩展章节，第一轮只建骨架 |

---

## 6. 推荐首批核心知识点

当前建议先整理 **P0 重点知识点约 40 个**，再为 P2 扩展章节保留少量骨架知识点。正式收集时仍然把精力放在第 1-6 章，后 5 章只保证图谱结构不断裂。

### 第1章 机器学习导论与模型评估
- 机器学习基本术语
- 监督学习与无监督学习
- 训练集、验证集与测试集
- 泛化能力
- 过拟合与欠拟合
- 评估方法
- 性能度量
- 偏差与方差
- 正则化

### 第2章 数学基础与优化基础
- 线性代数基础
- 概率论与统计基础
- 微积分与优化基础
- 损失函数
- 梯度与最优化

### 第3章 线性模型与梯度优化
- 线性回归
- 逻辑回归
- 线性判别分析
- 梯度下降
- 随机梯度下降与 Mini-batch

### 第4章 经典监督学习算法
- 决策树
- SVM
- 贝叶斯分类器
- 集成学习
- 随机森林

### 第5章 无监督学习与特征表示
- 聚类
- K-Means
- 降维
- 度量学习
- 特征选择
- 稀疏学习

### 第6章 神经网络与深度学习基础
- 感知机
- 多层神经网络
- 激活函数
- 反向传播
- Dropout
- BatchNorm
- CNN
- RNN
- LSTM
- Transformer
- 注意力机制

### 第7-11章 扩展章节

第一轮收集只建骨架，后续再补：

- PAC 学习
- VC 维
- 半监督学习
- 贝叶斯网
- 马尔可夫网
- 规则学习
- 强化学习
- 马尔可夫决策过程
- Q-learning

---

## 7. 知识库文件组织建议

建议将数据文件组织为：

```text
data/
  course/
    course_meta.json
    chapters.json
    knowledge_points.json
    graph_edges.json
  docs/
    ch01_intro_evaluation.md
    ch02_math_optimization.md
    ch03_linear_models_optimization.md
    ch04_supervised_algorithms.md
    ch05_unsupervised_representation.md
    ch06_neural_deep_learning.md
    ch07_learning_theory.md
    ch08_semi_supervised.md
    ch09_probabilistic_graphical_models.md
    ch10_rule_learning.md
    ch11_reinforcement_learning.md
  exercises/
    exercises_index.json
    ch01_intro_evaluation.json
    ch02_math_optimization.json
    ch03_linear_models_optimization.json
    ch04_supervised_algorithms.json
    ch05_unsupervised_representation.json
    ch06_neural_deep_learning.json
    ch07_learning_theory.json
    ch08_semi_supervised.json
    ch09_probabilistic_graphical_models.json
    ch10_rule_learning.json
    ch11_reinforcement_learning.json
  code_cases/
    linear_regression.py
    logistic_regression.py
    knn_demo.py
    decision_tree_demo.py
    gradient_descent_demo.py
  faq/
    misconceptions.json
  sources/
    sources.json
```

其中最关键的是：

1. `knowledge_points.json`
2. `graph_edges.json`
3. `docs/*.md`
4. `exercises_index.json` 与章节题库文件
5. `sources/sources.json`

### 7.1 文件夹与文件说明

| 路径 | 用途 | 主要被谁使用 |
| --- | --- | --- |
| `data/` | 课程知识库根目录，后续提交包、后端导入脚本、向量库构建脚本都从这里读取数据。 | 后端服务、知识库导入脚本、GraphRAG、提交包整理 |
| `data/course/` | 存放课程的结构化元数据，包括课程信息、章节、知识点和图谱边。这里是知识图谱和学习路径规划的基础。 | Knowledge Agent、Planning Agent、GraphRAG 检索、前端知识图谱页 |
| `data/course/course_meta.json` | 描述整门课程，例如课程 ID、课程名称、目标学习者、难度范围和章节数。 | 后端课程服务、前端课程选择页 |
| `data/course/chapters.json` | 描述章节结构、优先级、难度、学习目标、前置章节、讲义路径、来源、推荐资源类型、测评重点、演示定位和收集状态。 | 知识图谱层级展示、课程目录页、文档挂载、资源生成、学习路径规划、测评设计 |
| `data/course/knowledge_points.json` | 描述每个知识点的 ID、名称、章节、难度、预计学习时间、摘要、关键词、前置知识和关联知识。 | 知识图谱核心节点、GraphRAG 节点定位、学习路径规划、资源生成 |
| `data/course/graph_edges.json` | 描述图谱关系，例如章节包含知识点、知识点之间的前置关系和关联关系。 | GraphRAG 子图扩展、学习路径规划、知识图谱可视化 |
| `data/docs/` | 存放按章节整理的 Markdown 讲义，是 GraphRAG 检索和引用的主要文本来源。 | Retrieval Agent、Document Agent、Tutoring 功能 |
| `data/docs/ch*.md` | 每章对应一个讲义文件。每个文档块应尽量标明 `knowledge_node_id`、`source_ids`、标题、正文和关键词。 | 文档切片、向量检索、引用来源展示 |
| `data/exercises/` | 存放按章节拆分的练习题、答案、评分规则、反馈规则和画像更新策略。题目必须绑定知识点。 | Exercise Agent、Evaluation Agent、学习效果评估、画像更新 |
| `data/exercises/exercises_index.json` | 题库索引文件，记录每章题库文件、目标数量、当前数量、优先级和状态。 | 后端题库加载、收集进度统计、提交包检查 |
| `data/exercises/ch*.json` | 章节题库文件，包含该章节的增强版练习题对象。 | 练习测试页、错题归因、掌握度计算、`ASSESSES` 边生成 |
| `data/code_cases/` | 存放可运行或可讲解的代码案例。每个代码案例应能绑定到一个或多个知识点。 | Code Agent、智能辅导代码示例、资源生成页 |
| `data/faq/` | 存放常见问题、常见误区和类比解释素材。 | Tutoring 功能、错题归因、智能辅导素材 |
| `data/faq/misconceptions.json` | 常见误区主文件，用于记录问题、解释、误区描述和关联知识点。 | 智能辅导、Evaluation Agent、画像弱点更新 |
| `data/sources/` | 存放来源元数据，记录教材、公开课、官方文档和自写材料的来源信息。 | 引用来源展示、合规说明、提交材料 |
| `data/sources/sources.json` | 来源主文件，后续文档块、题目和代码案例都通过 `source_ids` 引用这里的来源。 | GraphRAG 引用、开源与资料说明、文档合规 |

### 7.2 文件之间的关系

知识库文件不是彼此独立的资料堆，而是一组互相引用的数据：

1. `chapters.json` 定义课程章节。
2. `knowledge_points.json` 中的 `chapter_id` 指向某个章节。
3. `graph_edges.json` 用 `source` 和 `target` 连接章节、知识点和资源。
4. `docs/*.md` 中的文档块通过 `knowledge_node_id` 绑定知识点，通过 `source_ids` 绑定来源。
5. `exercises.json` 通过 `related_node_id` 或 `assesses` 绑定知识点。
6. `code_cases/*.py` 需要在文件注释或元数据中标明关联知识点。
7. `misconceptions.json` 通过 `related_node_id` 绑定知识点。
8. `sources.json` 为所有讲义、题目、代码案例和 FAQ 提供来源记录。

### 7.3 后续扩展建议

如果后续需要更严格的数据管理，可以继续增加：

| 路径 | 用途 |
| --- | --- |
| `data/chunks/` | 存放自动切分后的文档块，便于向量化和调试检索结果。 |
| `data/generated/` | 存放多智能体生成的讲解文档、思维导图、视频脚本和练习资源样例。 |
| `data/evaluation/` | 存放测试学生样例、答题记录和学习效果评估样例。 |
| `data/indexes/` | 存放本地 FAISS、BM25 或其他检索索引文件。 |

---

## 8. 数据收集顺序建议

### 第一阶段：先搭骨架

先完成：

1. 章节清单
2. 20-30 个核心知识点
3. 前置关系表
4. 每个知识点的难度、关键词、摘要

### 第二阶段：补检索材料

再完成：

1. 每个知识点 1-2 段讲义说明
2. 每章对应 Markdown 文档
3. 讲义与知识点的挂载关系

### 第三阶段：补练习与代码

继续完成：

1. 50-80 道练习题
2. 6-10 个代码案例
3. 题目与知识点的挂载关系
4. 代码案例与知识点的挂载关系

### 第四阶段：补智能辅导素材

最后完成：

1. 常见问题清单
2. 常见误区清单
3. 类比解释素材
4. 视频脚本素材描述

---

## 9. 数据来源建议

优先使用以下来源：

1. 自己整理的课程讲义
2. 公开课程资料
3. 教材摘要
4. 开源代码示例
5. 自己编写的示例题

### 9.1 推荐十本本地参考教材

后续构建机器学习知识库时，优先将 `参考教材/` 下的十本 PDF 作为主参考来源。教材主要用于理解、摘要、知识点结构、公式、例题设计和引用来源记录，不建议把大段原文直接复制进知识库。每本本地教材都已在 `data/sources/sources.json` 中注册 `source_id` 和 `local_file`。

| 类型 | 资料 | 推荐用途 |
| --- | --- | --- |
| 中文主教材 | 周志华《机器学习》 | 机器学习知识点主干，适合监督学习、无监督学习、模型评估、过拟合、决策树、SVM、集成学习等 |
| 中文理论教材 | 李航《统计学习方法》 | 算法定义、公式和推导参考，适合感知机、KNN、逻辑回归、SVM、EM、HMM、CRF 等 |
| 深度学习公开教材 | 《动手学深度学习》Dive into Deep Learning | 深度学习章节和代码案例，适合神经网络、反向传播、CNN、RNN、LSTM、Transformer、注意力机制 |
| 理论增强参考 | Bishop, Pattern Recognition and Machine Learning | 概率模型、线性模型、核方法、聚类和图模型等理论增强参考 |
| 工程实践参考 | Aurélien Géron, Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow | sklearn、Keras、TensorFlow 代码案例、实验流程和工程化实践 |
| 数学基础参考 | Mathematics for Machine Learning | 线性代数、微积分、概率论、优化基础、梯度等数学前置 |
| 中文公式辅助 | Datawhale《南瓜书：机器学习公式详解》 | 周志华《机器学习》的公式推导辅助，适合线性模型、逻辑回归、SVM、贝叶斯、聚类 |
| 中文深度学习教材 | 邱锡鹏《神经网络与深度学习》 | 神经网络、反向传播、CNN、RNN、注意力机制、Transformer |
| 中文工程实践参考 | 《机器学习实战：基于 Scikit-Learn、Keras 和 TensorFlow（原书第3版）》 | Python 机器学习、sklearn、Keras、TensorFlow、代码案例和实验流程 |
| 中文应用实践参考 | 《机器学习实战：视频教学版》 | Python 机器学习、线性回归、分类算法、降维、聚类、关联规则、协同过滤和项目实战 |

### 9.2 推荐公开课与在线资料

公开课资料用于补充讲义表达、课程顺序、代码案例和可公开引用链接。优先使用官方课程页、官方文档或公开在线教材。

| 资料 | 推荐用途 |
| --- | --- |
| Stanford CS229 Machine Learning | 线性回归、逻辑回归、正则化、SVM、K-Means、EM 等核心理论和讲义结构 |
| 李宏毅机器学习课程 | 中文讲解材料，适合整理成面向本科生的通俗讲义、常见问题和类比解释 |
| Andrew Ng Machine Learning Specialization | 适合建立入门学习路径和监督学习、无监督学习、神经网络基础内容 |
| MIT 6.S191 Introduction to Deep Learning | 深度学习入门、神经网络、CNN、序列模型和生成模型概览 |
| Stanford CS231n | CNN、图像分类、反向传播和视觉模型相关内容 |
| scikit-learn User Guide | 线性回归、逻辑回归、KNN、决策树、随机森林、K-Means 等代码案例和算法 API 说明 |

### 9.3 推荐来源记录字段

建议建立 `data/sources/sources.json`，记录每份资料的来源信息，后续文档块、题目、代码案例都可以引用 `source_id`。

```json
{
  "source_id": "book_zhou_ml",
  "title": "机器学习",
  "author": "周志华",
  "type": "textbook",
  "language": "zh",
  "publisher_or_platform": "清华大学出版社",
  "url": "",
  "license_or_usage_note": "仅用于学习理解和自写摘要，不在知识库中大段复制原文",
  "recommended_for": ["模型评估", "决策树", "SVM", "集成学习"]
}
```

注意：

- 所有资料都要记录来源，便于引用与合规说明
- 尽量使用可公开说明来源的资料
- 不要直接堆砌海量网页内容，优先做高质量人工整理
- 教材内容用于理解和摘要，知识库最终内容应尽量使用自己的表述、少量必要引用和清晰来源记录

---

## 10. 收集时的验收标准

一份数据是否可以进入知识库，至少满足：

- 能挂载到某个知识点
- 能说明来源
- 内容足够清晰，适合学生学习
- 能被用于检索、生成、评估中的至少一个场景

如果一段材料无法对应知识点、无法形成引用、无法支持任何功能，就不要优先收集。

---

## 11. 当前最建议的执行策略

当前阶段最合适的目标是：

- 先完成 6 章结构
- 先完成 25 个核心知识点
- 先完成 40 条左右前置关系
- 每个核心知识点补 1 段讲义
- 先准备 50-80 道题
- 先准备 8 个左右代码案例

这样就足够支撑比赛版本的知识图谱、GraphRAG、资源生成、练习测试和学习路径规划。

---

## 12. 你接下来立刻可以做的事

建议按以下顺序执行：

1. 先建 `chapters.json`
2. 再建 `knowledge_points.json`
3. 再建 `graph_edges.json`
4. 再整理 6 章 Markdown 讲义
5. 再整理 `exercises.json`
6. 最后补代码案例和 FAQ

如果时间有限，优先保证：

- 知识点结构正确
- 前置关系清晰
- 讲义片段可检索
- 练习题能支持评估

这 4 件事比资料数量更重要。
