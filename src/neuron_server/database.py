import asyncio
import uuid
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pgvector.sqlalchemy import Vector
from psycopg_pool import AsyncNullConnectionPool
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, relationship, sessionmaker
from sqlalchemy.pool import NullPool

from neuron_server.config import config

DB_URI = (
    f"{config.database.user}:{config.database.password}"
    f"@{config.database.host}:{config.database.port}"
    f"/{config.database.database}"
)


engine = create_async_engine(
    f"postgresql+psycopg://{DB_URI}",
    poolclass=NullPool,  # require until we sort out the event loop
)

Base = declarative_base()


class ProviderModel(Base):
    __tablename__ = "provider_models"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    model_id = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    default = Column(Boolean, nullable=False, default=False)
    caching_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Personality(Base):
    __tablename__ = "personalities"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    context = Column(Text, nullable=False, default="")
    memory = Column(Text, nullable=False, default="")
    logo = Column(Text, nullable=True)
    tool_set = Column(Text, nullable=True, default=None)
    description = Column(Text, nullable=False, default="")
    default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    threads: Mapped[list["Thread"]] = relationship(
        back_populates="personality", cascade="all, delete-orphan"
    )
    prompts: Mapped[list["Prompt"]] = relationship(
        back_populates="personality", cascade="all, delete-orphan"
    )
    personality_users: Mapped[list["PersonalityUser"]] = relationship(
        back_populates="personality", cascade="all, delete-orphan"
    )


class Thread(Base):
    __tablename__ = "threads"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, default="")
    context = Column(Text, default="")
    memory = Column(Text, default="")
    status = Column(String, default="idle")
    message_count = Column(Integer, default=0)
    user_id = Column(String, nullable=False, index=True)
    personality_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("personalities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    personality: Mapped["Personality"] = relationship(back_populates="threads")
    media_items: Mapped[list["MediaItem"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    thread_users: Mapped[list["ThreadUser"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )


class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, default="")
    description = Column(Text, default="")
    url = Column(Text, nullable=False)
    media_type = Column(String, nullable=False)
    thread_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(String, nullable=False, index=True)
    thread: Mapped[Optional["Thread"]] = relationship(back_populates="media_items")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    media_list_items: Mapped[list["MediaListItem"]] = relationship(
        back_populates="media_item", cascade="all, delete-orphan"
    )


class MediaListItem(Base):
    __tablename__ = "media_list_items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    index = Column(Integer, nullable=False)
    media_list_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_item_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    media_list: Mapped["MediaList"] = relationship(back_populates="items")
    media_item: Mapped["MediaItem"] = relationship(back_populates="media_list_items")


class MediaList(Base):
    __tablename__ = "media_lists"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    user_id = Column(String, nullable=False, index=True)
    visibility = Column(String, nullable=False, default="private")
    shared_with = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    items: Mapped[list["MediaListItem"]] = relationship(
        back_populates="media_list", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(
        PG_UUID(as_uuid=True),
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

    uuid = Column(PG_UUID, primary_key=True, nullable=False)
    name = Column(String, nullable=False, unique=True)
    cmetadata = Column(JSON, nullable=True)
    embeddings: Mapped[list["LangchainPGEmbedding"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )


class LangchainPGEmbedding(Base):
    __tablename__ = "langchain_pg_embedding"

    id = Column(String, primary_key=True)
    collection_id = Column(
        PG_UUID,
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

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    personality_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("personalities.id", ondelete="CASCADE"),
        nullable=True,
    )
    personality: Mapped["Personality"] = relationship(back_populates="prompts")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # Auth0 user_id
    email = Column(String, nullable=False, unique=True)
    nickname = Column(String, nullable=False)
    picture = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    thread_users: Mapped[list["ThreadUser"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    personality_users: Mapped[list["PersonalityUser"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ThreadUser(Base):
    __tablename__ = "thread_users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String, nullable=False, default="user")  # 'admin' or 'user'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Ensure each user is only associated with a thread once
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="unique_thread_user"),
    )

    # Relationships
    thread: Mapped["Thread"] = relationship("Thread", back_populates="thread_users")
    user: Mapped["User"] = relationship("User", back_populates="thread_users")


class PersonalityUser(Base):
    __tablename__ = "personality_users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personality_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("personalities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String, nullable=False, default="user")  # 'admin' or 'user'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Ensure each user is only associated with a personality once
    __table_args__ = (
        UniqueConstraint("personality_id", "user_id", name="unique_personality_user"),
    )

    # Relationships
    personality: Mapped["Personality"] = relationship(
        "Personality", back_populates="personality_users"
    )
    user: Mapped["User"] = relationship("User", back_populates="personality_users")


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


async def start() -> None:
    # Disable migrations due to logging conflicts - use create_all instead
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await pool.open(wait=True)
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()


async def test_database() -> None:
    from sqlalchemy import select

    async with get_session() as session:
        results = await session.execute(select(Thread))
        print(results.scalars().all())


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_database())
