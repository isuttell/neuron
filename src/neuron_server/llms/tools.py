from langchain.tools import BaseTool

from neuron_server.config import config
from neuron_server.tools.alphavantage_tool import AlphaVantageTool
from neuron_server.tools.app_image_tool import AppImageTool
from neuron_server.tools.arxiv_recall_tool import ArxivRecallTool
from neuron_server.tools.arxiv_search_tool import ArxivSearchTool
from neuron_server.tools.arxiv_summary_tool import ArxivSummaryTool
from neuron_server.tools.astro_coordinates_tool import AstroCoordinatesTool
from neuron_server.tools.astro_finder_image_tool import AstroFinderImageTool
from neuron_server.tools.astro_object_search_tool import AstroObjectSearchTool
from neuron_server.tools.astro_observability_tool import AstroObservabilityTool
from neuron_server.tools.astro_target_search_tool import AstroTargetSearchTool
from neuron_server.tools.astrospheric_forecast_tool import (
    AstrosphericForecastTool,
)
from neuron_server.tools.automatic1111_tool import Automatic1111API, Automatic1111Tool
from neuron_server.tools.code_interpreter_tool import CodeInterpreterTool
from neuron_server.tools.deepseek_reasoning_tool import DeepSeekReasoningTool
from neuron_server.tools.dice_tool import DiceTool
from neuron_server.tools.elevenlabs_soundeffects_tool import (
    ElevenLabsSoundEffectsTool,
)
from neuron_server.tools.elevenlabs_tts_tool import ElevenLabsTTSTool
from neuron_server.tools.ffmpeg_tool import FFmpegTool
from neuron_server.tools.glados_tts_tool import GladosToolset
from neuron_server.tools.graph_arxiv_import_tool import GraphArxivImportTool
from neuron_server.tools.graph_import_tool import GraphImportTool
from neuron_server.tools.graph_question_tool import GraphQuestionTool
from neuron_server.tools.graph_website_import_tool import GraphWebsiteImportTool
from neuron_server.tools.hd2_galactic_war_report_tool import (
    HD2GalacticWarReportTool,
)
from neuron_server.tools.hd2_liberation_history_tool import (
    HD2LiberationHistoryTool,
)
from neuron_server.tools.homeassistant_api import HomeAssistantAPI
from neuron_server.tools.homeassistant_sensor_tool import (
    HomeAssistantSensorTool,
)
from neuron_server.tools.homeassistant_service_tool import (
    HomeAssistantServiceTool,
)
from neuron_server.tools.inspect_image_tool import InspectImageTool
from neuron_server.tools.media_list_access_tool import MediaListAccessTool
from neuron_server.tools.media_list_add_item_tool import MediaListAddItemTool
from neuron_server.tools.media_list_create_tool import MediaListCreateTool
from neuron_server.tools.media_list_delete_tool import MediaListDeleteTool
from neuron_server.tools.media_list_get_items_tool import MediaListGetItemsTool
from neuron_server.tools.media_list_read_tool import MediaListReadTool
from neuron_server.tools.media_list_remove_item_tool import (
    MediaListRemoveItemTool,
)
from neuron_server.tools.media_list_reorder_items_tool import (
    MediaListReorderItemsTool,
)
from neuron_server.tools.media_list_update_tool import MediaListUpdateTool
from neuron_server.tools.memory_recall_tool import MemoryRecallTool
from neuron_server.tools.memory_store_tool import MemoryStoreTool
from neuron_server.tools.micro_app_admin_data_tool import MicroAppAdminDataTool
from neuron_server.tools.micro_app_create_tool import MicroAppCreateTool
from neuron_server.tools.micro_app_data_tool import MicroAppDataTool
from neuron_server.tools.micro_app_executor_tool import MicroAppExecutorTool
from neuron_server.tools.micro_app_manager_tool import MicroAppManagerTool
from neuron_server.tools.moon_tool import MoonTool
from neuron_server.tools.openweathermap_forecast_tool import (
    OpenWeatherMapForecastTool,
)
from neuron_server.tools.openweathermap_overview_tool import (
    OpenWeatherMapOverviewTool,
)
from neuron_server.tools.pyodide_code_interpreter_tool import PyodideCodeInterpreterTool
from neuron_server.tools.read_thread_memory_tool import ReadThreadMemoryTool
from neuron_server.tools.release_commits_tool import ReleaseCommitsTool
from neuron_server.tools.replicate_audio_generation_tool import (
    ReplicateAudioGenerationTool,
)
from neuron_server.tools.replicate_image_generation_tool import (
    ReplicateImageGenerationTool,
)
from neuron_server.tools.replicate_kokoro_tts_tool import ReplicateKokoroTTSTool
from neuron_server.tools.replicate_kontext_image_tool import (
    ReplicateKontextImageTool,
)
from neuron_server.tools.replicate_music_generation_tool import (
    ReplicateMusicGenerationTool,
)
from neuron_server.tools.replicate_play_dialog_tts_tool import ReplicatePlayDialogTool
from neuron_server.tools.replicate_video_generation_tool import (
    ReplicateVideoGenerationTool,
)
from neuron_server.tools.schedule_list_tool import ScheduleListTool
from neuron_server.tools.schedule_prompt_tool import SchedulePromptTool
from neuron_server.tools.schedule_remove_tool import ScheduleRemoveTool
from neuron_server.tools.security_camera_tool import SecurityCameraTool
from neuron_server.tools.send_notification_tool import SendNotificationTool
from neuron_server.tools.set_thread_memory_tool import SetThreadMemoryTool
from neuron_server.tools.sun_tool import SunTool
from neuron_server.tools.tavily_search_tool import TavilySearchTool
from neuron_server.tools.web_fetch_tool import WebFetchTool
from neuron_server.tools.whisper_stt_tool import WhisperSTTTool

homeassistant_api = HomeAssistantAPI(token=config.homeassistant.token)

# Admin-only tools that require admin role to access
ADMIN_ONLY_TOOLS = [
    "micro_app_admin_data",
]

# Initialize toolsets that require configuration
glados_toolset = GladosToolset()

tool_sets: dict[str, list[BaseTool]] = {
    "nasa": [],
    "glados": glados_toolset.tools,
    "charts": [],
    "reasoning": [
        DeepSeekReasoningTool(),
    ],
    "finance": [
        AlphaVantageTool(),
    ],
    "kepler": [
        Automatic1111Tool(
            api=Automatic1111API(
                output_directory=config.static_folder,
                endpoint=config.automatic1111_endpoint,
            )
        ),
    ],
    "graph": [
        ArxivSearchTool(),
        GraphQuestionTool(),
        GraphArxivImportTool(),
        GraphImportTool(),
        GraphWebsiteImportTool(),
    ],
    "document_query": [],
    "image": [
        ReplicateImageGenerationTool(),
        ReplicateKontextImageTool(),
        AppImageTool(),
    ],
    "video": [
        FFmpegTool(),
        ReplicateVideoGenerationTool(),
        ReplicateAudioGenerationTool(),
        ReplicateMusicGenerationTool(),
    ],
    "audio": [
        FFmpegTool(),
        ElevenLabsSoundEffectsTool(),
        ReplicateMusicGenerationTool(),
        WhisperSTTTool(),
    ],
    "tts": [
        ElevenLabsTTSTool(),
        ReplicatePlayDialogTool(),
        ReplicateKokoroTTSTool(),
        FFmpegTool(),
        WhisperSTTTool(),
    ],
    "search": [
        TavilySearchTool(),
        WebFetchTool(),
    ],
    "arxiv": [
        ArxivSearchTool(),
        ArxivSummaryTool(),
        ArxivRecallTool(),
    ],
    "homeassistant": [
        SecurityCameraTool(),
        HomeAssistantServiceTool(api=homeassistant_api),
        HomeAssistantSensorTool(api=homeassistant_api),
        SendNotificationTool(),
    ],
    "astro": [
        MoonTool(),
        SunTool(),
        AstrosphericForecastTool(),
        AstroCoordinatesTool(),
        AstroTargetSearchTool(),
        AstroObjectSearchTool(),
        AstroObservabilityTool(),
        AstroFinderImageTool(),
        HomeAssistantSensorTool(api=homeassistant_api),
        OpenWeatherMapOverviewTool(),
        OpenWeatherMapForecastTool(),
        SendNotificationTool(),
    ],
    "memory": [
        MemoryRecallTool(),
        MemoryStoreTool(),
    ],
    "dice": [
        DiceTool(),
    ],
    "hd2": [
        HD2GalacticWarReportTool(),
        HD2LiberationHistoryTool(),
    ],
    "weather": [
        AstrosphericForecastTool(),
        HomeAssistantSensorTool(api=homeassistant_api),
        OpenWeatherMapOverviewTool(),
        OpenWeatherMapForecastTool(),
    ],
    "notifications": [
        SendNotificationTool(),
    ],
    "code_interpreter": [
        CodeInterpreterTool(),
        PyodideCodeInterpreterTool(),
    ],
    "neuron": [
        ReleaseCommitsTool(),
    ],
    "micro_apps": [
        MicroAppCreateTool(),
        MicroAppExecutorTool(),
        MicroAppManagerTool(),
        MicroAppDataTool(),
        MicroAppAdminDataTool(),
    ],
}

default_tools: list[BaseTool] = list(
    {
        tool.name: tool
        for tool in [
            *tool_sets["tts"],
        ]
    }.values()
)

media_tools: list[BaseTool] = [
    MediaListAccessTool(),
    MediaListAddItemTool(),
    MediaListGetItemsTool(),
    MediaListRemoveItemTool(),
    MediaListCreateTool(),
    MediaListReadTool(),
    MediaListUpdateTool(),
    MediaListDeleteTool(),
    MediaListReorderItemsTool(),
]

schedule_tools: list[BaseTool] = [
    SchedulePromptTool(),
    ScheduleListTool(),
    ScheduleRemoveTool(),
]

memory_tools: list[BaseTool] = [
    MemoryRecallTool(),
    MemoryStoreTool(),
]

thread_memory_tools: list[BaseTool] = [
    ReadThreadMemoryTool(),
    SetThreadMemoryTool(),
]

personality_tools: list[BaseTool] = []

micro_app_tools: list[BaseTool] = [
    MicroAppCreateTool(),
    MicroAppExecutorTool(),
    MicroAppManagerTool(),
    MicroAppDataTool(),
    MicroAppAdminDataTool(),
]


async def get_tools(query: str, user_roles: list[str] | None = None) -> list[BaseTool]:
    """Get tools based on query string.

    Args:
        query: Query string containing tool categories separated by '+'
        user_roles: List of user roles for filtering admin tools

    Returns:
        List of tools from requested categories plus required tools
    """
    ts: list[BaseTool] = []
    if query.strip():
        # Only process non-empty queries
        categories = [name for name in query.strip("+").split("+") if name in tool_sets]
        ts = [tool for name in categories for tool in tool_sets[name]]

    # Required Tools
    if config.memory_enabled:
        ts.extend(memory_tools)
    ts.extend(personality_tools)
    ts.extend(schedule_tools)
    ts.extend(thread_memory_tools)
    ts.append(WebFetchTool())
    ts.append(InspectImageTool())
    ts.extend(micro_app_tools)

    # Filter admin tools if user doesn't have admin role
    if user_roles is None or "admin" not in user_roles:
        ts = [tool for tool in ts if tool.name not in ADMIN_ONLY_TOOLS]

    return list({tool.name: tool for tool in ts}.values())


def get_available_tool_sets() -> list[str]:
    """Get list of all available tool set keys.

    Returns:
        List of tool set names that can be used in personality configurations
    """
    return list(tool_sets.keys())


def get_protected_tool_sets() -> dict[str, str]:
    """Get mapping of protected tool sets to their required roles.

    Returns:
        Dictionary mapping tool set names to required role names
    """
    return {
        "homeassistant": "tool-homeassistant",
        "kepler": "tool-kepler",
        "video": "tool-video",
        "reasoning": "tool-reasoning",
        "notifications": "tool-notifications",
    }


def validate_tool_set_keys(tool_set_string: str) -> list[str]:
    """Validate tool set keys and return list of invalid keys.

    Args:
        tool_set_string: Tool set string with categories separated by '+'

    Returns:
        List of invalid tool set keys that don't exist in tool_sets
    """
    if not tool_set_string or not tool_set_string.strip():
        return []

    available_sets = get_available_tool_sets()
    categories = tool_set_string.strip("+").split("+")
    requested_sets = [name.strip() for name in categories if name.strip()]

    return [name for name in requested_sets if name not in available_sets]


def get_missing_tool_permissions(
    tool_set_string: str, user_roles: list[str]
) -> list[str]:
    """Get list of tool sets that require permissions the user doesn't have.

    Args:
        tool_set_string: Tool set string with categories separated by '+'
        user_roles: List of roles the user has

    Returns:
        List of tool set names the user cannot access due to missing roles
    """
    if not tool_set_string or not tool_set_string.strip():
        return []

    protected_sets = get_protected_tool_sets()
    categories = tool_set_string.strip("+").split("+")
    requested_sets = [name.strip() for name in categories if name.strip()]

    missing_permissions = []
    for tool_set in requested_sets:
        if tool_set in protected_sets:
            required_role = protected_sets[tool_set]
            if required_role not in user_roles:
                missing_permissions.append(tool_set)

    return missing_permissions


async def cleanup() -> None:
    """Clean up resources for all tools on shutdown."""
    # Iterate through all tool categories
    for _category, tools in tool_sets.items():
        for tool in tools:
            # Check if tool has a cleanup method
            if hasattr(tool, "cleanup") and callable(tool.cleanup):
                await tool.cleanup()
            # Also check for __del__ for backward compatibility
            elif hasattr(tool, "__del__"):
                tool.__del__()
