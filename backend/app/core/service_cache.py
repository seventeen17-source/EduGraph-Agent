from typing import Optional

from neo4j import AsyncDriver

from app.core.config import Settings, get_settings
from app.db.neo4j import neo4j_client
from app.diagnosis.service import DiagnosisService
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.service import GraphRAGService
from app.profile.extractor import ProfileExtractor


class ServiceCache:
    _instance: Optional["ServiceCache"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, driver: AsyncDriver, settings: Settings) -> None:
        if self._initialized:
            return

        self.graph_store = Neo4jGraphStore(driver=driver, settings=settings)
        self.graphrag_service = GraphRAGService(self.graph_store)
        self.diagnosis_service = DiagnosisService(self.graph_store)
        self.profile_extractor = ProfileExtractor(settings)

        self._initialized = True

    def shutdown(self) -> None:
        self._initialized = False
        self.graph_store = None
        self.graphrag_service = None
        self.diagnosis_service = None
        self.profile_extractor = None

    @property
    def is_initialized(self) -> bool:
        return self._initialized


_service_cache = ServiceCache()


def get_service_cache() -> ServiceCache:
    return _service_cache


async def initialize_service_cache() -> None:
    settings = get_settings()
    await neo4j_client.connect()
    assert neo4j_client.driver is not None
    _service_cache.initialize(neo4j_client.driver, settings)


async def shutdown_service_cache() -> None:
    _service_cache.shutdown()