from neuron_server.config import config
from typing import List, Dict
import os
from langchain.tools import BaseTool
from langchain_community.tools.tavily_search import TavilySearchResults
from neuron_server.tools.dice_tool import DiceTool
from neuron_server.tools.hugging_face_serverless_image_generation_tool import (
    HuggingFaceServerlessImageGenerationTool,
)
from neuron_server.tools.automatic1111_tool import Automatic1111Tool, Automatic1111API
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from neuron_server.tools.security_camera_tool import SecurityCameraTool
from neuron_server.tools.homeassistant_api import HomeAssistantAPI
from neuron_server.tools.arxiv_summary_tool import ArxivSummaryTool
from neuron_server.tools.arxiv_search_tool import ArxivSearchTool
from neuron_server.tools.dalle_tool import DalleTool
from neuron_server.tools.elevenlabs_tts_tool import ElevenLabsTTSTool
from neuron_server.tools.elevenlabs_soundeffects_tool import (
    ElevenLabsSoundEffectsTool,
)
from neuron_server.tools.ffmpeg_tool import FFmpegTool
from neuron_server.tools.homeassistant_sensor_tool import HomeAssistantSensorTool
from neuron_server.tools.homeassistant_service_tool import HomeAssistantServiceTool
from neuron_server.tools.send_notification_tool import SendNotificationTool
from neuron_server.tools.openweathermap_overview_tool import OpenWeatherMapOverviewTool
from neuron_server.tools.openweathermap_forecast_tool import OpenWeatherMapForecastTool
from neuron_server.tools.astrospheric_forecast_tool import AstrosphericForecastTool
from neuron_server.tools.astro_target_search_tool import AstroTargetSearchTool
from neuron_server.tools.moon_tool import MoonTool
from neuron_server.tools.sun_tool import SunTool
from neuron_server.tools.astro_observability_tool import AstroObservabilityTool
from neuron_server.tools.astro_object_search_tool import AstroObjectSearchTool
from neuron_server.tools.astro_finder_image_tool import AstroFinderImageTool
from neuron_server.tools.astro_coordinates_tool import AstroCoordinatesTool
from neuron_server.tools.astrophotons_recommendation_tool import (
    AstrophotonsRecommendationTool,
)
from neuron_server.tools.memory_recall_tool import MemoryRecallTool
from neuron_server.tools.memory_store_tool import MemoryStoreTool
from neuron_server.tools.arxiv_recall_tool import ArxivRecallTool
from neuron_server.tools.hd2_galactic_war_report_tool import (
    HD2GalacticWarReportTool,
)
from neuron_server.tools.hd2_liberation_history_tool import HD2LiberationHistoryTool
from neuron_server.tools.code_interpreter_tool import CodeInterpreterTool
from neuron_server.tools.graph_question_tool import GraphQuestionTool
from neuron_server.tools.graph_arxiv_import_tool import GraphArxivImportTool
from neuron_server.tools.graph_import_tool import GraphImportTool
from neuron_server.tools.graph_website_import_tool import GraphWebsiteImportTool
from neuron_server.tools.replicate_video_generation_tool import (
    ReplicateVideoGenerationTool,
)
from neuron_server.tools.replicate_audio_generation_tool import (
    ReplicateAudioGenerationTool,
)
from neuron_server.tools.replicate_music_generation_tool import (
    ReplicateMusicGenerationTool,
)
from neuron_server.tools.replicate_image_generation_tool import (
    ReplicateImageGenerationTool,
)
from neuron_server.tools.inspect_image_tool import InspectImageTool
from neuron_server.tools.replicate_sound_effect_generation_tool import (
    ReplicateSoundEffectGenerationTool,
)
from neuron_server.tools.inspect_document_tool import DocumentInspectTool
from neuron_server.tools.app_image_tool import AppImageTool
from neuron_server.tools.openai_tts_tool import OpenAITTSTool
from neuron_server.tools.personality_prompt_tool import PersonalityPromptTool

homeassistant_api = HomeAssistantAPI(token=config.homeassistant.token)

tool_sets: Dict[str, List[BaseTool]] = {
    "nasa": [],
    "charts": [],
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
    "inspect": [
        InspectImageTool(),
        DocumentInspectTool(),
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
        # ReplicateSoundEffectGenerationTool(),
    ],
    "audio": [
        ElevenLabsSoundEffectsTool(),
        ReplicateMusicGenerationTool(),
    ],
    "tts": [
        OpenAITTSTool(),
        ElevenLabsTTSTool(),
        FFmpegTool(),
    ],
    "search": [
        TavilySearchResults(
            max_results=5, include_raw_content=True, search_depth="advanced"
        ),
        InspectImageTool(),
        DocumentInspectTool(),
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

default_tools: List[BaseTool] = list(
    {
        tool.name: tool
        for tool in [
            *tool_sets["inspect"],
            *tool_sets["tts"],
        ]
    }.values()
)


def get_tools(query: str) -> List[BaseTool]:
    ts = [tool for name in [*query.strip("+").split("+")] for tool in tool_sets[name]]
    if config.memory_enabled:
        ts.append(MemoryRecallTool())
        ts.append(MemoryStoreTool())
    ts.append(PersonalityPromptTool())
    return list({tool.name: tool for tool in ts}.values())
