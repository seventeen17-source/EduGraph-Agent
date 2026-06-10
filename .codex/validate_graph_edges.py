import json
from pathlib import Path

root = Path(r"d:/Code/EduGraph-Agent")
chapters = json.loads((root / "data/course/chapters.json").read_text(encoding="utf-8"))
knowledge_points = json.loads((root / "data/course/knowledge_points.json").read_text(encoding="utf-8"))
edges = json.loads((root / "data/course/graph_edges.json").read_text(encoding="utf-8"))
sources = json.loads((root / "data/sources/sources.json").read_text(encoding="utf-8"))
course_meta = json.loads((root / "data/course/course_meta.json").read_text(encoding="utf-8"))
exercises_index = json.loads((root / "data/exercises/exercises_index.json").read_text(encoding="utf-8"))

chapter_ids = {c["chapter_id"] for c in chapters}
node_ids = {n["node_id"] for n in knowledge_points}
source_ids = {s["source_id"] for s in sources}
course_ids = {course_meta["course_id"]} if isinstance(course_meta, dict) and "course_id" in course_meta else set()
exercise_ids = set()
for entry in exercises_index:
    exercise_file = root / entry["file"]
    if not exercise_file.exists():
        continue
    chapter_exercises = json.loads(exercise_file.read_text(encoding="utf-8"))
    exercise_ids.update(ex["exercise_id"] for ex in chapter_exercises.get("exercises", []))

valid_nodes = chapter_ids | node_ids | course_ids | exercise_ids

errors = []
for e in edges:
    if e["source"] not in valid_nodes:
        errors.append(f"invalid source: {e['edge_id']} -> {e['source']}")
    if e["target"] not in valid_nodes:
        errors.append(f"invalid target: {e['edge_id']} -> {e['target']}")
    for sid in e.get("source_ids", []):
        if sid not in source_ids:
            errors.append(f"invalid source_id: {e['edge_id']} -> {sid}")

if errors:
    print("VALIDATION_FAILED")
    for err in errors:
        print(err)
else:
    print(f"VALIDATION_OK edges={len(edges)}")
