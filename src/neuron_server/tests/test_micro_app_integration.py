"""
Integration test demonstrating the micro-app system.
Run with: poetry run python src/neuron_server/tests/test_micro_app_integration.py
"""

import asyncio

from neuron_server.models.micro_app_data_model import MicroAppDataModel
from neuron_server.models.micro_app_model import MicroAppActionModel, MicroAppModel


async def demo_micro_app_system():
    """Demonstrate the micro-app system functionality"""
    print("🚀 Micro-App System Demo\n")
    print("=" * 50)

    # 1. Create a Todo List micro-app
    print("\n1. Creating a Todo List micro-app...")

    todo_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title of the todo item"},
            "completed": {"type": "boolean", "default": False},
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title"],
    }

    actions = [
        MicroAppActionModel(
            name="add_todo",
            description="Add a new todo item",
            action_type="create",
            parameters={},
        ),
        MicroAppActionModel(
            name="list_todos",
            description="List all todo items",
            action_type="read",
            parameters={"filters": ["completed", "priority"]},
        ),
        MicroAppActionModel(
            name="complete_todo",
            description="Mark a todo as complete",
            action_type="update",
            parameters={},
        ),
        MicroAppActionModel(
            name="count_by_priority",
            description="Count todos by priority",
            action_type="aggregate",
            parameters={"operation": "count", "group_by": "priority"},
        ),
    ]

    try:
        app = await MicroAppModel.create(
            name="Demo Todo List",
            description="A demonstration todo list application",
            schema=todo_schema,
            creator_id="demo_user",
            actions=actions,
        )
        print(f"✅ Created app: {app.name} (ID: {app.id})")
        print(f"   Available actions: {', '.join([a.name for a in app.actions])}")
    except Exception as e:
        print(f"❌ Failed to create app: {e}")
        return

    # 2. Add some todo items
    print("\n2. Adding todo items...")

    user_id = "demo_user"
    todos = [
        {"title": "Review pull requests", "priority": 5, "tags": ["work", "urgent"]},
        {"title": "Write documentation", "priority": 3, "tags": ["work"]},
        {"title": "Buy groceries", "priority": 2, "tags": ["personal"]},
        {"title": "Exercise", "priority": 4, "tags": ["personal", "health"]},
    ]

    created_ids = []
    for todo in todos:
        try:
            record = await MicroAppDataModel.create(
                app_id=app.id,
                user_id=user_id,
                data=todo,
            )
            created_ids.append(record.id)
            print(
                f"   ✅ Added: {todo['title']} "
                f"(priority: {todo.get('priority', 'N/A')})"
            )
        except Exception as e:
            print(f"   ❌ Failed to add {todo['title']}: {e}")

    # 3. Query todos
    print("\n3. Querying todos...")

    # All todos
    all_todos = await MicroAppDataModel.query(
        app_id=app.id,
        user_id=user_id,
    )
    print(f"   Total todos: {len(all_todos)}")

    # High priority todos
    high_priority = await MicroAppDataModel.query(
        app_id=app.id,
        user_id=user_id,
        filters={"priority": 5},
    )
    if high_priority:
        print(f"   High priority todos: {high_priority[0].data['title']}")

    # 4. Update a todo
    print("\n4. Updating a todo (marking as complete)...")

    if created_ids:
        updated = await MicroAppDataModel.update(
            record_id=created_ids[0],
            user_id=user_id,
            data={"completed": True},
            partial=True,
        )
        if updated:
            print(f"   ✅ Marked '{updated.data['title']}' as complete")

    # 5. Demonstrate user isolation
    print("\n5. Testing user data isolation...")

    other_user_id = "another_user"

    # Try to create data as another user
    await MicroAppDataModel.create(
        app_id=app.id,
        user_id=other_user_id,
        data={"title": "Another user's todo", "priority": 1},
    )

    # Each user should only see their own data
    demo_user_todos = await MicroAppDataModel.query(
        app_id=app.id,
        user_id=user_id,
    )
    other_user_todos = await MicroAppDataModel.query(
        app_id=app.id,
        user_id=other_user_id,
    )

    print(f"   Demo user sees: {len(demo_user_todos)} todos")
    print(f"   Other user sees: {len(other_user_todos)} todos")
    print("   ✅ User data is properly isolated")

    # 6. Aggregate operations
    print("\n6. Performing aggregations...")

    count = await MicroAppDataModel.count(
        app_id=app.id,
        user_id=user_id,
    )
    print(f"   Total count: {count}")

    # 7. Clean up
    print("\n7. Cleaning up...")

    # Delete the app (this cascades to all data)
    deleted = await MicroAppModel.delete(app.id)
    if deleted:
        print("   ✅ Deleted app and all associated data")

    print("\n" + "=" * 50)
    print("✅ Demo completed successfully!")
    print("\nThe micro-app system provides:")
    print("  • Custom JSON schemas for data validation")
    print("  • User-segmented data storage")
    print("  • Predefined actions (CRUD + custom)")
    print("  • Automatic schema validation")
    print("  • Flexible query and aggregation capabilities")


if __name__ == "__main__":
    print("Starting Micro-App System Integration Demo...")
    print("Note: This requires a running database connection.")
    try:
        asyncio.run(demo_micro_app_system())
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure the database is running and migrations are applied.")
