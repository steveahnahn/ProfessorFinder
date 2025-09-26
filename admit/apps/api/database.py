import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from supabase import create_client, Client

from config import settings


class DatabaseManager:
    """Database connection manager for PostgreSQL via asyncpg."""

    def __init__(self):
        self._pool: asyncpg.Pool = None

    async def initialize(self):
        """Initialize the database connection pool."""
        self._pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=20,
            command_timeout=60
        )

    async def close(self):
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection from the pool."""
        if not self._pool:
            raise RuntimeError("Database not initialized")

        async with self._pool.acquire() as conn:
            yield conn

    async def execute_query(self, query: str, *args):
        """Execute a query and return results."""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)

    async def execute_one(self, query: str, *args):
        """Execute a query and return single result."""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)


class SupabaseManager:
    """Supabase client manager."""

    def __init__(self):
        self._client: Client = None

    def initialize(self):
        """Initialize Supabase client."""
        self._client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )

    @property
    def client(self) -> Client:
        """Get Supabase client."""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        return self._client


# Global instances
db = DatabaseManager()
supabase = SupabaseManager()


async def init_database():
    """Initialize database connections."""
    await db.initialize()
    supabase.initialize()


async def close_database():
    """Close database connections."""
    await db.close()