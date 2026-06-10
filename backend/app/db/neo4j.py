from collections.abc import AsyncIterator

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import Settings, get_settings


class Neo4jClient:
    """Small lifecycle wrapper around the async Neo4j driver."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.driver: AsyncDriver | None = None

    async def connect(self) -> None:
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            )
            await self.driver.verify_connectivity()

    async def close(self) -> None:
        if self.driver is not None:
            await self.driver.close()
            self.driver = None

    async def healthcheck(self) -> dict[str, str]:
        await self.connect()
        assert self.driver is not None
        async with self.driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run("RETURN 'ok' AS status")
            record = await result.single()
        return {"neo4j": record["status"] if record else "unknown"}


neo4j_client = Neo4jClient(get_settings())


async def get_neo4j_driver() -> AsyncIterator[AsyncDriver]:
    await neo4j_client.connect()
    assert neo4j_client.driver is not None
    yield neo4j_client.driver
