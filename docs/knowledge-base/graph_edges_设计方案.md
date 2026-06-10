# graph_edges.json 设计方案

## 1. 设计目标

`graph_edges.json` 用于统一描述 EduGraph-Agent 机器学习课程知识库中的结构关系、认知关系和资源关系。它需要同时支持以下能力：

1. 学习路径规划
2. GraphRAG 子图扩展
3. 知识图谱可视化
4. 资源、题目与代码案例挂载
5. 比赛演示中的可解释展示

因此，这个文件不能只是简单的三元组，而应是**带语义、带权重、带来源、带解释**的增强关系文件。

---

## 2. 关系分层

虽然所有边都放在同一个 `graph_edges.json` 中，但逻辑上分为三层。

### 2.1 结构层

用于描述课程组织结构。

关系类型：

- `CONTAINS`

示例：

- `ml_course -> ch03`
- `ch03 -> ml_gradient_descent`

作用：

- 图谱层级展示
- 章节导航
- 从课程到章节、从章节到知识点的组织

---

### 2.2 认知层

用于描述知识学习关系。

关系类型：

- `PREREQUISITE`
- `RELATED`
- `EXTENDS`
- `CONTRASTS`

作用：

- GraphRAG 子图扩展
- 学习路径规划
- 智能辅导中的对比解释
- 图谱高亮展示

---

### 2.3 资源层

用于描述资源、题目和代码案例与知识点之间的挂载关系。

关系类型：

- `SUPPORTS`
- `ASSESSES`
- `PRACTICES`
- `ILLUSTRATES`

作用：

- 文档和图解挂载到知识点
- 练习题测评知识点
- 代码案例练习知识点
- 视频脚本/图解说明知识点

---

## 3. 统一字段结构

建议每条边使用如下结构：

```json
{
  "edge_id": "edge_ml_loss_function_to_ml_gradient_descent_prerequisite",
  "source": "ml_loss_function",
  "target": "ml_gradient_descent",
  "relation": "PREREQUISITE",
  "strength": "strong",
  "weight": 0.95,
  "direction": "forward",
  "explanation": "理解梯度下降之前，需要先理解损失函数如何衡量预测误差以及优化目标是什么。",
  "source_ids": ["book_zhou_ml", "course_stanford_cs229"],
  "status": "verified",
  "demo_usage": "main_flow",
  "tags": ["p0", "optimization", "demo-core"]
}
```

---

## 4. 字段定义

| 字段 | 说明 |
| --- | --- |
| `edge_id` | 边的唯一 ID，建议格式：`edge_<source>_to_<target>_<relation>` |
| `source` | 起点 ID，可以是课程、章节、知识点、资源、题目或代码案例 |
| `target` | 终点 ID |
| `relation` | 关系类型 |
| `strength` | 关系强度：`strong / medium / weak` |
| `weight` | 数值权重，范围建议 `0-1` |
| `direction` | 方向：`forward / bidirectional` |
| `explanation` | 用自然语言解释这条边为什么存在 |
| `source_ids` | 来源列表，必须能在 `data/sources/sources.json` 中找到 |
| `status` | 关系状态：`draft / verified` |
| `demo_usage` | 演示定位：`main_flow / support / extension` |
| `tags` | 关键词标签，用于筛选和前端展示 |

---

## 5. 关系类型定义

### 5.1 `CONTAINS`

表示结构包含关系。

适用：
- 课程包含章节
- 章节包含知识点

特点：
- 方向固定为 `forward`
- 强度通常为 `strong`
- 权重通常为 `1.0`

---

### 5.2 `PREREQUISITE`

表示强前置依赖。

只有满足以下任一条件时才建立：

1. 不先学 A，几乎无法理解 B 的核心原理
2. 不先学 A，无法完成 B 的基础练习
3. B 的定义、推导或训练过程直接依赖 A

示例：
- `ml_loss_function -> ml_gradient_descent`
- `ml_gradient_descent -> ml_backpropagation`
- `ml_attention_mechanism -> ml_transformer`

---

### 5.3 `RELATED`

表示主题相关，但无严格前后顺序。

示例：
- `ml_linear_regression <-> ml_logistic_regression`
- `ml_rnn <-> ml_attention_mechanism`

作用：
- GraphRAG 扩展背景知识
- 辅导推荐相关知识点

---

### 5.4 `EXTENDS`

表示扩展、变体或进阶关系。

示例：
- `ml_gradient_descent -> ml_sgd_minibatch`
- `ml_rnn -> ml_lstm`
- `ml_multilayer_neural_network -> ml_cnn`

区别：
- `PREREQUISITE` 是必须先懂
- `EXTENDS` 是在已有知识上继续拓展

---

### 5.5 `CONTRASTS`

表示容易混淆、适合对比学习。

示例：
- `ml_linear_regression <-> ml_logistic_regression`
- `ml_dropout <-> ml_batchnorm`
- `ml_generalization <-> ml_overfitting_underfitting`

作用：
- 智能辅导中的对比解释
- 辨析题设计
- 前端高亮“易混淆关系”

---

### 5.6 `SUPPORTS`

表示文档/讲义/图解支撑某知识点。

示例：
- `doc_ch03_chunk_001 -> ml_gradient_descent`

---

### 5.7 `ASSESSES`

表示题目测评某知识点。

示例：
- `ex_gd_001 -> ml_gradient_descent`

练习题资源边使用短 ID，建议格式：

- `assess_<exercise_id>_<knowledge_node_id>`

例如：

- `assess_ex_ch03_gd_001_ml_gradient_descent`

这样能保留题目、关系和知识点信息，同时避免 `edge_ex_*_to_*_assesses` 过长。

---

### 5.8 `PRACTICES`

表示代码案例练习某知识点。

示例：
- `code_gradient_descent_demo -> ml_gradient_descent`

---

### 5.9 `ILLUSTRATES`

表示图解或视频脚本说明某知识点。

示例：
- `video_gd_storyboard -> ml_gradient_descent`
- `diagram_bp_flow -> ml_backpropagation`

---

## 6. 权重建议

| 关系 | 强度 | 默认权重 |
| --- | --- | --- |
| `PREREQUISITE` | strong | 0.95 |
| `PREREQUISITE` | medium | 0.85 |
| `RELATED` | medium | 0.70 |
| `RELATED` | weak | 0.55 |
| `EXTENDS` | strong | 0.88 |
| `EXTENDS` | medium | 0.78 |
| `CONTRASTS` | medium | 0.72 |
| `CONTAINS` | strong | 1.00 |
| `SUPPORTS` | strong | 0.90 |
| `ASSESSES` | strong | 0.92 |
| `PRACTICES` | strong | 0.90 |
| `ILLUSTRATES` | strong | 0.88 |

说明：
- `PREREQUISITE` 权重用于学习路径规划和前置补齐
- `RELATED` / `EXTENDS` 权重用于 GraphRAG 子图扩展优先级
- 资源边权重主要用于排序和展示，不参与章节级学习路径拓扑排序

---

## 7. 方向规则

| 关系 | direction |
| --- | --- |
| `CONTAINS` | `forward` |
| `PREREQUISITE` | `forward` |
| `EXTENDS` | `forward` |
| `SUPPORTS` | `forward` |
| `ASSESSES` | `forward` |
| `PRACTICES` | `forward` |
| `ILLUSTRATES` | `forward` |
| `RELATED` | `bidirectional` |
| `CONTRASTS` | `bidirectional` |

---

## 8. 建边规则与约束

### 8.1 `PREREQUISITE` 不可滥用

不要把所有相关点都做成前置关系，否则学习路径会过长，GraphRAG 扩展也会失控。

### 8.2 章节边和知识点边可以共存，但要靠 `relation` 明确区分

即便放在一个文件里，也不能混淆层次。

### 8.3 资源边不要参与认知路径拓扑排序

学习路径规划只使用：
- `PREREQUISITE`
- 必要时辅助参考 `EXTENDS`

不要把 `SUPPORTS / ASSESSES / PRACTICES / ILLUSTRATES` 用来做前置推理。

### 8.4 P0 主线边必须有解释和来源

主线知识点如：
- `ml_loss_function`
- `ml_gradient_descent`
- `ml_sgd_minibatch`
- `ml_backpropagation`
- `ml_attention_mechanism`
- `ml_transformer`

相关边建议都补：
- `explanation`
- `source_ids`
- `status = verified`
- `demo_usage = main_flow`

---

## 9. 开发建议

第一轮优先建立以下边：

1. `CONTAINS`：课程 → 章节 → 知识点
2. P0 主线知识点的 `PREREQUISITE`
3. 核心对比点的 `CONTRASTS`
4. 关键扩展点的 `EXTENDS`
5. 收集讲义、题目、代码后再补 `SUPPORTS / ASSESSES / PRACTICES / ILLUSTRATES`

---

## 10. 当前推荐执行顺序

建议按以下顺序落地：

1. 先补 `course -> chapter` 和 `chapter -> knowledge_point` 的 `CONTAINS`
2. 再补 P0 主线认知边：
   - `PREREQUISITE`
   - `EXTENDS`
   - `CONTRASTS`
3. 最后在资料收集完成后补资源边：
   - `SUPPORTS`
   - `ASSESSES`
   - `PRACTICES`
   - `ILLUSTRATES`

这样可以先保证知识图谱、路径规划和 GraphRAG 可跑，再补资源挂载层。

---

## 11. 当前实现状态（2026-06-03）

### 已完成

当前 `data/course/graph_edges.json` 已经落地，且完成一致性校验（source / target / source_ids 均合法）。当前版本共有 133 条边，重点覆盖：

1. **结构边**
   - `ml_course -> ch01 ~ ch11`
   - `ch01 / ch02 / ch03 / ch06 -> P0 主线知识点`

2. **P0 主线认知边**
   - `PREREQUISITE`：如 `ml_loss_function -> ml_gradient_descent`、`ml_gradient_descent -> ml_backpropagation`
   - `EXTENDS`：如 `ml_gradient_descent -> ml_sgd_minibatch`、`ml_rnn -> ml_lstm`
   - `RELATED`：如 `ml_rnn <-> ml_attention_mechanism`
   - `CONTRASTS`：如 `ml_linear_regression <-> ml_logistic_regression`、`ml_dropout <-> ml_batchnorm`

3. **增强字段已启用**
   - `strength`
   - `weight`
   - `direction`
   - `explanation`
   - `source_ids`
   - `status`
   - `demo_usage`
   - `tags`

4. **ch01 / ch02 / ch03 / ch04 / ch05 / ch06 练习题资源边**
   - 已为 `ch01_intro_evaluation.json` 的 8 道题生成 8 条 `ASSESSES` 边
   - 已为 `ch02_math_optimization.json` 的 8 道题生成 8 条 `ASSESSES` 边
   - 已为 `ch03_linear_models_optimization.json` 的 12 道题生成 14 条 `ASSESSES` 边
   - 已为 `ch04_supervised_algorithms.json` 的 8 道题生成 8 条 `ASSESSES` 边
   - 已为 `ch05_unsupervised_representation.json` 的 6 道题生成 6 条 `ASSESSES` 边
   - 已为 `ch06_neural_deep_learning.json` 的 12 道题生成 12 条 `ASSESSES` 边
   - 边 ID 使用短格式：`assess_<exercise_id>_<knowledge_node_id>`

### 还没做

当前版本已开始补 `ASSESSES` 资源边，但以下资源边还未全部系统化写入：

- `SUPPORTS`
- `PRACTICES`
- `ILLUSTRATES`

原因：
- 讲义 chunk 的稳定 ID 还未批量整理完成
- `code_cases` 的对象 ID 体系还未统一
- 视频脚本 / 图解对象还未形成可引用的资源实体

### 下一步建议

推荐后续按以下顺序补全：

1. 先开发 GraphRAG 数据加载服务，读取 course / exercises / sources 等 JSON 数据
2. 统一代码案例对象命名与 ID 规则
3. 给讲义 chunk 建立稳定 ID
4. 再补 `PRACTICES / SUPPORTS / ILLUSTRATES` 资源边

在补资源边之前，当前这版 `graph_edges.json` 已足够支撑：

- 知识图谱可视化
- 学习路径规划
- GraphRAG 子图扩展
- 主线知识点的可解释推荐
