from typing import Any

from neo4j import AsyncDriver

from app.core.config import Settings
from app.graph.models import GraphNode, GraphPath, GraphRelationship, SubgraphResult


def _node_from_neo4j(node: Any) -> GraphNode:
    props = dict(node)
    uid = props.get("uid")
    return GraphNode(uid=uid, labels=list(node.labels), properties=props)


def _relationship_from_neo4j(rel: Any) -> GraphRelationship:
    props = dict(rel)
    return GraphRelationship(
        type=rel.type,
        source_uid=rel.start_node.get("uid"),
        target_uid=rel.end_node.get("uid"),
        properties=props,
    )


def _path_from_neo4j(path: Any) -> GraphPath:
    return GraphPath(
        nodes=[_node_from_neo4j(node) for node in path.nodes],
        relationships=[_relationship_from_neo4j(rel) for rel in path.relationships],
    )


def _safe_relations(relations: list[str]) -> list[str]:
    safe = []
    for relation in relations:
        upper = relation.upper()
        if upper.replace("_", "").isalnum() and upper[0].isalpha():
            safe.append(upper)
    return safe


class Neo4jGraphStore:
    """Graph query adapter. It does not orchestrate GraphRAG business flow."""

    def __init__(self, driver: AsyncDriver, settings: Settings) -> None:
        self.driver = driver
        self.settings = settings

    async def _run(self, query: str, **params: Any) -> list[Any]:
        async with self.driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, **params)
            return [record async for record in result]

    async def get_node(self, uid: str) -> GraphNode | None:
        rows = await self._run("MATCH (n:Entity {uid: $uid}) RETURN n LIMIT 1", uid=uid)
        return _node_from_neo4j(rows[0]["n"]) if rows else None

    async def search_knowledge_points(self, keyword: str, limit: int = 10) -> list[GraphNode]:
        like = keyword.lower()
        rows = await self._run(
            """
            MATCH (k:KnowledgePoint)
            WHERE toLower(coalesce(k.uid, "")) CONTAINS $like
               OR $like CONTAINS toLower(coalesce(k.uid, ""))
               OR toLower(coalesce(k.name, "")) CONTAINS $like
               OR $like CONTAINS toLower(coalesce(k.name, ""))
               OR any(alias IN coalesce(k.aliases, []) WHERE toLower(alias) CONTAINS $like OR $like CONTAINS toLower(alias))
               OR any(term IN coalesce(k.keywords, []) WHERE toLower(term) CONTAINS $like OR $like CONTAINS toLower(term))
            RETURN k
            LIMIT $limit
            """,
            like=like,
            limit=limit,
        )
        return [_node_from_neo4j(row["k"]) for row in rows]

    async def get_prerequisites(self, uid: str, depth: int = 1, limit: int = 8) -> list[GraphPath]:
        depth = max(1, min(depth, self.settings.max_graph_depth))
        rows = await self._run(
            f"""
            MATCH p = (pre:KnowledgePoint)-[:PREREQUISITE*1..{depth}]->(:KnowledgePoint {{uid: $uid}})
            RETURN p
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        paths = [_path_from_neo4j(row["p"]) for row in rows]
        paths.extend(await self._fallback_property_paths(uid, "prerequisites", "PREREQUISITE", limit))
        return self._dedupe_paths(paths)[:limit]

    async def get_related_nodes(self, uid: str, limit: int = 8) -> list[GraphPath]:
        rows = await self._run(
            """
            MATCH p = (:KnowledgePoint {uid: $uid})-[:RELATED|EXTENDS|CONTRASTS]-(:KnowledgePoint)
            RETURN p
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        paths = [_path_from_neo4j(row["p"]) for row in rows]
        paths.extend(await self._fallback_property_paths(uid, "related", "RELATED", limit))
        return self._dedupe_paths(paths)[:limit]

    async def get_exercises_for_node(self, uid: str, limit: int = 8) -> list[GraphNode]:
        rows = await self._run(
            """
            MATCH (:Exercise)-[:ASSESSES]->(k:KnowledgePoint {uid: $uid})
            WITH k
            MATCH (e:Exercise)-[:ASSESSES]->(k)
            RETURN DISTINCT e
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        return [_node_from_neo4j(row["e"]) for row in rows]

    async def get_document_chunks_for_node(self, uid: str, limit: int = 6) -> list[GraphNode]:
        rows = await self._run(
            """
            MATCH (chunk:DocumentChunk)-[:SUPPORTS]->(:KnowledgePoint {uid: $uid})
            RETURN DISTINCT chunk
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        return [_node_from_neo4j(row["chunk"]) for row in rows]

    async def get_code_cases_for_node(self, uid: str, limit: int = 3) -> list[GraphNode]:
        rows = await self._run(
            """
            MATCH (code:CodeCase)-[:PRACTICES]->(:KnowledgePoint {uid: $uid})
            RETURN DISTINCT code
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        return [_node_from_neo4j(row["code"]) for row in rows]

    async def get_sources_for_entity(self, uid: str, limit: int = 10) -> list[GraphNode]:
        rows = await self._run(
            """
            MATCH (:Entity {uid: $uid})-[:CITES_SOURCE]->(source:Source)
            RETURN DISTINCT source
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        return [_node_from_neo4j(row["source"]) for row in rows]

    async def get_misconceptions_for_node(self, uid: str, limit: int = 5) -> list[GraphNode]:
        rows = await self._run(
            """
            MATCH (m:Misconception)-[:ADDRESSES]->(:KnowledgePoint {uid: $uid})
            RETURN DISTINCT m
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        return [_node_from_neo4j(row["m"]) for row in rows]

    async def get_subgraph(
        self,
        uid: str,
        relation_types: list[str],
        depth: int = 1,
        limit: int = 80,
    ) -> SubgraphResult:
        depth = max(1, min(depth, self.settings.max_graph_depth))
        rel_types = _safe_relations(relation_types)
        if not rel_types:
            return SubgraphResult(center_uid=uid)

        rel_pattern = ":" + "|".join(rel_types)
        rows = await self._run(
            f"""
            MATCH p = (:Entity {{uid: $uid}})-[{rel_pattern}*1..{depth}]-(:Entity)
            RETURN p
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        paths = [_path_from_neo4j(row["p"]) for row in rows]
        nodes_by_uid: dict[str, GraphNode] = {}
        rels_by_key: dict[tuple[str, str, str], GraphRelationship] = {}
        for path in paths:
            for node in path.nodes:
                nodes_by_uid[node.uid] = node
            for rel in path.relationships:
                rels_by_key[(rel.source_uid, rel.type, rel.target_uid)] = rel
        return SubgraphResult(
            center_uid=uid,
            nodes=list(nodes_by_uid.values()),
            relationships=list(rels_by_key.values()),
            paths=paths,
        )

    async def _fallback_property_paths(
        self,
        uid: str,
        property_name: str,
        relation_type: str,
        limit: int,
    ) -> list[GraphPath]:
        rows = await self._run(
            f"""
            MATCH (center:KnowledgePoint {{uid: $uid}})
            UNWIND coalesce(center.{property_name}, []) AS target_uid
            MATCH (target:KnowledgePoint {{uid: target_uid}})
            RETURN center, target
            LIMIT $limit
            """,
            uid=uid,
            limit=limit,
        )
        paths: list[GraphPath] = []
        for row in rows:
            center = _node_from_neo4j(row["center"])
            target = _node_from_neo4j(row["target"])
            if relation_type == "PREREQUISITE":
                source_uid, target_uid = target.uid, center.uid
                nodes = [target, center]
            else:
                source_uid, target_uid = center.uid, target.uid
                nodes = [center, target]
            paths.append(
                GraphPath(
                    nodes=nodes,
                    relationships=[
                        GraphRelationship(
                            type=relation_type,
                            source_uid=source_uid,
                            target_uid=target_uid,
                            properties={"derived_from_property": property_name},
                        )
                    ],
                )
            )
        return paths

    def _dedupe_paths(self, paths: list[GraphPath]) -> list[GraphPath]:
        seen: set[tuple[tuple[str, ...], tuple[tuple[str, str, str], ...]]] = set()
        unique: list[GraphPath] = []
        for path in paths:
            key = (
                tuple(node.uid for node in path.nodes),
                tuple((rel.source_uid, rel.type, rel.target_uid) for rel in path.relationships),
            )
            if key not in seen:
                seen.add(key)
                unique.append(path)
        return unique
