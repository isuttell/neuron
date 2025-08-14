"""fix unique constraint for micro app data

Revision ID: a592347cd959
Revises: a88a8902e447
Create Date: 2025-08-14 15:45:10.239486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a592347cd959'
down_revision: Union[str, Sequence[str], None] = 'a88a8902e447'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the incorrect unique constraint
    op.drop_constraint('uq_app_user_data', 'micro_app_data', type_='unique')

    # Clean up duplicate records - keep only the most recent record for each app_id/user_id pair
    op.execute("""
        DELETE FROM micro_app_data
        WHERE id NOT IN (
            SELECT DISTINCT ON (app_id, user_id) id
            FROM micro_app_data
            ORDER BY app_id, user_id, created_at DESC
        )
    """)

    # Add the correct unique constraint (prevent duplicate user data per app)
    op.create_unique_constraint('uq_app_user_data', 'micro_app_data', ['app_id', 'user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Restore the original (incorrect) constraint
    op.drop_constraint('uq_app_user_data', 'micro_app_data', type_='unique')
    op.create_unique_constraint('uq_app_user_data', 'micro_app_data', ['app_id', 'user_id', 'id'])
