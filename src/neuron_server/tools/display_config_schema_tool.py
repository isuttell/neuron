import asyncio
import json
import logging
from typing import Any

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from neuron_server.models.display_config_model import DisplayConfig

logger = logging.getLogger(__name__)


class DisplayConfigSchemaToolArgs(BaseModel):
    """Args for getting display config schema."""

    include_examples: bool = True


class DisplayConfigSchemaTool(BaseTool):
    name: str = "display_config_schema"
    description: str = """Get the JSON schema for micro-app display configurations.

    This tool returns the complete JSON schema that defines the structure for
    display configurations. Use this schema as a reference when creating or
    modifying display configurations for micro-apps.

    The schema includes:
    - All supported component types (input, select, textarea, etc.)
    - Validation rules and constraints
    - Position-based field ordering
    - View configuration options
    - Examples of valid configurations
    """

    args_schema: type[DisplayConfigSchemaToolArgs] = DisplayConfigSchemaToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        include_examples: bool = True,
        config: RunnableConfig | None = None,
    ) -> str:
        try:
            # Get the JSON schema from the Pydantic model
            schema = DisplayConfig.get_json_schema_for_llm()

            if not include_examples:
                # Remove examples if not requested
                schema.pop("examples", None)

            return f"""Display Configuration JSON Schema:

{json.dumps(schema, indent=2)}

This schema defines the structure for micro-app display configurations. Key points:

1. **Views**: Define how data is presented (list view, detail view, etc.)
   - `fields`: Array of field names to display
   - `title`, `description`: Optional display metadata
   - `actions`: Optional array of available actions

2. **Components**: Define how individual fields are rendered
   - `type`: Component type (input, select, textarea, checkbox, date, number, email)
   - `position`: Integer for explicit field ordering (0-based)
   - `validation`: Rules for field validation (min, max, pattern, etc.)
   - `options`: For select components (array of {{value, label}} objects)

3. **Position-based ordering**: Use the `position` property to control field order
   - Lower numbers appear first
   - Must be unique across all components
   - Optional - fields without positions appear after positioned fields

Example usage:
- Set `position: 0` for the first field, `position: 1` for second, etc.
- All field names in views must exist in components
- Select components must have `options` array defined"""

        except Exception as e:
            logger.error("Failed to get display config schema: %s", e, exc_info=True)
            return f"Failed to get display config schema: {e}"
