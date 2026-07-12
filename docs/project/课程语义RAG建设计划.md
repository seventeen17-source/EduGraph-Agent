# 课程语义 RAG 建设计划

最后更新：2026-07-03

## 1. 定位

课程向量 RAG 不应复制 Neo4j 中的课程事实数据，而应作为“语义入口层”存在。

Neo4j 负责保存可信事实：

- 知识点、章节、前置关系、相关关系
- FAQ / 常见误区
- 练习题与测评关系
- 代码案例
- 文档片段、来源、引用链路

Chroma 向量库负责保存语义检索视图：

- 学生可能怎么提问
- 学生可能怎么表达困惑
- 某道题可能暴露什么错误
- 某个代码案例适合解决什么实践需求
- 某个知识点适合怎样学习、复习、诊断

向量检索返回 `target_uid`，再回到 Neo4j 查询 canonical evidence。这样可以避免“双份知识库事实不一致”的问题。

推荐链路：

```text
学生自然语言问题
-> Neo4j 解析中心知识点
-> 图扩展候选范围
-> Chroma 在候选范围内做语义入口检索
-> target_uid 回查 Neo4j canonical evidence
-> EvidencePackage 合并证据
-> Agent 基于证据生成个性化回答/练习/代码案例
-> 学生反馈和练习结果写回画像
```

## 2. 嵌入模型推荐

### 2.1 当前推荐

优先使用 `text-embedding-3-small`。

原因：

- 当前项目只有约 603 条课程语义视图，规模不大。
- 1536 维，和现有 `EmbeddingService.embedding_dim()` 默认配置一致。
- OpenAI-compatible API 已经被当前代码支持，接入成本最低。
- 足够支撑 GraphRAG 调试、演示和第一轮质量评测。

`.env` 示例：

```env
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=your_api_key
EMBEDDING_BASE_URL=https://api.openai.com/v1
```

### 2.2 更高质量 API 模型

可选 `text-embedding-3-large`。

适合场景：

- 课程语义视图扩展到数千条以上。
- FAQ、练习错误诊断、代码案例描述显著增加。
- 对中文自然语言问题的细粒度匹配质量要求更高。

注意：

- 维度为 3072。
- 切换后必须重建 Chroma collection。
- 成本和延迟高于 `text-embedding-3-small`。

### 2.3 开源/本地优先模型

推荐顺序：

1. `BAAI/bge-m3`
   - 多语言、多粒度、长文本能力较强。
   - 适合中文课程检索、FAQ 检索、跨章节语义召回。
   - 推荐作为本地化或私有部署首选。

2. `BAAI/bge-large-zh-v1.5`
   - 中文语义检索成熟稳定。
   - 适合中文为主、文本长度中等的课程知识库。
   - 部署和调试比 `bge-m3` 更简单。

3. `jina-embeddings-v3`
   - 多语言能力强，支持较长上下文。
   - 适合后续需要中英文资料混合、代码说明混合检索的场景。

4. `moka-ai/m3e-large`
   - 中文向量检索常用模型。
   - 适合资源有限、希望快速本地化验证的场景。

5. `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
   - 成熟、易用、多语言。
   - 效果不是最前沿，但适合做离线 baseline。

### 2.4 不建议当前优先使用

- `text-embedding-ada-002`：老模型，只适合兼容旧索引。
- 只支持英文优化的 embedding：当前项目中文问题和中文课程资源占主体。
- 未知维度、未知归一化方式、无稳定 API 文档的模型：会增加 Chroma 维度错误和检索质量不可控风险。

### 2.5 代码适配要求

当前 `backend/app/memory/embedding.py` 只显式识别：

```python
text-embedding-3-small -> 1536
text-embedding-3-large -> 3072
text-embedding-ada-002 -> 1536
```

如果接入其他模型，需要补充：

- `EMBEDDING_PROVIDER`
- 模型维度映射
- OpenAI-compatible API provider
- 本地 `sentence-transformers` provider
- 索引重建前的 collection 维度检查

## 3. 当前代码状态

已具备 P0 雏形：

- `backend/app/rag/schemas.py`
- `backend/app/rag/semantic_view_builder.py`
- `backend/app/rag/course_vector_store.py`
- `backend/app/rag/course_retriever.py`
- `Scripts/build_course_semantic_index.py`
- `backend/app/graphrag/evidence_retriever.py` 已接入 `semantic_hits`
- `backend/app/graphrag/schemas.py` 已在 `EvidencePackage` 中加入 `semantic_hits`
- `backend/app/agents/resource_agents.py` 已把 `semantic_hits` 纳入资源生成上下文

已验证 dry-run 可生成约 603 条语义视图：

```text
CodeCase: 24
DocumentChunk: 82
Exercise: 54
KnowledgePoint: 121
Misconception: 322
```

## 4. P0：必须完成

### P0.1 构建真实课程语义索引

目标：

- 用真实 embedding API 构建 Chroma collection。
- 确认 `course_semantic_views` 有真实向量，而不是 dry-run 数据。

命令：

```powershell
cd D:\Code\EduGraph-Agent
python Scripts/build_course_semantic_index.py
```

验收标准：

- 构建过程无异常。
- collection count 约为 603。
- 重启后端后 GraphRAG 查询不会因为向量库为空而返回空 `semantic_hits`。

### P0.2 增加语义检索调试接口

建议新增：

```text
GET /api/graphrag/semantic-search?q=...&uid=...
```

返回：

- query
- center_uid
- candidate_node_ids
- semantic_hits
- target_uid
- target_type
- view_type
- score
- semantic_score
- graph_bonus
- profile_bonus
- rank_reason

验收样例：

```text
q=为什么我的 loss 一直震荡，是不是学习率太大
uid=ml_gradient_descent
```

期望命中：

- 梯度下降
- 学习率
- loss 震荡相关 FAQ
- 优化过程相关练习
- 梯度下降或学习率相关代码案例

### P0.3 semantic hit 回灌 Neo4j canonical evidence

当前 `semantic_hits` 仍只是语义视图。下一步必须根据 `target_uid` 回查 Neo4j。

合并规则：

```text
Misconception -> misconceptions
Exercise -> exercises
CodeCase -> code_cases
DocumentChunk -> document_chunks
KnowledgePoint -> related_nodes 或 recommended_next_actions
```

要求：

- Neo4j 仍是事实源。
- `semantic_hits` 保留为检索解释轨迹。
- 不把 Chroma metadata 当成最终事实。
- 合并时按 uid 去重。

验收标准：

- 只靠语义命中的 FAQ / 练习 / 代码案例，可以进入最终 EvidencePackage。
- Resource Agent 能使用这些 canonical evidence 生成回答。

### P0.4 后端启动时暴露索引健康状态

建议在 `/health` 或新增 endpoint 中返回：

- Chroma persist dir
- embedding model
- embedding dimension
- `course_semantic_views` count
- collection dimension 是否匹配当前 embedding model

验收标准：

- 前端或调试人员能一眼判断：当前是否真的使用了课程向量 RAG。
- 如果索引为空，系统应提示“课程语义索引未构建”，而不是静默表现为检索质量差。

### P0.5 写入最小回归测试

至少覆盖：

- `build_course_semantic_views()` 可生成稳定数量和类型分布。
- `CourseVectorStore.replace_all()` 可以写入测试 collection。
- `CourseSemanticRetriever.search()` 可以返回带 `target_uid` 的结果。
- GraphRAG evidence package 包含 `semantic_hits` 字段。
- semantic hit 回灌后 canonical evidence 不重复。

## 5. P1：强烈建议完成

### P1.1 生成更多高质量语义视图

当前语义视图多为模板生成。后续应离线生成更丰富的 paraphrase views。

建议数量：

- 每条 FAQ：6-8 条学生问法
- 每个重点知识点：8-12 条概念解释入口
- 每道重点练习：3-5 条错误诊断入口
- 每个代码案例：3-5 条实践意图入口

要求：

- 生成结果仍然只保存 semantic view。
- `target_uid` 必须指向 Neo4j 中已有节点。
- 不把 LLM 生成文本当 canonical 课程内容。

### P1.2 加入 rerank 层

当前 rerank 主要是向量分数 + 图范围 bonus + 画像 bonus。后续可以加入：

- cross-encoder reranker
- LLM evidence judge
- query intent-specific ranker
- exercise/code/document 不同资源类型权重

对学习场景尤其重要：

- 学生要“讲解”时，不应优先返回练习。
- 学生要“代码”时，代码案例权重应更高。
- 学生说“我错在哪里”时，FAQ / error diagnosis 应更高。

### P1.3 前端 EvidencePanel 展示 semantic hits

前端应能显示：

- 命中的语义入口
- 指向的 canonical 证据
- 为什么命中
- 图谱加权、画像加权、语义分数

注意：

- 不要直接暴露英文枚举。
- `student_confusion` 显示为“学生困惑入口”。
- `error_diagnosis` 显示为“错误诊断入口”。
- `code_intent` 显示为“代码实践入口”。

### P1.4 Agent 使用 semantic hits 做生成策略

资源生成和主对话不应只把 `semantic_hits` 当展示信息。

应进入策略：

- 命中 `student_confusion`：先澄清误区。
- 命中 `error_diagnosis`：先解释错误原因，再给补救练习。
- 命中 `code_intent`：优先给可运行代码和调试建议。
- 命中弱点知识点：先补前置，再讲当前问题。
- 命中低掌握度节点：回答中加入复习建议。

### P1.5 建立检索质量评测集

新增小型测试集，例如 30-50 条学生真实问法：

```json
{
  "query": "为什么我的 loss 一直震荡",
  "expected_node_ids": ["ml_gradient_descent", "ml_learning_rate"],
  "expected_target_types": ["Misconception", "DocumentChunk", "CodeCase"]
}
```

指标：

- Recall@5
- MRR
- target_type 命中率
- 是否命中学生画像弱点
- 是否命中可生成资源的 canonical evidence

## 6. P2：后续增强

### P2.1 多 embedding 模型对比

对比：

- `text-embedding-3-small`
- `text-embedding-3-large`
- `BAAI/bge-m3`
- `BAAI/bge-large-zh-v1.5`
- `jina-embeddings-v3`

评估维度：

- 中文问题召回
- 误区类问题召回
- 代码案例召回
- 长文本片段召回
- 成本
- 延迟
- 部署复杂度

### P2.2 混合检索

加入：

- BM25 / keyword recall
- dense vector recall
- graph constrained recall
- profile-aware recall
- reranker fusion

最终得分可以类似：

```text
final_score =
  0.45 * dense_score
  + 0.20 * keyword_score
  + 0.20 * graph_bonus
  + 0.15 * profile_bonus
```

### P2.3 课程索引版本化

语义索引需要版本管理：

- course version
- embedding model
- embedding dimension
- semantic view generator version
- indexed_at
- source data hash

否则后续课程内容变动后，很难判断 Chroma 中的旧向量是否已经过期。

### P2.4 增量索引

当前脚本是 replace all。后续应支持：

- 按章节重建
- 按 target_uid 重建
- 删除失效 target_uid
- 对新增 FAQ / 练习 / 代码案例增量写入

### P2.5 多模态扩展

长期可以扩展：

- 公式截图
- 知识图谱局部图
- 代码运行输出
- 学生错题截图
- 视频脚本片段

但这应放在文本 GraphRAG 稳定之后。

## 7. 实施顺序

推荐顺序：

1. 使用 `text-embedding-3-small` 构建真实索引。
2. 增加 semantic-search 调试接口。
3. 实现 semantic hit 回灌 Neo4j canonical evidence。
4. 增加索引健康检查。
5. 用 10 条典型学生问题做手动验收。
6. 前端展示 semantic hits。
7. Agent 根据 semantic view type 调整回答策略。
8. 扩充高质量 paraphrase semantic views。
9. 建立自动化检索质量评测集。
10. 再考虑切换 `bge-m3` 或 `text-embedding-3-large` 做效果对比。

## 8. 风险

### 8.1 向量库变成第二事实源

风险：

- FAQ、练习、代码案例在 Neo4j 和 Chroma 中各存一份事实。
- 两边不一致时，Agent 可能引用错误内容。

解决：

- Chroma 只存 semantic view。
- 回答、引用、资源生成必须回查 Neo4j canonical evidence。

### 8.2 embedding 维度不匹配

风险：

- 模型从 1536 维切到 3072 维后，旧 collection 不能继续用。

解决：

- collection metadata 记录 dimension。
- 启动时检查模型维度和 collection 维度。
- 不匹配时提示重建索引。

### 8.3 静默降级导致误判

风险：

- embedding key 没配、索引为空、Chroma 不可用时，系统仍然返回 GraphRAG 结果。
- 看起来“能用”，但其实课程语义 RAG 没参与。

解决：

- health endpoint 暴露状态。
- 调试面板显示 semantic index status。
- 开发环境中对索引为空给出明显 warning。

### 8.4 模板语义视图召回质量不足

风险：

- 学生真实问法和模板文本差异大。

解决：

- 离线生成 paraphrase views。
- 建立真实问法评测集。
- 对低召回 query 进行 targeted augmentation。

## 9. 当前结论

短期不要纠结“课程内容到底放 Neo4j 还是向量库”。结论是：

```text
Neo4j 放事实。
Chroma 放问法、意图、困惑和语义入口。
GraphRAG 负责把两者合成可解释证据包。
Agent 负责把证据包转化成个性化学习服务。
```

这条路线最符合当前项目目标：不是做一个普通 RAG demo，而是做一个能解释、能追踪、能个性化更新的学习系统。
