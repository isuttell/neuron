"""Database migration utilities for Neuron server."""

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Path to alembic.ini relative to project root
    project_root = Path(__file__).parent.parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))

    # Set the script location to the alembic directory
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))

    return alembic_cfg


async def run_migrations() -> None:
    """Run database migrations to latest version."""
    logger.info("Starting database migrations...")

    try:
        alembic_cfg = get_alembic_config()

        # Run migrations in a thread pool to avoid blocking the async loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")

        logger.info("Database migrations completed successfully")

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise


def create_migration(message: str, autogenerate: bool = True) -> None:
    """Create a new migration file."""
    alembic_cfg = get_alembic_config()

    if autogenerate:
        command.revision(alembic_cfg, message=message, autogenerate=True)
    else:
        command.revision(alembic_cfg, message=message)


def get_current_revision() -> str:
    """Get the current database revision."""
    alembic_cfg = get_alembic_config()

    # This will return the current revision
    script_directory = command.ScriptDirectory.from_config(alembic_cfg)

    return script_directory.get_current_head()


def check_migration_status() -> bool:
    """Check if database is up to date with migrations."""
    try:
        alembic_cfg = get_alembic_config()
        script_directory = command.ScriptDirectory.from_config(alembic_cfg)

        # Get the head revision (latest migration)
        head_revision = script_directory.get_current_head()

        # Get the current database revision
        with alembic_cfg.get_context().begin_transaction() as context:
            current_revision = context.get_current_revision()

        return current_revision == head_revision

    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return False
