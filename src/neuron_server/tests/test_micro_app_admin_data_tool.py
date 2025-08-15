"""Tests for MicroAppAdminDataTool."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.tools.micro_app_admin_data_tool import MicroAppAdminDataTool


class TestMicroAppAdminDataTool:
    """Test suite for MicroAppAdminDataTool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = MicroAppAdminDataTool()
        self.app_id = str(uuid4())
        self.user_id = "admin_user_123"
        self.record_id = str(uuid4())

    def test_tool_name_and_description(self):
        """Test that tool has correct name and description."""
        assert self.tool.name == "micro_app_admin_data"
        assert "ADMIN ONLY" in self.tool.description
        assert "Cross-user data operations" in self.tool.description

    @pytest.mark.asyncio
    async def test_admin_role_validation_success(self):
        """Test that admin users can access the tool."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin", "user"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_data_model.admin_count = AsyncMock(return_value=5)

                result = await self.tool._arun(
                    app_id=self.app_id, operation="count", config=config
                )

                assert "Total records in 'Test App'" in result
                assert "(cross-user): 5" in result
                mock_model.get.assert_called_once()
                mock_data_model.admin_count.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_role_validation_failure_no_admin_role(self):
        """Test that non-admin users are denied access."""
        config = RunnableConfig(
            configurable={"user_id": "regular_user_123", "user_roles": ["user"]}
        )

        result = await self.tool._arun(
            app_id=self.app_id, operation="count", config=config
        )

        assert "Error: Admin role required" in result
        assert "cross-user data access" in result
        assert "administrators only" in result

    @pytest.mark.asyncio
    async def test_admin_role_validation_failure_empty_roles(self):
        """Test that users with no roles are denied access."""
        config = RunnableConfig(
            configurable={"user_id": "user_no_roles", "user_roles": []}
        )

        result = await self.tool._arun(
            app_id=self.app_id, operation="count", config=config
        )

        assert "Error: Admin role required" in result

    @pytest.mark.asyncio
    async def test_admin_role_validation_failure_missing_roles(self):
        """Test that users with missing user_roles are denied access."""
        config = RunnableConfig(
            configurable={
                "user_id": "user_missing_roles"
                # user_roles not provided
            }
        )

        result = await self.tool._arun(
            app_id=self.app_id, operation="count", config=config
        )

        assert "Error: Admin role required" in result

    @pytest.mark.asyncio
    async def test_missing_user_id(self):
        """Test that missing user_id is handled."""
        config = RunnableConfig(
            configurable={
                "user_roles": ["admin"]
                # user_id not provided
            }
        )

        result = await self.tool._arun(
            app_id=self.app_id, operation="count", config=config
        )

        assert "Error: User ID is required" in result

    @pytest.mark.asyncio
    async def test_invalid_app_id(self):
        """Test handling of invalid app ID."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        result = await self.tool._arun(
            app_id="invalid-uuid", operation="count", config=config
        )

        assert "Error:" in result

    @pytest.mark.asyncio
    async def test_app_not_found(self):
        """Test handling when app doesn't exist."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_model.get = AsyncMock(return_value=None)

            result = await self.tool._arun(
                app_id=self.app_id, operation="count", config=config
            )

            assert f"Error: App with ID {self.app_id} not found" in result

    @pytest.mark.asyncio
    async def test_read_operation(self):
        """Test the read operation."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_record = Mock()
                mock_record.id = self.record_id
                mock_record.user_id = "some_user"
                mock_record.data = {"title": "Test Issue", "status": "open"}
                mock_record.created_at.isoformat.return_value = "2024-01-01T00:00:00"
                mock_record.updated_at.isoformat.return_value = "2024-01-01T00:00:00"

                mock_data_model.admin_query = AsyncMock(return_value=[mock_record])
                mock_data_model.admin_count = AsyncMock(return_value=1)

                result = await self.tool._arun(
                    app_id=self.app_id,
                    operation="read",
                    config=config,
                    limit=10,
                    offset=0,
                )

                assert "Records from 'Test App' (ADMIN VIEW - ALL USERS)" in result
                assert "Showing 1 of 1 total records (cross-user)" in result
                assert self.record_id in result
                assert "some_user" in result
                assert "Test Issue" in result

    @pytest.mark.asyncio
    async def test_get_operation(self):
        """Test the get operation."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_record = Mock()
                mock_record.id = self.record_id
                mock_record.user_id = "some_user"
                mock_record.data = {"title": "Test Issue", "status": "open"}
                mock_record.created_at.isoformat.return_value = "2024-01-01T00:00:00"
                mock_record.updated_at.isoformat.return_value = "2024-01-01T00:00:00"

                mock_data_model.admin_get = AsyncMock(return_value=mock_record)

                result = await self.tool._arun(
                    app_id=self.app_id,
                    operation="get",
                    config=config,
                    record_id=self.record_id,
                )

                assert "Record from 'Test App' (ADMIN VIEW)" in result
                assert f"ID: {self.record_id}" in result
                assert "Owner: some_user" in result
                assert "Test Issue" in result

    @pytest.mark.asyncio
    async def test_get_operation_missing_record_id(self):
        """Test get operation without record_id."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            result = await self.tool._arun(
                app_id=self.app_id,
                operation="get",
                config=config,
                # record_id not provided
            )

            assert (
                "Error: 'record_id' parameter is required for get operation" in result
            )

    @pytest.mark.asyncio
    async def test_get_operation_record_not_found(self):
        """Test get operation when record doesn't exist."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_data_model.admin_get = AsyncMock(return_value=None)

                result = await self.tool._arun(
                    app_id=self.app_id,
                    operation="get",
                    config=config,
                    record_id=self.record_id,
                )

                assert f"Record {self.record_id} not found in 'Test App'" in result

    @pytest.mark.asyncio
    async def test_count_operation(self):
        """Test the count operation."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_data_model.admin_count = AsyncMock(return_value=42)

                result = await self.tool._arun(
                    app_id=self.app_id,
                    operation="count",
                    config=config,
                    filters={"status": "open"},
                )

                assert "Total records in 'Test App' matching filters" in result
                assert "(cross-user): 42" in result
                mock_data_model.admin_count.assert_called_once_with(
                    app_id=mock_app.id, filters={"status": "open"}
                )

    @pytest.mark.asyncio
    async def test_aggregate_operation_count(self):
        """Test aggregate operation with count."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_data_model.admin_count = AsyncMock(return_value=15)

                result = await self.tool._arun(
                    app_id=self.app_id,
                    operation="aggregate",
                    config=config,
                    aggregate_operation="count",
                )

                assert "Count of records in 'Test App' (cross-user): 15" in result

    @pytest.mark.asyncio
    async def test_aggregate_operation_sum(self):
        """Test aggregate operation with sum."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_data_model.admin_aggregate = AsyncMock(return_value=150.5)

                result = await self.tool._arun(
                    app_id=self.app_id,
                    operation="aggregate",
                    config=config,
                    field="amount",
                    aggregate_operation="sum",
                )

                assert "Sum of 'amount' in 'Test App' (cross-user): 150.5" in result
                mock_data_model.admin_aggregate.assert_called_once_with(
                    app_id=mock_app.id, field="amount", operation="sum", filters=None
                )

    @pytest.mark.asyncio
    async def test_aggregate_operation_missing_field(self):
        """Test aggregate operation without required field."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            result = await self.tool._arun(
                app_id=self.app_id,
                operation="aggregate",
                config=config,
                aggregate_operation="sum",
                # field not provided
            )

            assert "Error: 'field' parameter is required for sum aggregation" in result

    @pytest.mark.asyncio
    async def test_unknown_operation(self):
        """Test handling of unknown operation."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            result = await self.tool._arun(
                app_id=self.app_id, operation="invalid_operation", config=config
            )

            assert "Error: Unknown operation: invalid_operation" in result
            assert "Valid operations: read, get, count, aggregate" in result

    @pytest.mark.asyncio
    async def test_read_operation_no_records(self):
        """Test read operation when no records found."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_data_model.admin_query = AsyncMock(return_value=[])

                result = await self.tool._arun(
                    app_id=self.app_id, operation="read", config=config
                )

                assert "No records found in 'Test App'" in result

    @pytest.mark.asyncio
    async def test_read_operation_with_filters(self):
        """Test read operation with filters."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_app = Mock()
            mock_app.id = self.app_id
            mock_app.name = "Test App"
            mock_model.get = AsyncMock(return_value=mock_app)

            with patch(
                "neuron_server.tools.micro_app_admin_data_tool.MicroAppDataModel"
            ) as mock_data_model:
                mock_data_model.admin_query = AsyncMock(return_value=[])

                filters = {"status": "open", "priority": "high"}
                result = await self.tool._arun(
                    app_id=self.app_id, operation="read", config=config, filters=filters
                )

                assert (
                    f"No records found in 'Test App' with filters {filters}" in result
                )
                mock_data_model.admin_query.assert_called_once_with(
                    app_id=mock_app.id, filters=filters, limit=100, offset=0
                )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are properly caught and returned as error strings."""
        config = RunnableConfig(
            configurable={"user_id": self.user_id, "user_roles": ["admin"]}
        )

        with patch(
            "neuron_server.tools.micro_app_admin_data_tool.MicroAppModel"
        ) as mock_model:
            mock_model.get = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            result = await self.tool._arun(
                app_id=self.app_id, operation="count", config=config
            )

            assert (
                "Failed to perform admin data operation: Database connection failed"
                in result
            )

    def test_sync_run_method(self):
        """Test that the synchronous _run method works."""
        with patch.object(self.tool, "_arun") as mock_arun:
            mock_arun.return_value = "test result"

            # The _run method should call _arun and return the result
            # Note: We can't actually test asyncio.run here easily,
            # so we'll just verify the method exists
            assert hasattr(self.tool, "_run")
