from langchain_community.tools.tavily_search import TavilySearchResults
from neuron_server.tools.hugging_face_serverless_image_generation_tool import (
    HuggingFaceServerlessImageGenerationTool,
)
from neuron_server.tools.inspect_image_tool import InspectImageTool

from neuron_server.tools.inspect_webcam_tool import InspectWebcamTool, Camera
from neuron_server.tools.security_camera_tool import SecurityCameraTool
from neuron_server.tools.homeassistant_tool import HomeAssistantTool, HomeAssistantAPI
from neuron_server.tools.homeassistant_service_tool import HomeAssistantServiceTool
from neuron_server.tools.dalle_tool import DalleTool
from neuron_server.tools.arxiv_tool import ArxivTool
from neuron_server.tools.elevenlabs_tts_tool import ElevenLabsTTSTool
from neuron_server.config import config
from neuron_server.tools.elevenlabs_soundeffects_tool import ElevenLabsSoundEffectsTool
from neuron_server.tools.ffmpeg_tool import FFmpegTool
from neuron_server.tools.arxiv_summary_tool import ArxivSummaryTool


homeassistant_api = HomeAssistantAPI(token=config.homeassistant.token)

tools = [
    TavilySearchResults(max_results=3),
    ArxivTool(),
    ArxivSummaryTool(),
    # HuggingFaceServerlessImageGenerationTool(),
    InspectImageTool(),
    # InspectWebcamTool(camera=Camera()),
    SecurityCameraTool(),
    HomeAssistantTool(api=homeassistant_api),
    # HomeAssistantServiceTool(api=homeassistant_api),
    DalleTool(),
    ElevenLabsTTSTool(),
    # ElevenLabsSoundEffectsTool(),
    FFmpegTool(),
]
