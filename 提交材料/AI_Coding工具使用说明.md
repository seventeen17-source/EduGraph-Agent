# EduGraph-Agent AI Coding 工具使用说明

版本：1.0 · 日期：2026-07-16

> 按赛事要求："如若使用 AI Coding 工具，给出相关说明"。本项目在开发过程中使用了 AI Coding 工具，现将使用范围、方式与人工把关机制说明如下。

---

## 1. 使用的 AI Coding 工具

| 工具 | 用途 | 使用环节 |
|------|------|---------|
| **Trae**（AI IDE） | 主力 AI 辅助编程工具 | 代码生成、重构、Bug 修复、Spec 驱动开发 |
| **Claude Code**（Anthropic CLI） | 辅助工具 | 文档整理、提交材料生成、代码审查辅助 |

## 2. 工作流程：Spec 驱动 + AI 辅助 + 人工验收

本项目并非"让 AI 一键生成"，而是采用 **规格先行（Spec-Driven）** 的受控流程，全过程记录保留在仓库 `.trae/` 目录下，可审计：

```
人工撰写需求 Spec（.trae/specs/*/spec.md：Why / What Changes / Impact / Requirements）
    ↓
拆解任务清单（tasks.md）与验收清单（checklist.md）
    ↓
AI 工具按 Spec 逐任务生成/修改代码
    ↓
人工逐项审查 diff + 运行测试 + 按 checklist 验收打勾
    ↓
不合格 → 反馈修正；合格 → 提交 git
```

仓库中的过程证据：

- `.trae/specs/enhance-system-intelligence/`（spec.md / tasks.md / checklist.md）——"系统智能化增强"迭代：资源生成自修复链路、学习路径逐节点解释、画像证据链等；
- `.trae/specs/refactor-exercise-assessment/`——"练习评估重构"迭代：统一练习来源池、4 种模式、后端评分；
- `.trae/skills/edugraph/SKILL.md`——人工沉淀的项目开发规范（技术栈、目录结构、编码约定），作为 AI 工具的上下文约束，保证生成代码风格统一。

## 3. AI 参与与人工把关的分工

### 3.1 AI 工具承担的工作

- 按 Spec 生成模块代码初稿（路由/服务层/前端组件）；
- 样板代码（Pydantic Schema、SQLAlchemy 模型、API 客户端封装）；
- 重构执行（如练习评估模块按 spec 重构）；
- 错误排查建议与修复草案；
- 文档初稿（README、说明书）与注释。

### 3.2 人工完成/主导的工作

- **架构与技术选型**：LangGraph 17 节点编排设计、HybridRAG 双通道融合方案、8 维画像与行为建模方案（设计文档见 `docs/project/` 与 `docs/knowledge-base/`，均为人工撰写的设计方案）；
- **需求定义**：全部 Spec 的 Why/What/验收标准由人工撰写；
- **数据集建设**：11 章讲义、题库、FAQ、知识图谱结构（`data/`）由团队围绕课程知识体系整理编写；
- **代码审查**：AI 生成的每一处修改均经人工 review diff 后才合入；
- **测试与验收**：checklist 逐项人工验证，端到端冒烟测试人工执行确认；
- **提示词工程**：各智能体节点的 prompt 设计与调优。

## 4. 质量保障措施

1. **Spec 约束**：AI 只在明确的 Spec 范围内工作，杜绝无边界生成；
2. **Skill 规范约束**：`.trae/skills/edugraph/SKILL.md` 固化技术栈与目录规范，AI 生成代码必须符合；
3. **Checklist 验收**：每个迭代有独立 checklist，人工逐项打勾方视为完成；
4. **测试兜底**：`backend/tests/test_e2e_smoke.py` 覆盖核心闭环，改动后回归；
5. **Git 追溯**：全部变更经 git 提交，历史可查。

## 5. 诚信声明

- 本项目的**系统创意、架构设计、算法方案、数据集与最终代码质量责任**均由团队承担；
- AI Coding 工具在本项目中定位为**提效工具**（类比更强的代码补全与结对编程），不改变团队对全部交付物的著作与责任归属；
- 本说明如实披露 AI 工具使用情况，过程记录（`.trae/` 目录）随源码一并提交，可供核查。
