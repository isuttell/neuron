"""Pydantic models for micro-app display configuration validation."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ValidationConfig(BaseModel):
    """Validation rules for component fields."""

    min: Optional[int] = Field(None, description="Minimum value for numeric fields")
    max: Optional[int] = Field(None, description="Maximum value for numeric fields")
    pattern: Optional[str] = Field(
        None, description="Regex pattern for string validation"
    )
    min_length: Optional[int] = Field(
        None, ge=0, description="Minimum string length", alias="minLength"
    )
    max_length: Optional[int] = Field(
        None, ge=0, description="Maximum string length", alias="maxLength"
    )


class SelectOption(BaseModel):
    """Option for select component."""

    value: str = Field(description="Option value")
    label: str = Field(description="Human-readable option label")


class ComponentConfig(BaseModel):
    """Configuration for individual field components."""

    type: Literal[
        "input", "textarea", "select", "checkbox", "date", "number", "email"
    ] = Field(description="Type of form component to render")
    label: Optional[str] = Field(None, description="Human-readable field label")
    placeholder: Optional[str] = Field(
        None, description="Placeholder text for input fields"
    )
    required: Optional[bool] = Field(False, description="Whether the field is required")
    readonly: Optional[bool] = Field(
        False, description="Whether the field is read-only"
    )
    position: Optional[int] = Field(
        None, ge=0, description="Display position (0-based, determines field order)"
    )
    options: Optional[list[SelectOption]] = Field(
        None, description="Options for select components"
    )
    validation: Optional[ValidationConfig] = Field(
        None, description="Validation rules for the field"
    )
    props: Optional[dict[str, Any]] = Field(
        None, description="Additional component-specific properties"
    )

    @model_validator(mode="after")
    def validate_select_options(self) -> "ComponentConfig":
        """Validate that select components have options."""
        if self.type == "select" and not self.options:
            raise ValueError("Select components must have options defined")
        return self


class ViewConfig(BaseModel):
    """Configuration for a view (list, detail, etc.)."""

    fields: list[str] = Field(description="List of field names to display in this view")
    title: Optional[str] = Field(None, description="Title for the view")
    description: Optional[str] = Field(None, description="Description of the view")
    actions: Optional[list[str]] = Field(
        None, description="Available actions for this view"
    )


class DisplayConfig(BaseModel):
    """Complete display configuration for a micro-app."""

    views: dict[str, ViewConfig] = Field(
        description="View configurations (list, detail, etc.)"
    )
    components: dict[str, ComponentConfig] = Field(
        description="Component configurations for each field"
    )

    @model_validator(mode="after")
    def validate_configuration(self) -> "DisplayConfig":
        """Validate the complete display configuration."""
        positions_used = set()

        # Validate component positions are unique
        for _field_name, component in self.components.items():
            if component.position is not None:
                if component.position in positions_used:
                    raise ValueError(
                        f"Position {component.position} is used by multiple components"
                    )
                positions_used.add(component.position)

        # Validate that all view fields reference existing components
        for view_name, view_config in self.views.items():
            for field_name in view_config.fields:
                if field_name not in self.components:
                    raise ValueError(
                        f"View '{view_name}' references field '{field_name}' "
                        f"which is not defined in components"
                    )

        return self

    @classmethod
    def get_json_schema_for_llm(cls) -> dict:
        """Export JSON schema for LLM consumption."""
        schema = cls.model_json_schema()

        # Add helpful examples and descriptions for LLMs
        schema["examples"] = [
            {
                "views": {
                    "list": {"fields": ["name", "status"], "title": "User List"},
                    "detail": {
                        "fields": ["name", "email", "status", "bio"],
                        "title": "User Details",
                    },
                },
                "components": {
                    "name": {
                        "type": "input",
                        "label": "Full Name",
                        "required": True,
                        "position": 0,
                        "placeholder": "Enter full name",
                        "validation": {"minLength": 2, "maxLength": 50},
                    },
                    "email": {
                        "type": "email",
                        "label": "Email Address",
                        "required": True,
                        "position": 1,
                        "placeholder": "Enter email address",
                    },
                    "status": {
                        "type": "select",
                        "label": "Status",
                        "position": 2,
                        "options": [
                            {"value": "active", "label": "Active"},
                            {"value": "inactive", "label": "Inactive"},
                        ],
                    },
                    "bio": {
                        "type": "textarea",
                        "label": "Biography",
                        "position": 3,
                        "placeholder": "Enter biography",
                        "validation": {"maxLength": 500},
                    },
                },
            }
        ]

        return schema

    def to_dict(self) -> dict:
        """Convert to dictionary format compatible with existing validation."""
        return self.model_dump(exclude_none=True)
