from pydantic import (
    BaseModel,
    Field,
)
from dotenv import load_dotenv
import os
from uuid import UUID

# Load environment variables from a .env file
load_dotenv()


class PushoverConfig(BaseModel):
    token: str = Field(
        default=os.environ.get("PUSHOVER_API_TOKEN"), description="Pushover API token"
    )
    user: str = Field(
        default=os.environ.get("PUSHOVER_USER_KEY"), description="Pushover user key"
    )


class DatabaseConfig(BaseModel):
    host: str = Field(
        default=os.environ.get("POSTGRES_HOST", "localhost"),
        description="Database host",
    )
    port: int = Field(
        default=int(os.environ.get("POSTGRES_PORT", 5432)), description="Database port"
    )
    user: str = Field(
        default=os.environ.get("POSTGRES_USER", "neuron"), description="Database user"
    )
    password: str = Field(
        default=os.environ.get("POSTGRES_PASSWORD"),
        description="Database password",
    )
    database: str = Field(
        default=os.environ.get("POSTGRES_DB", "neuron"),
        description="Database database",
    )


class RedisConfig(BaseModel):
    host: str = Field(
        default=os.environ.get("REDIS_HOST", "localhost"),
        description="Redis host",
    )
    port: int = Field(
        default=int(os.environ.get("REDIS_PORT", 6379)), description="Redis port"
    )
    db: int = Field(
        default=int(os.environ.get("REDIS_DB", 0)), description="Redis database"
    )


class HomeAssistantConfig(BaseModel):
    server: str = Field(
        default=os.environ.get("HOMEASSISTANT_SERVER", "http://localhost:8123"),
        description="Home Assistant URL",
    )
    token: str = Field(
        default=os.environ.get("HOMEASSISTANT_TOKEN", ""),
        description="Home Assistant Token",
    )


class Neo4jConfig(BaseModel):
    url: str = Field(
        default=os.environ.get("NEO4J_URL", "bolt://localhost:7687"),
        description="Neo4j URL",
    )
    username: str = Field(
        default=os.environ.get("NEO4J_USERNAME", "neo4j"),
        description="Neo4j username",
    )
    password: str = Field(
        default=os.environ.get("NEO4J_PASSWORD"), description="Neo4j password"
    )


class Config(BaseModel):
    debug: bool = Field(
        default=os.environ.get("DEBUG", "False").lower() == "true",
        description="Debug mode",
    )
    hf_token: str = Field(
        default=os.environ.get("HF_TOKEN"), description="Hugging Face token"
    )
    openai_api_key: str = Field(
        default=os.environ.get("OPENAI_API_KEY"), description="OpenAI API key"
    )
    anthropic_api_key: str = Field(
        default=os.environ.get("ANTHROPIC_API_KEY"), description="Anthropic API key"
    )
    elevenlabs_api_key: str = Field(
        default=os.environ.get("ELEVENLABS_API_KEY"), description="ElevenLabs API key"
    )
    openweather_api_key: str = Field(
        default=os.environ.get("OPENWEATHER_API_KEY", ""),
        description="OpenWeather API key",
    )
    astrospheric_api_key: str = Field(
        default=os.environ.get("ASTROSPHERIC_API_KEY", ""),
        description="Astrospheric API key",
    )
    log_level: str = Field(
        default=os.environ.get("LOG_LEVEL", "DEBUG"), description="Log level"
    )
    provider_id: UUID = Field(
        default=UUID(os.environ.get("PROVIDER_ID")), description="Provider ID"
    )
    host: str = Field(default=os.environ.get("HOST", "0.0.0.0"), description="Host")
    port: int = Field(default=int(os.environ.get("PORT", 5000)), description="Port")
    client_assets_folder: str = Field(
        default=os.path.abspath(
            os.environ.get("STATIC_FOLDER", "./src/neuron_client/dist")
        ),
        description="Static folder",
    )
    static_folder: str = Field(
        default=os.path.abspath(os.environ.get("OUTPUT_FOLDER", "./static")),
        description="Output folder for generated and downloaded files",
    )
    static_content_url: str = Field(
        default=os.environ.get("STATIC_CONTENT_URL", "http://localhost:5000/static"),
        description="Static content URL",
    )
    homeassistant: HomeAssistantConfig = HomeAssistantConfig()
    temp_folder: str = Field(
        default=os.path.abspath(os.environ.get("TEMP_FOLDER", "./tmp")),
        description="Temp folder",
    )
    tablet_image_filename: str = Field(
        default=os.path.abspath(
            os.environ.get(
                "TABLET_IMAGE_FILENAME", "./static/images/dalle_generated_image.png"
            )
        ),
        description="Tablet image filename",
    )
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    pushover: PushoverConfig = PushoverConfig()
    memory_enabled: bool = Field(
        default=os.environ.get("MEMORY_ENABLED", "True").lower() == "true",
        description="Memory enabled",
    )
    automatic1111_endpoint: str = Field(
        default=os.environ.get("AUTOMATIC1111_ENDPOINT", "http://192.168.1.211:7860"),
        description="Automatic1111 API URL",
    )
    firecrawl_api_key: str = Field(
        default=os.environ.get("FIRECRAWL_API_KEY"),
        description="FireCrawl API key",
    )
    neo4j: Neo4jConfig = Neo4jConfig()

    allowed_file_types: list[str] = Field(
        default=[
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".pdf",
            ".txt",
            ".md",
            ".csv",
            ".srt",
            ".vtt",
            ".mp3",
            ".wav",
            ".mp4",
        ],
        description="Allowed file types",
    )
    max_file_size: int = Field(
        default=10_000_000,
        description="Maximum file size in bytes",
    )
    auth0_domain: str = Field(
        default=os.environ.get("AUTH0_DOMAIN", "dev-c33mi6x6gyem2l5o.us.auth0.com"),
        description="Auth0 domain",
    )
    auth0_api_audience: str = Field(
        default=os.environ.get("AUTH0_API_AUDIENCE", "https://neuron.zaks.io/api"),
        description="API audience",
    )
    auth0_client_id: str = Field(
        default=os.environ.get("AUTH0_CLIENT_ID", "LYSbL0a44J1McAObzNLfSRdoBZ7KwfPR"),
        description="Auth0 client ID",
    )


config = Config()
