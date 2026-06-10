---
name: edugraph-agent
description: Project-specific workflow for EduGraph-Agent, a China Software Cup A3 personalized learning multi-agent platform based on knowledge graphs, GraphRAG, and learning-resource generation. Use when Codex works in the EduGraph-Agent repository on requirements, schedule, architecture, Vue/FastAPI/LangGraph implementation, GraphRAG, student profiles, knowledge graphs, multi-agent resource generation, demo flow, PPT/video/submission materials, or scope tradeoffs for this competition project.
---

# EduGraph-Agent

## Quick Start

Use this skill to keep EduGraph-Agent work aligned with the competition goal: deliver a demonstrable personalized learning loop, not isolated AI chat features.

Start by reading the local project docs:

- `docs/project/A3_initial_development_doc.md`
- `docs/project/A3_development_schedule.md`
- `docs/project/PROJECT_PROGRESS.md`
- `docs/knowledge-base/ML_知识库收集指南.md` when collecting or structuring the machine-learning knowledge base.

If Chinese text appears mojibake in PowerShell, read files with explicit UTF-8:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[System.IO.File]::ReadAllText("docs/project/A3_initial_development_doc.md", [System.Text.Encoding]::UTF8)
```

Read `references/project-brief.md` when choosing scope, designing data models, planning milestones, building agents, or preparing demo/submission materials.

## Work Rules

Prioritize the closed learning loop:

```text
student profile -> knowledge diagnosis -> GraphRAG retrieval -> multi-agent resource generation -> learning-path planning -> learning evaluation -> profile update
```

Before implementing, classify the task:

- `P0`: Required for the competition core. Do this first.
- `P1`: Strong differentiator. Do after the P0 loop works.
- `P2`: Nice-to-have. Add only when the demo path is stable.

Keep the first runnable version simple and inspectable. Prefer deterministic demo data, visible agent inputs/outputs, and explicit evidence links over ambitious hidden automation.

After completing any project task, update `docs/project/PROJECT_PROGRESS.md`: mark completed items, add newly discovered TODOs, refresh the last-updated date, and update `docs/README.md` when new docs or major data files are added. When a long-lived rule affects future Codex or Claude behavior, keep `.codex/skills/edugraph-agent/SKILL.md` and `.claude/skills/edugraph-agent/SKILL.md` synchronized.

## Architecture Defaults

Use the project-approved stack unless the user explicitly changes direction:

- Frontend: Vue 3, TypeScript, Vite, Pinia, Vue Router, Element Plus or Ant Design Vue, ECharts or AntV G6.
- Backend: Python 3.11+, FastAPI, Pydantic, SQLAlchemy or SQLModel, SSE/WebSocket where streaming or agent status matters.
- AI orchestration: LangChain and LangGraph.
- Vector retrieval: Chroma or Milvus; fall back to FAISS, in-memory vector store, or BM25 plus embeddings for demos.
- Graph storage: Neo4j; fall back to JSON, NetworkX, PostgreSQL tables, or relational edges when deployment time is tight.

Treat GraphRAG as graph-guided retrieval for personalized learning: locate the knowledge point, expand prerequisites/related/follow-up nodes, retrieve evidence chunks, then rank by student profile, learning goal, preference, weakness, and difficulty.

## Knowledge Source Baseline

When building the machine-learning course knowledge base, treat these as the default source set and record source metadata for every document chunk, exercise, and code case. Use textbooks for understanding and self-written summaries; avoid copying long textbook passages into the repository.

Primary local textbooks/PDF references:

- 周志华《机器学习》: main Chinese machine-learning structure; use for evaluation, overfitting, decision trees, SVM, ensemble learning, supervised/unsupervised learning.
- 李航《统计学习方法》: formal algorithm definitions and derivations; use for perceptron, KNN, logistic regression, SVM, EM, HMM, CRF.
- 《动手学深度学习》Dive into Deep Learning: deep-learning explanations and runnable examples; use for neural networks, backpropagation, CNN, RNN, LSTM, Transformer, attention.
- Bishop, Pattern Recognition and Machine Learning: theory reference for probabilistic models, linear models, kernel methods, clustering, graphical models.
- Aurélien Géron, Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow: engineering reference for sklearn/Keras/TensorFlow examples and experiment workflows.
- Mathematics for Machine Learning: math foundation reference for linear algebra, calculus, probability, optimization, and gradients.
- Datawhale《南瓜书：机器学习公式详解》: Chinese formula-derivation companion for 周志华《机器学习》.
- 邱锡鹏《神经网络与深度学习》: Chinese deep-learning reference for neural networks, backpropagation, CNN/RNN, attention, and Transformer.
- 《机器学习实战：基于 Scikit-Learn、Keras 和 TensorFlow（原书第3版）》: Chinese engineering reference for sklearn/Keras/TensorFlow workflows and code cases.
- 《机器学习实战：视频教学版》: newer Chinese application-oriented reference for Python ML, classification, regression, dimensionality reduction, clustering, and project cases.

Public courses and official docs:

- Stanford CS229 Machine Learning.
- 李宏毅机器学习课程.
- Andrew Ng Machine Learning Specialization.
- MIT 6.S191 Introduction to Deep Learning.
- Stanford CS231n.
- scikit-learn User Guide.

Prefer official course pages, official documentation, public online textbooks, and self-authored summaries. Keep a `data/sources/sources.json` file once the knowledge base is created.

## Chapter Data Schema

When editing `data/course/chapters.json`, keep chapter objects rich enough to support GraphRAG, resource generation, evaluation, and demo planning. Use these fields:

- `chapter_id`, `course_id`, `title`, `order`, `summary`.
- `priority`: `P0`, `P1`, or `P2`; collect P0 first.
- `difficulty`: integer from 1 to 5.
- `estimated_hours`: estimated learning time for path planning.
- `learning_objectives`: objectives used by generation and evaluation agents.
- `key_node_ids`: core knowledge point ids from `knowledge_points.json`.
- `prerequisite_chapter_ids`: chapter-level prerequisites.
- `doc_file`: chapter Markdown path under `data/docs/`.
- `source_ids`: main references from `data/sources/sources.json`.
- `recommended_resource_types`: allowed values are `document`, `diagram`, `exercise`, `video_script`, `code_case`.
- `assessment_focus`: allowed values are `concept`, `calculation`, `coding`, `application`.
- `demo_usage`: use `main_flow`, `support`, or `extension`.
- `collection_status`: use `skeleton`, `collecting`, `drafted`, `reviewed`, or `ready`.
- `tags`: stable keywords for filtering and UI display.

Use `recommended_resource_types` to decide which resource agents should run for the chapter. Use `assessment_focus` to design exercises and learning evaluation. Use `demo_usage` to keep the competition demo centered on the core flow.

## Exercise Data Schema

Use split exercise files, not a single flat `exercises.json`.

Required layout:

- `data/exercises/exercises_index.json`
- `data/exercises/ch01_intro_evaluation.json`
- `data/exercises/ch02_math_optimization.json`
- `data/exercises/ch03_linear_models_optimization.json`
- `data/exercises/ch04_supervised_algorithms.json`
- `data/exercises/ch05_unsupervised_representation.json`
- `data/exercises/ch06_neural_deep_learning.json`
- `data/exercises/ch07_learning_theory.json`
- `data/exercises/ch08_semi_supervised.json`
- `data/exercises/ch09_probabilistic_graphical_models.json`
- `data/exercises/ch10_rule_learning.json`
- `data/exercises/ch11_reinforcement_learning.json`

Each chapter file should contain `chapter_id`, `chapter_title`, `exercise_schema_version`, `status`, `target_count`, and `exercises`.

Each exercise should use the enhanced schema: `exercise_id`, `version`, `title`, `type`, `chapter_id`, `related_node_id`, `assesses`, `also_assesses`, `prerequisite_node_ids`, `difficulty`, `estimated_minutes`, `cognitive_level`, `assessment_focus`, `question`, `options`, `answer`, `rubric`, `grading`, `test_cases`, `adaptive_feedback`, `profile_update_policy`, `misconception_tags`, `source_ids`, `created_by`, `review_status`, `quality_score`, `demo_usage`, and `tags`.

Use `assesses` to generate `ASSESSES` graph edges. Keep exercise assessment edge IDs short: `assess_<exercise_id>_<knowledge_node_id>`, for example `assess_ex_ch03_gd_001_ml_gradient_descent`. Use `profile_update_policy` to update mastery, confidence, weak points, and review recommendations after answers. First populate ch03, ch06, ch01, and ch02 before expansion chapters.

## Required Product Shape

Preserve these core concepts in code, docs, and UI decisions:

- Student profile with at least 6 dimensions; the current plan uses 8: background, goal, knowledge base, progress, cognitive style, weak points, preferences, ability state.
- One complete college course knowledge base; the preferred first course is Machine Learning.
- Course knowledge graph nodes: course, chapter, knowledge point, prerequisite, resource, exercise, code case, learning outcome.
- Graph relations: contains, prerequisite, related, supports, assesses, practices.
- At least 5 generated resource types: explanation document, mind map, exercises, video/animation script, code practice case.
- Explainability and anti-hallucination: evidence citations, knowledge-point links, answer checks, code syntax/run checks when practical, safety/risk flags, and uncertainty notes.

## Agent Pattern

Model agents as role-specific nodes or services with visible inputs and outputs. The expected roles are:

- `Profile Agent`: build and update the structured student profile.
- `Knowledge Agent`: manage course knowledge graph and graph paths.
- `Retrieval Agent`: run GraphRAG and return evidence.
- `Planning Agent`: plan learning paths and recommendation reasons.
- `Document/Mindmap/Exercise/Video/Code Agents`: generate the 5 required resource types.
- `Evaluation Agent`: assess generated quality and learning outcomes.
- `Safety Agent`: check grounding, safety, and hallucination risks.

When time is tight, keep the agents as explicit modules/functions with logs instead of over-engineering autonomous behavior.

## Demo And Submission

Optimize toward a 7-minute demo around one student scenario:

```text
Computer science sophomore, wants to learn Introduction to AI, knows Python and calculus, weak in machine learning, prefers diagrams and code, asks about gradient descent and neural-network training.
```

The demo should visibly show: profile extraction, 8-dimension profile card, graph-based prerequisite path, GraphRAG citations, 5 generated resources, learning-path recommendation, exercise/evaluation result, and profile/path update.

For submission materials, keep source, data, configuration, startup docs, test docs, open-source/license notes, and AI Coding tool usage notes aligned with the competition requirements.
