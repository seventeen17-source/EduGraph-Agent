"""Build the course semantic-view index for Hybrid GraphRAG.

The index stores semantic retrieval views only. Each view points back to a
canonical Neo4j uid through target_uid; it is not a second source of truth.

Examples:
  python Scripts/build_course_semantic_index.py --dry-run
  python Scripts/build_course_semantic_index.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.memory.embedding import EmbeddingService  # noqa: E402
from app.rag.course_vector_store import CourseVectorStore  # noqa: E402
from app.rag.semantic_view_builder import build_course_semantic_views  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build course semantic-view vector index")
    parser.add_argument("--dry-run", action="store_true", help="Only build and summarize semantic views")
    parser.add_argument("--sample", type=int, default=5, help="Sample view count to print in dry-run")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding batch size")
    return parser.parse_args()


def summarize(views) -> dict:
    by_target_type: dict[str, int] = {}
    by_view_type: dict[str, int] = {}
    for view in views:
        by_target_type[view.target_type] = by_target_type.get(view.target_type, 0) + 1
        by_view_type[view.view_type] = by_view_type.get(view.view_type, 0) + 1
    return {
        "total": len(views),
        "by_target_type": dict(sorted(by_target_type.items())),
        "by_view_type": dict(sorted(by_view_type.items())),
    }


async def build_index(batch_size: int) -> int:
    settings = get_settings()
    views = build_course_semantic_views(ROOT)
    embedding_service = EmbeddingService(settings)
    embeddings: list[list[float]] = []
    for start in range(0, len(views), batch_size):
        batch = views[start:start + batch_size]
        batch_embeddings = await embedding_service.embed_batch([view.text for view in batch])
        embeddings.extend(batch_embeddings)
        print(f"embedded {min(start + len(batch), len(views))}/{len(views)}")

    store = CourseVectorStore(settings, embedding_dim=embedding_service.embedding_dim())
    return await store.replace_all(views, embeddings)


def main() -> None:
    args = parse_args()
    views = build_course_semantic_views(ROOT)
    print(json.dumps(summarize(views), ensure_ascii=False, indent=2))
    if args.dry_run:
        for view in views[: max(args.sample, 0)]:
            print(json.dumps(view.model_dump(), ensure_ascii=False, indent=2))
        return

    count = asyncio.run(build_index(args.batch_size))
    print(f"indexed={count}")


if __name__ == "__main__":
    main()
