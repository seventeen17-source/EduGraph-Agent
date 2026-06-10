"""Import EduGraph-Agent graph data into Neo4j.

Usage examples:

1) Dry run (load and validate local data only)
   python Scripts/import_to_neo4j.py --dry-run

2) Import into local Neo4j
   python Scripts/import_to_neo4j.py \
       --uri bolt://localhost:7687 \
       --user neo4j \
       --password edugraph123 \
       --database neo4j \
       --drop-existing

Environment variables are also supported:
- NEO4J_URI
- NEO4J_USER
- NEO4J_PASSWORD
- NEO4J_DATABASE

This script imports:
- Course
- Chapter
- KnowledgePoint
- Source
- Exercise
- ChapterDocument / DocumentChunk
- CodeCase
- FAQ / Misconception
- Relationships from data/course/graph_edges.json

All imported nodes share a universal :Entity label and a unique `uid`.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: neo4j. Install with `pip install neo4j`."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
COURSE_DIR = DATA_DIR / "course"
DOCS_DIR = DATA_DIR / "docs"
EXERCISES_DIR = DATA_DIR / "exercises"
SOURCES_PATH = DATA_DIR / "sources" / "sources.json"
FAQ_PATH = DATA_DIR / "faq" / "misconceptions.json"
CODE_CASES_DIR = DATA_DIR / "code_cases"


@dataclass
class NodeRecord:
    labels: list[str]
    uid: str
    props: dict[str, Any]


@dataclass
class RelRecord:
    source: str
    target: str
    relation: str
    props: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import EduGraph-Agent data into Neo4j")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "edugraph123"))
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "neo4j"))
    parser.add_argument("--drop-existing", action="store_true", help="Delete all existing nodes and relationships before import")
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize data without connecting to Neo4j")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_prop_value(value: Any) -> Any:
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        if all(isinstance(v, (str, int, float, bool)) or v is None for v in value):
            return value
        return json.dumps(value, ensure_ascii=False)
    return value


def sanitize_props(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: sanitize_prop_value(v) for k, v in value.items()}
    return sanitize_prop_value(value)


def safe_rel_type(name: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9_]", "_", name.upper())
    if not cleaned or not re.fullmatch(r"[A-Z][A-Z0-9_]*", cleaned):
        raise ValueError(f"Invalid relationship type: {name}")
    return cleaned


def stem_uid(prefix: str, path: Path) -> str:
    return f"{prefix}_{path.stem}"


def parse_text_list(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        try:
            value = ast.literal_eval(raw)
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
        except Exception:
            pass
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_doc_chunks(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    chunks: list[dict[str, Any]] = []
    current_heading = ""
    in_block = False
    block_lines: list[str] = []
    block_index = 0

    for line in lines:
        if line.startswith("## "):
            current_heading = line[3:].strip()
        if line.strip().startswith("```text"):
            in_block = True
            block_lines = []
            continue
        if in_block and line.strip() == "```":
            block_index += 1
            metadata: dict[str, str] = {}
            for raw in block_lines:
                if ":" in raw:
                    key, value = raw.split(":", 1)
                    metadata[key.strip()] = value.strip()
            knowledge_node_id = metadata.get("knowledge_node_id")
            if knowledge_node_id:
                chunk_id = f"chunk_{path.stem}_{block_index:03d}_{knowledge_node_id}"
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": stem_uid("doc", path),
                        "chapter_id": path.stem.split("_")[0],
                        "section_title": current_heading,
                        "knowledge_node_id": knowledge_node_id,
                        "title": metadata.get("title", current_heading or knowledge_node_id),
                        "content": metadata.get("content", ""),
                        "keywords": parse_text_list(metadata.get("keywords", "")),
                        "source_ids": parse_text_list(metadata.get("source_ids", "")),
                        "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    }
                )
            in_block = False
            block_lines = []
            continue
        if in_block:
            block_lines.append(line)

    return chunks


def parse_code_case(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    related_node_id = None
    source_ids: list[str] = []

    related_match = re.search(r"Related node:\s*([a-zA-Z0-9_\-]+)", text)
    if related_match:
        related_node_id = related_match.group(1).strip()

    source_match = re.search(r"Source IDs:\s*(.+)", text)
    if source_match:
        value = source_match.group(1).strip()
        if value.lower() != "fill in data/sources/sources.json after collection.":
            source_ids = parse_text_list(value)

    return {
        "code_case_id": stem_uid("code", path),
        "title": path.stem,
        "language": "python",
        "related_node_id": related_node_id,
        "source_ids": source_ids,
        "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "content": text,
    }


def build_nodes_and_relationships() -> tuple[list[NodeRecord], list[RelRecord]]:
    nodes: list[NodeRecord] = []
    rels: list[RelRecord] = []

    course = load_json(COURSE_DIR / "course_meta.json")
    course_uid = course["course_id"]
    nodes.append(NodeRecord(["Entity", "Course"], course_uid, sanitize_props(course)))

    chapters = load_json(COURSE_DIR / "chapters.json")
    for chapter in chapters:
        nodes.append(NodeRecord(["Entity", "Chapter"], chapter["chapter_id"], sanitize_props(chapter)))
        rels.append(
            RelRecord(
                source=course_uid,
                target=chapter["chapter_id"],
                relation="HAS_CHAPTER",
                props={"derived": True},
            )
        )

    knowledge_points = load_json(COURSE_DIR / "knowledge_points.json")
    for point in knowledge_points:
        nodes.append(NodeRecord(["Entity", "KnowledgePoint"], point["node_id"], sanitize_props(point)))
        rels.append(
            RelRecord(
                source=point["chapter_id"],
                target=point["node_id"],
                relation="HAS_KNOWLEDGE_POINT",
                props={"derived": True},
            )
        )

    sources = load_json(SOURCES_PATH)
    for source in sources:
        nodes.append(NodeRecord(["Entity", "Source"], source["source_id"], sanitize_props(source)))

    if FAQ_PATH.exists():
        faqs = load_json(FAQ_PATH)
        for faq in faqs:
            uid = faq["faq_id"]
            nodes.append(NodeRecord(["Entity", "FAQ", "Misconception"], uid, sanitize_props(faq)))
            related_node_id = faq.get("related_node_id")
            if related_node_id:
                rels.append(
                    RelRecord(
                        source=uid,
                        target=related_node_id,
                        relation="ADDRESSES",
                        props={"derived": True},
                    )
                )
            for source_id in faq.get("source_ids", []):
                rels.append(
                    RelRecord(
                        source=uid,
                        target=source_id,
                        relation="CITES_SOURCE",
                        props={"derived": True},
                    )
                )

    for doc_path in sorted(DOCS_DIR.glob("*.md")):
        text = doc_path.read_text(encoding="utf-8")
        document_id = stem_uid("doc", doc_path)
        chapter_id = doc_path.stem.split("_")[0]
        document_props = {
            "document_id": document_id,
            "title": doc_path.stem,
            "chapter_id": chapter_id,
            "source_file": str(doc_path.relative_to(ROOT)).replace("\\", "/"),
            "content": text,
        }
        nodes.append(NodeRecord(["Entity", "Document", "ChapterDocument"], document_id, sanitize_props(document_props)))
        rels.append(
            RelRecord(
                source=chapter_id,
                target=document_id,
                relation="HAS_DOCUMENT",
                props={"derived": True},
            )
        )
        for chunk in parse_doc_chunks(doc_path):
            chunk_id = chunk["chunk_id"]
            nodes.append(NodeRecord(["Entity", "DocumentChunk"], chunk_id, sanitize_props(chunk)))
            rels.append(RelRecord(source=document_id, target=chunk_id, relation="HAS_CHUNK", props={"derived": True}))
            rels.append(RelRecord(source=chunk_id, target=chunk["knowledge_node_id"], relation="SUPPORTS", props={"derived": True}))
            for source_id in chunk.get("source_ids", []):
                rels.append(RelRecord(source=chunk_id, target=source_id, relation="CITES_SOURCE", props={"derived": True}))

    if EXERCISES_DIR.exists():
        exercises_index = load_json(EXERCISES_DIR / "exercises_index.json")
        index_uid = "exercises_index"
        nodes.append(NodeRecord(["Entity", "ExerciseIndex"], index_uid, {"uid": index_uid, "entry_count": len(exercises_index)}))
        for entry in exercises_index:
            rels.append(RelRecord(source=index_uid, target=entry["chapter_id"], relation="TRACKS_CHAPTER", props=sanitize_props(entry)))
            chapter_file = ROOT / entry["file"]
            if not chapter_file.exists():
                continue
            chapter_payload = load_json(chapter_file)
            for exercise in chapter_payload.get("exercises", []):
                uid = exercise["exercise_id"]
                nodes.append(NodeRecord(["Entity", "Exercise"], uid, sanitize_props(exercise)))
                rels.append(RelRecord(source=chapter_payload["chapter_id"], target=uid, relation="HAS_EXERCISE", props={"derived": True}))
                for source_id in exercise.get("source_ids", []):
                    rels.append(RelRecord(source=uid, target=source_id, relation="CITES_SOURCE", props={"derived": True}))

    if CODE_CASES_DIR.exists():
        for code_path in sorted(CODE_CASES_DIR.glob("*.py")):
            code_case = parse_code_case(code_path)
            uid = code_case["code_case_id"]
            nodes.append(NodeRecord(["Entity", "CodeCase"], uid, sanitize_props(code_case)))
            if code_case.get("related_node_id"):
                rels.append(RelRecord(source=uid, target=code_case["related_node_id"], relation="PRACTICES", props={"derived": True}))
            for source_id in code_case.get("source_ids", []):
                rels.append(RelRecord(source=uid, target=source_id, relation="CITES_SOURCE", props={"derived": True}))

    graph_edges = load_json(COURSE_DIR / "graph_edges.json")
    for edge in graph_edges:
        props = sanitize_props({k: v for k, v in edge.items() if k not in {"source", "target", "relation"}})
        rels.append(RelRecord(source=edge["source"], target=edge["target"], relation=edge["relation"], props=props))

    for chapter in chapters:
        for source_id in chapter.get("source_ids", []):
            rels.append(RelRecord(source=chapter["chapter_id"], target=source_id, relation="CITES_SOURCE", props={"derived": True}))

    return nodes, rels


class Neo4jImporter:
    def __init__(self, uri: str, user: str, password: str, database: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params: Any) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(query, **params)
            return [record.data() for record in result]

    def clear(self) -> None:
        self.run("MATCH (n) DETACH DELETE n")

    def create_constraints(self) -> None:
        self.run("CREATE CONSTRAINT entity_uid IF NOT EXISTS FOR (n:Entity) REQUIRE n.uid IS UNIQUE")
        self.run("CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:Source) REQUIRE n.source_id IS UNIQUE")

    def upsert_node(self, node: NodeRecord) -> None:
        labels = ":".join(node.labels)
        props = dict(node.props)
        props["uid"] = node.uid
        query = f"MERGE (n:{labels} {{uid: $uid}}) SET n += $props"
        self.run(query, uid=node.uid, props=props)

    def upsert_relationship(self, rel: RelRecord) -> None:
        rel_type = safe_rel_type(rel.relation)
        props = dict(rel.props)
        query = (
            f"MATCH (s:Entity {{uid: $source}}), (t:Entity {{uid: $target}}) "
            f"MERGE (s)-[r:{rel_type} {{_key: $key}}]->(t) "
            f"SET r += $props"
        )
        key = props.get("edge_id") or f"derived::{rel.source}::{rel.relation}::{rel.target}"
        props["_key"] = key
        self.run(query, source=rel.source, target=rel.target, key=key, props=props)

    def counts(self) -> dict[str, int]:
        node_count = self.run("MATCH (n) RETURN count(n) AS count")[0]["count"]
        rel_count = self.run("MATCH ()-[r]->() RETURN count(r) AS count")[0]["count"]
        return {"nodes": node_count, "relationships": rel_count}


def summarize(nodes: list[NodeRecord], rels: list[RelRecord]) -> str:
    label_counter: dict[str, int] = {}
    rel_counter: dict[str, int] = {}
    for node in nodes:
        for label in node.labels:
            label_counter[label] = label_counter.get(label, 0) + 1
    for rel in rels:
        rel_counter[rel.relation] = rel_counter.get(rel.relation, 0) + 1

    parts = [
        f"nodes={len(nodes)}",
        f"relationships={len(rels)}",
        "node_labels=" + ", ".join(f"{k}:{v}" for k, v in sorted(label_counter.items())),
        "relation_types=" + ", ".join(f"{k}:{v}" for k, v in sorted(rel_counter.items())),
    ]
    return "\n".join(parts)


def main() -> None:
    args = parse_args()
    nodes, rels = build_nodes_and_relationships()
    print(summarize(nodes, rels))

    if args.dry_run:
        print("Dry run completed. No data written to Neo4j.")
        return

    if not args.password:
        raise SystemExit("NEO4J_PASSWORD is required unless --dry-run is used.")

    importer = Neo4jImporter(args.uri, args.user, args.password, args.database)
    try:
        if args.drop_existing:
            importer.clear()
        importer.create_constraints()
        for node in nodes:
            importer.upsert_node(node)
        for rel in rels:
            importer.upsert_relationship(rel)
        counts = importer.counts()
        print(f"Import completed: nodes={counts['nodes']}, relationships={counts['relationships']}")
    finally:
        importer.close()


if __name__ == "__main__":
    main()
