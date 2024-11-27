from neuron_server.config import config
import os
from langchain_community.tools.tavily_search import TavilySearchResults
from neuron_server.tools.hugging_face_serverless_image_generation_tool import (
    HuggingFaceServerlessImageGenerationTool,
)
from neuron_server.tools.inspect_image_tool import InspectImageTool

from neuron_server.tools.inspect_webcam_tool import InspectWebcamTool, Camera
from neuron_server.tools.security_camera_tool import SecurityCameraTool
from neuron_server.tools.homeassistant_api import (
    HomeAssistantAPI,
)
from neuron_server.config import config
from neuron_server.tools.arxiv_summary_tool import ArxivSummaryTool
from neuron_server.tools.arxiv_tool import ArxivTool
from neuron_server.tools.dalle_tool import DalleTool
from neuron_server.tools.elevenlabs_soundeffects_tool import ElevenLabsSoundEffectsTool
from neuron_server.tools.elevenlabs_tts_tool import ElevenLabsTTSTool
from neuron_server.tools.openai_tts_tool import OpenAITTSTool
from neuron_server.tools.ffmpeg_tool import FFmpegTool
from neuron_server.tools.ffprobe_tool import FFProbeTool
from neuron_server.tools.homeassistant_sensor_tool import HomeAssistantSensorTool
from neuron_server.tools.homeassistant_service_tool import HomeAssistantServiceTool
from neuron_server.tools.dice_tool import DiceTool
from neuron_server.tools.send_notification_tool import SendNotificationTool
from neuron_server.tools.wait_tool import WaitTool
from neuron_server.tools.automatic1111_tool import Automatic1111Tool, Automatic1111API

homeassistant_api = HomeAssistantAPI(token=config.homeassistant.token)

image_tools = [
    DalleTool(),
    HuggingFaceServerlessImageGenerationTool(),
    # Automatic1111Tool(
    #     api=Automatic1111API(
    #         output_directory=os.path.join(config.static_folder, "images"),
    #         endpoint="http://192.168.1.211:7860",
    #     )
    # ),
]

search_tools = [
    TavilySearchResults(max_results=5),
    ArxivTool(),
    ArxivSummaryTool(),
]

tts_tools = [
    # OpenAITTSTool(),
    ElevenLabsTTSTool(),
    # ElevenLabsSoundEffectsTool(),
]

ffmpeg_tools = [
    FFmpegTool(),
    FFProbeTool(),
]

homeassistant_tools = [
    InspectImageTool(),
    WaitTool(),
    SecurityCameraTool(),
    SendNotificationTool(),
    HomeAssistantSensorTool(api=homeassistant_api),
    # HomeAssistantServiceTool(api=homeassistant_api),
]

# webcam_tools = [
#     InspectWebcamTool(camera=Camera()),
# ]

tools = [
    DiceTool(),
    *image_tools,
    *search_tools,
    *tts_tools,
    *ffmpeg_tools,
    *homeassistant_tools,
]
