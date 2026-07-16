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

    async def get_all_nodes(self, limit: int = 200) -> list[GraphNode]:
        """Return all knowledge point nodes with basic properties for full-graph overview."""
        rows = await self._run(
            """
            MATCH (k:KnowledgePoint)
            RETURN k
            ORDER BY coalesce(k.chapter, k.uid)
            LIMIT $limit
            """,
            limit=limit,
        )
        return [_node_from_neo4j(row["k"]) for row in rows]

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

    async def get_prerequisite_tree(
        self,
        uid: str,
        max_depth: int = 3,
        limit_per_level: int = 8,
    ) -> list[GraphPath]:
        """获取多跳前置依赖树。

        逐层查询，每层使用精确跳数匹配：
        - depth=1: 1-hop 直接前置
        - depth=2: 2-hop 传递前置
        - depth=3: 3-hop 更上游

        返回所有路径，按 depth 升序排列。
        """
        max_depth = max(1, min(max_depth, self.settings.max_graph_depth + 1))
        all_paths: list[GraphPath] = []
        seen_pairs: set[tuple[str, str]] = set()

        for d in range(1, max_depth + 1):
            rows = await self._run(
                f"""
                MATCH p = (pre:KnowledgePoint)-[:PREREQUISITE*{d}]->(:KnowledgePoint {{uid: $uid}})
                RETURN p
                LIMIT $limit
                """,
                uid=uid,
                limit=limit_per_level,
            )
            for row in rows:
                path = _path_from_neo4j(row["p"])
                if path.nodes:
                    pair = (path.nodes[0].uid, path.nodes[-1].uid)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        all_paths.append(path)

        # Fallback: property-based prerequisites (depth=1 only)
        if max_depth >= 1:
            fallback = await self._fallback_property_paths(uid, "prerequisites", "PREREQUISITE", limit_per_level)
            for path in fallback:
                if path.nodes:
                    pair = (path.nodes[0].uid, path.nodes[-1].uid)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        all_paths.append(path)

        return self._dedupe_paths(all_paths)

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
            MATCH (chunk:DocumentChunk)-[:SUPPORTS]->(k:KnowledgePoint {uid: $uid})
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
        if "PREREQUISITE" in rel_types:
            paths.extend(await self._fallback_property_paths(uid, "prerequisites", "PREREQUISITE", limit))
        if "RELATED" in rel_types:
            paths.extend(await self._fallback_property_paths(uid, "related", "RELATED", limit))
        nodes_by_uid: dict[str, GraphNode] = {}
        rels_by_key: dict[tuple[str, str, str], GraphRelationship] = {}
        for path in self._dedupe_paths(paths):
            for node in path.nodes:
                nodes_by_uid[node.uid] = node
            for rel in path.relationships:
                rels_by_key[(rel.source_uid, rel.type, rel.target_uid)] = rel
        if uid not in nodes_by_uid:
            center_node = await self.get_node(uid)
            if center_node is not None:
                nodes_by_uid[uid] = center_node
        return SubgraphResult(
            center_uid=uid,
            nodes=list(nodes_by_uid.values()),
            relationships=list(rels_by_key.values()),
            paths=self._dedupe_paths(paths),
        )

    async def get_node_with_mastery(self, uid: str, student_id: str) -> dict | None:
        """获取节点信息。mastery 数据由 service 层从 SQLite 补充。

        Args:
            uid: 知识点节点 uid
            student_id: 学生 ID（保留参数，mastery 由 service 层补充）

        Returns:
            包含 uid/name/type/chapter/difficulty 的字典，节点不存在时返回 None
        """
        node = await self.get_node(uid)
        if node is None:
            return None
        props = node.properties
        labels = [lb for lb in node.labels if lb != "Entity"]
        return {
            "uid": uid,
            "name": props.get("name", "") or uid,
            "type": props.get("type", "") or (labels[0] if labels else "KnowledgePoint"),
            "chapter": props.get("chapter", "") or "",
            "difficulty": props.get("difficulty", "") or "",
        }

    async def get_all_nodes_with_mastery(self, student_id: str, profile_service=None) -> list[dict]:
        """返回所有知识点节点，附带掌握度和状态。
        
        Args:
            student_id: 学生 ID
            profile_service: ProfileService 实例，用于查询掌握度
        
        Returns:
            节点列表，每项包含 uid/name/chapter/difficulty/mastery_score/status/last_practiced
            status: "mastered" | "weak" | "forgetting" | "unlearned"
        """
        rows = await self._run(
            """
            MATCH (k:KnowledgePoint)
            RETURN k.uid AS uid, k.name AS name, k.chapter AS chapter, 
                   k.difficulty AS difficulty, k.summary AS summary
            ORDER BY coalesce(k.chapter, k.uid)
            LIMIT 300
            """,
        )
        
        # 从 profile 获取掌握度
        node_mastery_map = {}
        if profile_service:
            try:
                from app.core.errors import NotFoundError
                profile = await profile_service.get_profile(student_id)
                node_mastery_map = profile.node_mastery
            except Exception:
                pass
        
        from datetime import datetime, timedelta
        now = datetime.now()
        
        result = []
        for row in rows:
            uid = row["uid"]
            mastery_score = 0.0
            last_practiced = None
            status = "unlearned"
            
            mastery = node_mastery_map.get(uid)
            if mastery is not None:
                mastery_score = mastery.mastery_score
                last_practiced = mastery.last_practiced_at
                
                if mastery_score >= 0.6:
                    # 检查遗忘风险
                    if last_practiced:
                        days_since = (now - last_practiced).days
                        if days_since > 14:
                            status = "forgetting"
                        else:
                            status = "mastered"
                    else:
                        status = "mastered"
                elif mastery_score < 0.4:
                    status = "weak"
                else:
                    status = "learning"
            
            result.append({
                "uid": uid,
                "name": row["name"] or uid,
                "chapter": row["chapter"] or "",
                "difficulty": row["difficulty"] or "",
                "summary": row["summary"] or "",
                "mastery_score": round(mastery_score, 2),
                "status": status,
                "last_practiced": last_practiced.strftime("%Y-%m-%d") if last_practiced else None,
            })
        
        return result

    async def get_edges_with_weight(self, uid: str, direction: str = "both") -> list[dict]:
        """获取节点的边信息，包含权重和解释。

        权重逻辑：
            - 直接前置依赖（PREREQUISITE 1跳）: 1.0
            - 间接前置（PREREQUISITE 2跳）: 0.6
            - 相关概念（RELATED_TO）: 0.4

        Args:
            uid: 知识点节点 uid
            direction: "prerequisites" | "next" | "both"

        Returns:
            边信息列表，每项包含 uid/name/weight/explanation/relation_type/direction/depth
        """
        edges: list[dict] = []
        seen: set[tuple[str, str]] = set()

        center_node = await self.get_node(uid)
        center_name = (center_node.properties.get("name", "") if center_node else "") or uid

        def _add_edge(
            target_uid: str,
            target_name: str,
            weight: float,
            relation_type: str,
            edge_direction: str,
            depth: int,
            source_name: str,
            target_label: str,
        ) -> None:
            key = (target_uid, edge_direction)
            if key in seen:
                return
            seen.add(key)
            if relation_type == "PREREQUISITE":
                explanation = (
                    f"{source_name} 是 {target_label} 的前置知识，"
                    f"掌握 {source_name} 是理解 {target_label} 的基础"
                )
            else:
                explanation = f"{source_name} 与 {target_label} 是相关概念，学习时可以互相参照"
            edges.append({
                "uid": target_uid,
                "name": target_name or target_uid,
                "weight": weight,
                "explanation": explanation,
                "relation_type": relation_type,
                "direction": edge_direction,
                "depth": depth,
            })

        # 1. 前置依赖（prerequisites）
        if direction in ("prerequisites", "both"):
            # 1-hop 直接前置: pre -> this
            rows = await self._run(
                """
                MATCH (pre:KnowledgePoint)-[:PREREQUISITE]->(k:KnowledgePoint {uid: $uid})
                RETURN pre.uid AS uid, pre.name AS name
                LIMIT 20
                """,
                uid=uid,
            )
            for row in rows:
                pre_name = row["name"] or row["uid"]
                _add_edge(
                    target_uid=row["uid"],
                    target_name=pre_name,
                    weight=1.0,
                    relation_type="PREREQUISITE",
                    edge_direction="prerequisite",
                    depth=1,
                    source_name=pre_name,
                    target_label=center_name,
                )

            # 2-hop 间接前置: pre -> mid -> this（排除已有直接边的节点）
            rows = await self._run(
                """
                MATCH (pre:KnowledgePoint)-[:PREREQUISITE*2]->(k:KnowledgePoint {uid: $uid})
                WHERE NOT (pre)-[:PREREQUISITE]->(k)
                RETURN DISTINCT pre.uid AS uid, pre.name AS name
                LIMIT 20
                """,
                uid=uid,
            )
            for row in rows:
                pre_name = row["name"] or row["uid"]
                _add_edge(
                    target_uid=row["uid"],
                    target_name=pre_name,
                    weight=0.6,
                    relation_type="PREREQUISITE",
                    edge_direction="prerequisite",
                    depth=2,
                    source_name=pre_name,
                    target_label=center_name,
                )

        # 2. 后续节点（next_nodes）: this -> PREREQUISITE -> next
        if direction in ("next", "both"):
            rows = await self._run(
                """
                MATCH (k:KnowledgePoint {uid: $uid})-[:PREREQUISITE]->(next:KnowledgePoint)
                RETURN next.uid AS uid, next.name AS name
                LIMIT 20
                """,
                uid=uid,
            )
            for row in rows:
                next_name = row["name"] or row["uid"]
                _add_edge(
                    target_uid=row["uid"],
                    target_name=next_name,
                    weight=1.0,
                    relation_type="PREREQUISITE",
                    edge_direction="next",
                    depth=1,
                    source_name=center_name,
                    target_label=next_name,
                )

        # 3. 相关概念（related）
        rows = await self._run(
            """
            MATCH (k:KnowledgePoint {uid: $uid})-[:RELATED|EXTENDS|CONTRASTS]-(r:KnowledgePoint)
            RETURN DISTINCT r.uid AS uid, r.name AS name
            LIMIT 20
            """,
            uid=uid,
        )
        for row in rows:
            rel_name = row["name"] or row["uid"]
            _add_edge(
                target_uid=row["uid"],
                target_name=rel_name,
                weight=0.4,
                relation_type="RELATED_TO",
                edge_direction="related",
                depth=1,
                source_name=center_name,
                target_label=rel_name,
            )

        return edges

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
