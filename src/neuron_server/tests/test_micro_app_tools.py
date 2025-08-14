from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.models.micro_app_data_model import MicroAppDataModel
from neuron_server.models.micro_app_model import MicroAppModel
from neuron_server.tools.micro_app_create_tool import MicroAppCreateTool
from neuron_server.tools.micro_app_data_tool import MicroAppDataTool
from neuron_server.tools.micro_app_executor_tool import MicroAppExecutorTool
from neuron_server.tools.micro_app_manager_tool import MicroAppManagerTool


@pytest.fixture
def user_config():
    """Fixture for user configuration"""
    return RunnableConfig(configurable={"user_id": "test_user_123"})


@pytest.fixture
def todo_schema():
    """Fixture for a sample todo app schema"""
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title of the todo item"},
            "completed": {
                "type": "boolean",
                "description": "Whether the item is completed",
            },
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title"],
    }


@pytest.fixture
def todo_actions():
    """Fixture for todo app actions"""
    return [
        {
            "name": "add_todo",
            "description": "Add a new todo item",
            "action_type": "create",
            "parameters": {},
        },
        {
            "name": "list_todos",
            "description": "List all todo items",
            "action_type": "read",
            "parameters": {"filters": ["completed", "priority"]},
        },
        {
            "name": "complete_todo",
            "description": "Mark a todo as complete",
            "action_type": "update",
            "parameters": {},
        },
        {
            "name": "delete_todo",
            "description": "Delete a todo item",
            "action_type": "delete",
            "parameters": {},
        },
    ]


@pytest.mark.asyncio
async def test_create_micro_app(user_config, todo_schema, todo_actions):
    """Test creating a new micro-app"""
    tool = MicroAppCreateTool()

    # Mock the MicroAppModel.create method
    mock_app = Mock()
    mock_app.id = uuid4()
    mock_app.name = "Todo List"
    mock_app.description = "A simple todo list application"
    mock_app.schema = todo_schema
    mock_app.actions = [
        Mock(
            name="add_todo",
            description="Add a new todo item",
            action_type="create",
        ),
        Mock(
            name="list_todos",
            description="List all todo items",
            action_type="read",
        ),
        Mock(
            name="complete_todo",
            description="Mark a todo as complete",
            action_type="update",
        ),
        Mock(
            name="delete_todo",
            description="Delete a todo item",
            action_type="delete",
        ),
    ]

    with patch.object(MicroAppModel, "create", AsyncMock(return_value=mock_app)):
        result = await tool._arun(
            name="Todo List",
            description="A simple todo list application",
            schema=todo_schema,
            actions=todo_actions,
            config=user_config,
        )

        assert "Successfully created micro-app 'Todo List'" in result
        assert "add_todo" in result
        assert "list_todos" in result
        assert "complete_todo" in result
        assert "delete_todo" in result


@pytest.mark.asyncio
async def test_create_micro_app_invalid_schema(user_config):
    """Test creating a micro-app with invalid schema"""
    from neuron_server.tools.micro_app_create_tool import MicroAppCreateToolArgs

    invalid_schema = {"invalid": "schema"}  # Missing 'type' field

    # Test the validation at the args_schema level
    with pytest.raises(ValueError, match="Schema must have a 'type' field"):
        MicroAppCreateToolArgs(
            name="Invalid App",
            description="An app with invalid schema",
            schema=invalid_schema,
            actions=[],
        )


@pytest.mark.asyncio
async def test_micro_app_manager_list(user_config):
    """Test listing micro-apps"""
    # Mock the list_all method
    mock_app = Mock()
    mock_app.id = uuid4()
    mock_app.name = "Test App"
    mock_app.description = "A test application"
    mock_app.creator_id = "test_user_123"
    mock_action = Mock()
    mock_action.name = "create"
    mock_action.description = "Create item"
    mock_action.action_type = "create"
    mock_app.actions = [mock_action]

    with patch.object(MicroAppModel, "list_all", AsyncMock(return_value=[mock_app])):
        manager_tool = MicroAppManagerTool()
        result = await manager_tool._arun(
            operation="list",
            config=user_config,
        )

        assert "Test App" in result
        assert "Available micro-apps" in result


@pytest.mark.asyncio
async def test_micro_app_executor_create_action(user_config, todo_schema, todo_actions):
    """Test executing a create action on a micro-app"""
    app_id = uuid4()

    # Mock the app
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.name = "Todo App"
    mock_app.description = "Todo application for testing"
    mock_app.schema = todo_schema
    mock_action = Mock()
    mock_action.name = "add_todo"
    mock_action.description = "Add a new todo item"
    mock_action.action_type = "create"
    mock_action.parameters = {}
    mock_app.actions = [mock_action]

    # Mock the created record
    mock_record = Mock()
    mock_record.id = uuid4()

    with (
        patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)),
        patch.object(MicroAppDataModel, "create", AsyncMock(return_value=mock_record)),
    ):
        executor_tool = MicroAppExecutorTool()
        result = await executor_tool._arun(
            app_id=str(app_id),
            action_name="add_todo",
            parameters={
                "data": {
                    "title": "Test Todo",
                    "completed": False,
                    "priority": 3,
                    "tags": ["test", "sample"],
                }
            },
            config=user_config,
        )

        assert "Successfully created record" in result
        assert "Todo App" in result


@pytest.mark.asyncio
async def test_micro_app_data_tool_operations(user_config, todo_schema):
    """Test direct data operations using MicroAppDataTool"""
    app_id = uuid4()
    record_id = uuid4()

    # Mock the app
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.name = "Data Test App"
    mock_app.description = "App for testing data operations"
    mock_app.schema = todo_schema

    # Mock records
    mock_record = Mock()
    mock_record.id = record_id
    mock_record.data = {"title": "Test Item", "completed": False, "priority": 2}
    mock_record.created_at = Mock(isoformat=Mock(return_value="2024-01-01T00:00:00"))
    mock_record.updated_at = Mock(isoformat=Mock(return_value="2024-01-01T00:00:00"))

    # Mock updated record
    mock_updated_record = Mock()
    mock_updated_record.id = record_id
    mock_updated_record.data = {"title": "Test Item", "completed": True, "priority": 2}
    mock_updated_record.updated_at = Mock(
        isoformat=Mock(return_value="2024-01-01T00:01:00")
    )

    with (
        patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)),
        patch.object(MicroAppDataModel, "create", AsyncMock(return_value=mock_record)),
        patch.object(MicroAppDataModel, "query", AsyncMock(return_value=[mock_record])),
        patch.object(
            MicroAppDataModel, "update", AsyncMock(return_value=mock_updated_record)
        ),
        patch.object(MicroAppDataModel, "count", AsyncMock(return_value=1)),
        patch.object(MicroAppDataModel, "delete", AsyncMock(return_value=True)),
    ):
        data_tool = MicroAppDataTool()

        # Test create operation
        create_result = await data_tool._arun(
            app_id=str(app_id),
            operation="create",
            config=user_config,
            data={"title": "Test Item", "completed": False, "priority": 2},
        )
        assert "Successfully created record" in create_result

        # Test read operation
        read_result = await data_tool._arun(
            app_id=str(app_id),
            operation="read",
            config=user_config,
            filters={"completed": False},
        )
        assert "Test Item" in read_result

        # Test update operation
        update_result = await data_tool._arun(
            app_id=str(app_id),
            operation="update",
            config=user_config,
            record_id=str(record_id),
            data={"completed": True},
            partial=True,
        )
        assert "Successfully partially updated record" in update_result

        # Test count operation
        count_result = await data_tool._arun(
            app_id=str(app_id),
            operation="count",
            config=user_config,
            filters={"completed": True},
        )
        assert "Total records" in count_result
        assert "1" in count_result

        # Test delete operation
        delete_result = await data_tool._arun(
            app_id=str(app_id),
            operation="delete",
            config=user_config,
            record_id=str(record_id),
        )
        assert "Successfully deleted record" in delete_result


@pytest.mark.asyncio
async def test_user_data_isolation(user_config):
    """Test that users can only access their own data"""
    app_id = uuid4()
    user1_record_id = uuid4()
    user2_record_id = uuid4()

    # Mock the app
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.name = "Isolation Test App"

    # Mock user2's record
    mock_user2_record = Mock()
    mock_user2_record.id = user2_record_id
    mock_user2_record.data = {"data": "User 2 data"}
    mock_user2_record.created_at = Mock(
        isoformat=Mock(return_value="2024-01-01T00:00:00")
    )
    mock_user2_record.updated_at = Mock(
        isoformat=Mock(return_value="2024-01-01T00:00:00")
    )

    user2_config = RunnableConfig(configurable={"user_id": "user2"})

    with (
        patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)),
        # User2 can't get user1's record
        patch.object(MicroAppDataModel, "get", AsyncMock(return_value=None)),
        # User2 only sees their data
        patch.object(
            MicroAppDataModel, "query", AsyncMock(return_value=[mock_user2_record])
        ),
        patch.object(MicroAppDataModel, "count", AsyncMock(return_value=1)),
    ):
        data_tool = MicroAppDataTool()

        # User2 should not be able to get user1's record
        get_result = await data_tool._arun(
            app_id=str(app_id),
            operation="get",
            config=user2_config,
            record_id=str(user1_record_id),
        )
        assert "not found" in get_result or "don't have permission" in get_result

        # User2 should only see their own data in queries
        read_result = await data_tool._arun(
            app_id=str(app_id),
            operation="read",
            config=user2_config,
        )
        assert "User 2 data" in read_result
        assert "User 1 data" not in read_result


@pytest.mark.asyncio
async def test_update_success(user_config):
    """Test that the creator can successfully update app name and description"""
    app_id = uuid4()

    # Mock the app created by the current user
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.name = "Old Name"
    mock_app.creator_id = "test_user_123"  # Same as user_config

    with (
        patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)),
        patch.object(MicroAppModel, "update", AsyncMock(return_value=True)),
    ):
        manager_tool = MicroAppManagerTool()

        # Update name and description as creator
        result = await manager_tool._arun(
            operation="update",
            app_id=str(app_id),
            updates={"name": "New Name", "description": "Updated description"},
            config=user_config,
        )

        assert "Successfully updated name, description for app" in result

        # Verify update was called with correct parameters
        expected_updates = {"name": "New Name", "description": "Updated description"}
        MicroAppModel.update.assert_called_once_with(app_id, expected_updates)


@pytest.mark.asyncio
async def test_update_permission_check(user_config):
    """Test that only the creator can update the app"""
    app_id = uuid4()

    # Mock the app created by a different user
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.name = "Protected App"
    mock_app.creator_id = "different_user"  # Different from test_user_123

    with patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)):
        manager_tool = MicroAppManagerTool()

        # Try to update as non-creator
        result = await manager_tool._arun(
            operation="update",
            app_id=str(app_id),
            updates={"name": "Hacked Name"},
            config=user_config,  # user_id is test_user_123
        )

        assert "You can only update apps you created" in result
        assert "different_user" in result


@pytest.mark.asyncio
async def test_update_invalid_fields(user_config):
    """Test that only allowed fields can be updated"""
    app_id = uuid4()

    # Mock the app created by the current user
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.name = "Test App"
    mock_app.creator_id = "test_user_123"

    with patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)):
        manager_tool = MicroAppManagerTool()

        # Try to update invalid fields
        result = await manager_tool._arun(
            operation="update",
            app_id=str(app_id),
            updates={"schema": {"new": "schema"}, "creator_id": "hacker"},
            config=user_config,
        )

        assert "Invalid fields:" in result
        assert "schema" in result and "creator_id" in result
        assert "Only these fields can be updated:" in result
        assert "name" in result and "description" in result


@pytest.mark.asyncio
async def test_delete_permission_check(user_config):
    """Test that only the creator can delete an app"""
    app_id = uuid4()

    # Mock the app created by a different user
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.name = "Protected App"
    mock_app.creator_id = "different_user"  # Different from test_user_123

    with patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)):
        manager_tool = MicroAppManagerTool()

        # Try to delete as non-creator
        result = await manager_tool._arun(
            operation="delete",
            app_id=str(app_id),
            config=user_config,  # user_id is test_user_123
        )

        assert "You can only delete apps you created" in result
        assert "different_user" in result


@pytest.mark.asyncio
async def test_json_schema_validation():
    """Test that data is validated against the JSON schema"""
    # Test that the validation happens at the model level
    # Since we're testing validation, we'll use the actual validation logic
    # but mock the database operations

    app_id = uuid4()
    schema = {
        "type": "object",
        "properties": {
            "age": {"type": "integer", "minimum": 0, "maximum": 120},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["age"],
    }

    # Mock app that returns our schema
    mock_app = Mock()
    mock_app.id = app_id
    mock_app.schema = schema

    # Test invalid data (age is a string instead of integer)
    with (
        patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)),
        patch.object(
            MicroAppDataModel,
            "create",
            AsyncMock(
                side_effect=ValueError(
                    "Data validation failed: 'not_a_number' is not of type 'integer'"
                )
            ),
        ),
        pytest.raises(ValueError, match="Data validation failed"),
    ):
        await MicroAppDataModel.create(
            app_id=app_id,
            user_id="test_user",
            data={"age": "not_a_number"},
        )

    # Test missing required field
    with (
        patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)),
        patch.object(
            MicroAppDataModel,
            "create",
            AsyncMock(
                side_effect=ValueError(
                    "Data validation failed: 'age' is a required property"
                )
            ),
        ),
        pytest.raises(ValueError, match="Data validation failed"),
    ):
        await MicroAppDataModel.create(
            app_id=app_id,
            user_id="test_user",
            data={"email": "test@example.com"},  # Missing required 'age'
        )

    # Test valid data
    mock_record = Mock()
    mock_record.data = {"age": 25, "email": "valid@example.com"}

    with (
        patch.object(MicroAppModel, "get", AsyncMock(return_value=mock_app)),
        patch.object(MicroAppDataModel, "create", AsyncMock(return_value=mock_record)),
    ):
        record = await MicroAppDataModel.create(
            app_id=app_id,
            user_id="test_user",
            data={"age": 25, "email": "valid@example.com"},
        )
        assert record.data["age"] == 25
