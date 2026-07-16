# Agents

LangChain-backed learning resource generation agents.

Current scope:

- `DocumentAgent`: generate grounded Markdown explanations.
- `MindmapAgent`: generate Mermaid mind maps.
- `ExerciseAgent`: generate structured exercises.
- `VideoScriptAgent`: generate storyboard-style video scripts.
- `CodeAgent`: generate Python code cases.
- `ImageAgent`: generate concept illustration images (Xunfei HiDream).

All agents implement a **generate-validate-repair-revalidate** chain: if the first output fails validation, an LLM repair pass is attempted before failing.

API entrypoints:

```text
POST /api/agents/generate-resources   # generate multiple resource types
POST /api/agents/retry                # retry a single failed resource type
GET  /api/agents/resource-types       # list available resource types
```

The agents reuse the existing GraphRAG evidence package before calling the LLM.
