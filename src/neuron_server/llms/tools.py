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
from neuron_server.tools.arxiv_tool import ArxivTool
from neuron_server.tools.dalle_tool import DalleTool
from neuron_server.tools.elevenlabs_tts_tool import ElevenLabsTTSTool
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
from langchain_community.utilities.wolfram_alpha import WolframAlphaAPIWrapper
from langchain_community.tools import WolframAlphaQueryRun
from neuron_server.tools.code_interpreter_tool import CodeInterpreterTool

homeassistant_api = HomeAssistantAPI(token=config.homeassistant.token)

tool_sets: Dict[str, List[BaseTool]] = {
    "nasa": [],
    "charts": [],
    "image": [
        DalleTool(),
        HuggingFaceServerlessImageGenerationTool(),
        Automatic1111Tool(
            api=Automatic1111API(
                output_directory=os.path.join(config.static_folder, "images"),
                endpoint=config.automatic1111_endpoint,
            )
        ),
    ],
    "tts": [
        ElevenLabsTTSTool(),
        FFmpegTool(),
    ],
    "search": [
        TavilySearchResults(
            max_results=5, include_raw_content=True, search_depth="advanced"
        ),
        WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()),
        WolframAlphaQueryRun(api_wrapper=WolframAlphaAPIWrapper()),
    ],
    "arxiv": [
        ArxivTool(),
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
        AstrophotonsRecommendationTool(),
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
            *tool_sets["image"],
            *tool_sets["search"],
            *tool_sets["tts"],
        ]
    }.values()
)


def get_tools(query: str) -> List[BaseTool]:
    ts = [tool for name in [*query.strip("+").split("+")] for tool in tool_sets[name]]
    if config.memory_enabled:
        # ts.append(MemoryRecallTool())
        ts.append(MemoryStoreTool())
    return list({tool.name: tool for tool in ts}.values())
