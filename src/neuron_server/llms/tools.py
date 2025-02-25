from langchain.tools import BaseTool
from langchain_community.tools.tavily_search import TavilySearchResults

from neuron_server.config import config
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
from neuron_server.tools.dalle_tool import DalleTool
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
from neuron_server.tools.graph_query_tool import GraphQueryTool
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
from neuron_server.tools.inspect_document_tool import InspectDocumentTool
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
from neuron_server.tools.moon_tool import MoonTool
from neuron_server.tools.openai_tts_tool import OpenAITTSTool
from neuron_server.tools.openweathermap_forecast_tool import (
    OpenWeatherMapForecastTool,
)
from neuron_server.tools.openweathermap_overview_tool import (
    OpenWeatherMapOverviewTool,
)
from neuron_server.tools.replicate_audio_generation_tool import (
    ReplicateAudioGenerationTool,
)
from neuron_server.tools.replicate_image_generation_tool import (
    ReplicateImageGenerationTool,
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
from neuron_server.tools.sun_tool import SunTool
from neuron_server.tools.whisper_stt_tool import WhisperSTTTool

homeassistant_api = HomeAssistantAPI(token=config.homeassistant.token)

# Initialize toolsets that require configuration
glados_toolset = GladosToolset()

tool_sets: dict[str, list[BaseTool]] = {
    "nasa": [],
    "glados": glados_toolset.tools,
    "charts": [],
    "reasoning": [
        DeepSeekReasoningTool(),
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
        GraphQueryTool(),
        GraphArxivImportTool(),
        GraphImportTool(),
        GraphWebsiteImportTool(),
    ],
    "inspect": [
        InspectImageTool(),
        InspectDocumentTool(),
    ],
    "document_query": [],
    "image": [
        DalleTool(),
        ReplicateImageGenerationTool(),
        InspectImageTool(),
        AppImageTool(),
    ],
    "video": [
        FFmpegTool(),
        InspectImageTool(),
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
        OpenAITTSTool(),
        ElevenLabsTTSTool(),
        ReplicatePlayDialogTool(),
        FFmpegTool(),
        WhisperSTTTool(),
    ],
    "search": [
        TavilySearchResults(
            max_results=5, include_raw_content=True, search_depth="advanced"
        ),
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
    ],
}

default_tools: list[BaseTool] = list(
    {
        tool.name: tool
        for tool in [
            *tool_sets["inspect"],
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
personality_tools: list[BaseTool] = []


def get_tools(query: str) -> list[BaseTool]:
    """Get tools based on query string.

    Args:
        query: Query string containing tool categories separated by '+'

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

    return list({tool.name: tool for tool in ts}.values())
