from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship, Mapped, sessionmaker
import uuid
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from neuron_server.config import config
from sqlalchemy.pool import NullPool
from psycopg_pool import AsyncConnectionPool, AsyncNullConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neuron_server.logger import logger
import asyncio

DB_URI = f"{config.database.user}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.database}"


engine = create_async_engine(
    f"postgresql+psycopg://{DB_URI}",
    poolclass=NullPool,  # require until we sort out the event loop
)

Base = declarative_base()


class ProviderModel(Base):
    __tablename__ = "provider_models"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    model_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Personality(Base):
    __tablename__ = "personalities"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    context = Column(Text, nullable=False, default="")
    memory = Column(Text, nullable=False, default="")
    logo = Column(Text, nullable=True)
    tool_set = Column(Text, nullable=True, default=None)
    description = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    threads: Mapped[List["Thread"]] = relationship(
        back_populates="personality", cascade="all, delete-orphan"
    )
    prompts: Mapped[List["Prompt"]] = relationship(
        back_populates="personality", cascade="all, delete-orphan"
    )


class Thread(Base):
    __tablename__ = "threads"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, default="")
    context = Column(Text, default="")
    memory = Column(Text, default="")
    status = Column(String, default="idle")
    message_count = Column(Integer, default=0)
    user_id = Column(String, nullable=False, index=True)
    personality_id = Column(
        pgUUID(as_uuid=True),
        ForeignKey("personalities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    personality: Mapped["Personality"] = relationship(back_populates="threads")


class Message(Base):
    __tablename__ = "messages"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(
        pgUUID(as_uuid=True),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False, default="")
    role = Column(String, nullable=False)
    tool_call_id = Column(Text, nullable=True)
    tool_calls = Column(JSON, nullable=False, default=list)
    usage_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LangchainPGCollection(Base):
    __tablename__ = "langchain_pg_collection"

    uuid = Column(pgUUID, primary_key=True, nullable=False)
    name = Column(String, nullable=False, unique=True)
    cmetadata = Column(JSON, nullable=True)
    embeddings: Mapped[List["LangchainPGEmbedding"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )


class LangchainPGEmbedding(Base):
    __tablename__ = "langchain_pg_embedding"

    id = Column(String, primary_key=True)
    collection_id = Column(
        pgUUID,
        ForeignKey("langchain_pg_collection.uuid", ondelete="CASCADE"),
        nullable=True,
    )
    embedding = Column(Vector(), nullable=True)
    document = Column(String, nullable=True)
    cmetadata = Column(JSONB, nullable=True)
    collection: Mapped[Optional["LangchainPGCollection"]] = relationship(
        back_populates="embeddings"
    )


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    personality_id = Column(
        pgUUID(as_uuid=True),
        ForeignKey("personalities.id", ondelete="CASCADE"),
        nullable=True,
    )
    personality: Mapped["Personality"] = relationship(back_populates="prompts")


# Create async session maker
get_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


pool = AsyncNullConnectionPool(
    conninfo=f"postgresql://{DB_URI}",
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
    open=False,
)


async def start():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await pool.open(wait=True)
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()


async def test_database():
    from sqlalchemy import select

    async with get_session() as session:
        results = await session.execute(select(Thread))
        print(results.scalars().all())


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_database())
