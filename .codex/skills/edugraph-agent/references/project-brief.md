# EduGraph-Agent Project Brief

## Identity

EduGraph-Agent is a China Software Cup A3 competition project: a personalized learning multi-agent system based on large models, course knowledge graphs, and GraphRAG.

Competition direction: personalized resource generation and learning multi-agent system for higher education.

Planned project period: 2026-06-01 to 2026-06-30.

Submission deadline: 2026-06-30.

Primary system goal: build a complete learning feedback loop:

```text
student profile -> knowledge diagnosis -> GraphRAG retrieval -> multi-agent resource generation -> learning-path planning -> learning-effect evaluation -> dynamic profile update
```

This project should not become only an AI Q&A chatbot. It should behave like a course learning platform.

## Priority Model

P0 means required for the competition core:

- Conversational student profile construction.
- One course knowledge base.
- Basic RAG or GraphRAG.
- Multi-agent workflow.
- 5 resource types.
- Learning-path planning.
- Demo video and documents.

P1 means strong differentiator:

- Knowledge graph visualization.
- GraphRAG recommendation reasons.
- Intelligent tutoring.
- Learning-effect evaluation.
- Dynamic profile update.
- Anti-hallucination citations.

P2 means only if time remains:

- Teacher portal.
- Resource review.
- Automatic PPT generation.
- Real video rendering.
- Agent execution visualization.
- Multi-course support.

## Milestones

| Date | Milestone | Acceptance |
| --- | --- | --- |
| 2026-06-03 | Scope freeze v0.1 | Course, core features, stack, page list clear |
| 2026-06-06 | Project skeleton | Vue, FastAPI, LangGraph minimal chain runs |
| 2026-06-10 | MVP loop | Profile -> retrieval -> resource generation -> path recommendation |
| 2026-06-14 | 5 resources | Document, mind map, exercise, video script, code case |
| 2026-06-18 | Core features | GraphRAG, profile update, path planning, resource recommendation demonstrable |
| 2026-06-21 | Add-ons v1 | Tutoring and learning evaluation demonstrable |
| 2026-06-23 | Demo flow freeze | 7-minute video flow and stable data ready |
| 2026-06-26 | Docs and PPT draft | Development docs, test docs, PPT, open-source notes |
| 2026-06-28 | Candidate package | Source, data, config, docs, video organized |
| 2026-06-30 | Final submission | Final check and upload |

From 2026-06-28 to 2026-06-30, avoid large architectural changes.

## Domain Model

StudentProfile fields:

- `student_id`
- `major`
- `grade`
- `learning_goal`
- `knowledge_base`
- `cognitive_style`
- `weak_points`
- `preferences`
- `mastery_map`
- `update_history`

CourseKnowledgeNode fields:

- `node_id`
- `name`
- `course_id`
- `chapter_id`
- `difficulty`
- `prerequisites`
- `outcomes`
- `related_resources`

LearningResource fields:

- `resource_id`
- `type`
- `title`
- `content`
- `related_nodes`
- `difficulty`
- `generated_by`
- `evidence`
- `quality_score`

LearningRecord fields:

- `record_id`
- `student_id`
- `node_id`
- `action_type`
- `score`
- `feedback`
- `timestamp`

## Course And Knowledge Graph

Preferred first course: Machine Learning.

Reason: it matches the project themes of large models, multi-agent systems, knowledge graphs, and GraphRAG; the knowledge hierarchy is clear; it is suitable for documents, exercises, code cases, and multimodal teaching materials.

Knowledge base content should include:

- Course syllabus.
- Chapter notes.
- Textbook summaries.
- Exercises and answers.
- Lab guides.
- Code cases.
- References and further reading.

Recommended source baseline for the machine-learning knowledge base:

Primary textbooks:

- 周志华《机器学习》.
- 李航《统计学习方法》.
- 《动手学深度学习》Dive into Deep Learning.
- Bishop, Pattern Recognition and Machine Learning.
- Aurélien Géron, Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow.

Public courses and official docs:

- Stanford CS229 Machine Learning.
- 李宏毅机器学习课程.
- Andrew Ng Machine Learning Specialization.
- MIT 6.S191 Introduction to Deep Learning.
- Stanford CS231n.
- scikit-learn User Guide.

Use these sources to understand and structure the course; write knowledge-base content in original wording, avoid long copied passages, and record source metadata in `data/sources/sources.json`.

Chapter records in `data/course/chapters.json` should include the chapter's `course_id`, `priority`, `difficulty`, `estimated_hours`, `learning_objectives`, `key_node_ids`, `prerequisite_chapter_ids`, `doc_file`, `source_ids`, `recommended_resource_types`, `assessment_focus`, `demo_usage`, `collection_status`, and `tags`.

Use `recommended_resource_types` to route resource generation agents, `assessment_focus` to design exercises/evaluation, and `demo_usage` to separate the main demo flow from support and extension chapters.

Knowledge graph node types:

- Course.
- Chapter.
- Knowledge point.
- Prerequisite.
- Resource.
- Exercise.
- Code case.
- Learning outcome.

Knowledge graph relation types:

- Contains: course -> chapter -> knowledge point.
- Prerequisite: required prior knowledge.
- Related: semantic association between knowledge points.
- Supports: resource supports a knowledge point.
- Assesses: exercise assesses a knowledge point.
- Practices: code case practices a knowledge point.

## Agent Roles

| Agent | Responsibility | Input | Output |
| --- | --- | --- | --- |
| Profile Agent | Build/update student profile | dialogue, behavior, tests | structured profile |
| Knowledge Agent | Manage graph | course docs, nodes, resources | relations, graph paths |
| Retrieval Agent | Execute GraphRAG | question, profile, node | evidence and citations |
| Planning Agent | Plan learning path | profile, mastery, graph | personalized path |
| Document Agent | Generate explanation doc | evidence, node, profile | Markdown document |
| Mindmap Agent | Generate mind map | node structure, chapter relations | Mermaid or JSON |
| Exercise Agent | Generate exercises | node, difficulty, weak points | choice, short-answer, coding tasks |
| Video Agent | Generate video/animation script | node, explanation, preference | storyboard and voiceover |
| Code Agent | Generate code practice | node, language, ability | code and lab steps |
| Evaluation Agent | Evaluate resource/learning quality | resources, answers, feedback | score and evaluation |
| Safety Agent | Filter hallucination/safety risks | generated content, evidence | risk flags and fixes |

## Recommended Demo Flow

Use one concrete student:

```text
Student: computer science sophomore
Goal: learn Introduction to AI for a course project
Foundation: knows Python and calculus, weak in machine learning
Preference: diagrams and code examples
Question: does not understand gradient descent and neural-network training
```

Show this path:

1. Natural-language conversation builds the profile.
2. System extracts and displays 8 profile dimensions.
3. Course graph locates "gradient descent" prerequisites.
4. GraphRAG retrieves course evidence and citations.
5. Agents generate explanation document, mind map, exercises, video script, and code case.
6. System plans a learning path and explains why.
7. Student completes exercises and system evaluates weak points.
8. Profile and learning path update.

## Fallback Decisions

When Neo4j is too heavy, use JSON edges, NetworkX, or relational tables first.

When vector database deployment is too heavy, use FAISS, LangChain in-memory store, or BM25 plus embeddings.

When video generation is too slow, generate storyboard, voiceover, and key-frame descriptions instead of real video.

When LangGraph is hard to debug, use explicit FastAPI orchestration or LangChain Runnable sequences while preserving visible agent logs.

When time is short, preserve the 5 required resource types but reduce their complexity.

## Submission Checklist

- Source code includes frontend, backend, agent orchestration, database/init scripts, sample knowledge base, model/API config, and startup instructions.
- Docs include development documentation, test documentation, user manual, open-source/license notes, and AI Coding tool usage notes.
- PPT highlights application value, technical route, innovation points, and core features.
- Demo video is under 7 minutes.
- Demo flow is stable and reproducible.
