"""ensure_thread_owners_have_thread_user_entries

Revision ID: 780d01163600
Revises: 77ea140e8a7c
Create Date: 2025-07-29 18:47:00.781876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '780d01163600'
down_revision: Union[str, Sequence[str], None] = '77ea140e8a7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure all thread owners have thread_user entries."""
    # Create thread_user entries for all thread owners who don't already have one
    op.execute("""
        INSERT INTO thread_users (thread_id, user_id, role, created_at, updated_at)
        SELECT
            t.id as thread_id,
            t.user_id,
            'admin' as role,
            CURRENT_TIMESTAMP as created_at,
            CURRENT_TIMESTAMP as updated_at
        FROM threads t
        WHERE NOT EXISTS (
            SELECT 1
            FROM thread_users tu
            WHERE tu.thread_id = t.id
            AND tu.user_id = t.user_id
        )
    """)


def downgrade() -> None:
    """Remove thread_user entries that match thread owners and have admin role."""
    # Only remove thread_user entries where user_id = thread.user_id and role = 'admin'
    # This preserves any manually added thread_user entries
    op.execute("""
        DELETE FROM thread_users tu
        USING threads t
        WHERE tu.thread_id = t.id
        AND tu.user_id = t.user_id
        AND tu.role = 'admin'
    """)
