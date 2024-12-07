from neuron_server.config import config
from langchain_community.tools.tavily_search import TavilySearchResults
from neuron_server.tools.dice_tool import DiceTool
from neuron_server.tools.hugging_face_serverless_image_generation_tool import (
    HuggingFaceServerlessImageGenerationTool,
)
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
from neuron_server.tools.wait_tool import WaitTool
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

# from neuron_server.tools.inspect_webcam_tool import InspectWebcamTool, Camera

homeassistant_api = HomeAssistantAPI(token=config.homeassistant.token)

image_tools = [
    DalleTool(),
    HuggingFaceServerlessImageGenerationTool(),
]

tts_tools = [
    ElevenLabsTTSTool(),
]

search_tools = [
    TavilySearchResults(
        max_results=5, include_raw_content=True, search_depth="advanced"
    ),
    ArxivTool(),
    ArxivSummaryTool(),
    WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()),
]

ffmpeg_tools = [
    FFmpegTool(),
]

homeassistant_tools = [
    SecurityCameraTool(),
    SendNotificationTool(),
    HomeAssistantServiceTool(api=homeassistant_api),
    HomeAssistantSensorTool(api=homeassistant_api),
    OpenWeatherMapOverviewTool(),
    OpenWeatherMapForecastTool(),
]

astro_tools = [
    MoonTool(),
    SunTool(),
    AstrosphericForecastTool(),
    AstroCoordinatesTool(),
    AstroTargetSearchTool(),
    AstroObjectSearchTool(),
    AstroObservabilityTool(),
    AstroFinderImageTool(),
    AstrophotonsRecommendationTool(),
]

tools = [
    DiceTool(),
    WaitTool(),
    *image_tools,
    *search_tools,
    *tts_tools,
    *ffmpeg_tools,
    *homeassistant_tools,
    *astro_tools,
    # InspectWebcamTool(camera=Camera(device=0)),
]
