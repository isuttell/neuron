from typing import List
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import relationship, Mapped, sessionmaker
import uuid
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from neuron_server.config import config
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    f"postgresql+asyncpg://{config.database.user}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.database}",
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    threads: Mapped[List["Thread"]] = relationship(
        back_populates="personality", cascade="all, delete-orphan"
    )


class Thread(Base):
    __tablename__ = "threads"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, default="")
    context = Column(Text, default="")
    memory = Column(Text, default="")
    status = Column(String, default="idle")
    personality_id = Column(
        pgUUID(as_uuid=True),
        ForeignKey("personalities.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[List["Message"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    personality: Mapped["Personality"] = relationship(back_populates="threads")

    @hybrid_property
    def message_count(self) -> int:
        return len(self.messages)


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
    thread: Mapped["Thread"] = relationship(back_populates="messages")


# Create async session maker
get_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def test_database():
    from sqlalchemy import select

    async with get_session() as session:
        results = await session.execute(select(Thread))
        print(results.scalars().all())


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_database())
