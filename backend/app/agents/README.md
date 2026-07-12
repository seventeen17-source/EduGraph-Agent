# Agents

LangChain-backed learning resource generation agents.

Current scope:

- `DocumentAgent`: generate grounded Markdown explanations.
- `MindmapAgent`: generate Mermaid mind maps.
- `ExerciseAgent`: generate structured exercises.
- `VideoScriptAgent`: generate storyboard-style video scripts.
- `CodeAgent`: generate Python code cases.
- `QualityAgent`: produce a lightweight grounding report.

The first API entrypoint is:

```text
POST /api/agents/generate-resources
```

The agents reuse the existing GraphRAG evidence package before calling the LLM. LangGraph orchestration can wrap this package later without changing the public response shape.
