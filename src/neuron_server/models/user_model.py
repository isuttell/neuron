from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

# Import the SQLAlchemy model and session factory
from neuron_server.controllers.auth import TokenPayload
from neuron_server.database import User as DBUser
from neuron_server.database import get_session


class UserModel(BaseModel):
    id: str = Field(description="Auth0 user_id")
    email: str = Field(description="User email")
    nickname: str = Field(description="User nickname")
    picture: str | None = Field(description="User picture URL", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @classmethod
    async def upsert_from_payload(cls, payload: TokenPayload) -> None:
        """
        Upserts user information into the database based on the token payload.
        """
        async with get_session() as session:
            stmt = insert(DBUser).values(
                id=payload.user_id,
                email=payload.email,
                nickname=payload.nickname,
                picture=payload.picture,
            )
            # Define the update part for the ON CONFLICT clause
            update_dict = {
                "email": stmt.excluded.email,
                "nickname": stmt.excluded.nickname,
                "picture": stmt.excluded.picture,
                "updated_at": func.now(),
            }
            # Create the ON CONFLICT DO UPDATE statement (upsert)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["id"],  # Conflict target is the primary key 'id'
                set_=update_dict,
            )
            await session.execute(upsert_stmt)
            await session.commit()

    @classmethod
    async def get_by_ids(cls, user_ids: list[str]) -> list["UserModel"]:
        """
        Retrieve users by their IDs.

        Args:
            user_ids: List of user IDs to fetch

        Returns:
            List of UserModel instances
        """
        if not user_ids:
            return []

        async with get_session() as session:
            stmt = select(DBUser).where(DBUser.id.in_(user_ids))
            result = await session.execute(stmt)
            users = result.scalars().all()

            return [cls.model_validate(user.__dict__) for user in users]
