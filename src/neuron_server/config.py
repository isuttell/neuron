import os

from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    Field,
)

# Load environment variables from a .env file
load_dotenv()


class PushoverConfig(BaseModel):
    token: str = Field(
        default=os.environ.get("PUSHOVER_API_TOKEN", ""),
        description="Pushover API token",
    )
    user: str = Field(
        default=os.environ.get("PUSHOVER_USER_KEY", ""), description="Pushover user key"
    )


class DatabaseConfig(BaseModel):
    host: str = Field(
        default=os.environ.get("POSTGRES_HOST", "localhost"),
        description="Database host",
    )
    port: int = Field(
        default=int(os.environ.get("POSTGRES_PORT", "5432")),
        description="Database port",
    )
    user: str = Field(
        default=os.environ.get("POSTGRES_USER", "neuron"),
        description="Database user",
    )
    password: str = Field(
        default=os.environ.get("POSTGRES_PASSWORD", ""),
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
        default=int(os.environ.get("REDIS_PORT", "6379")), description="Redis port"
    )
    db: int = Field(
        default=int(os.environ.get("REDIS_DB", "0")), description="Redis database"
    )
    password: str | None = Field(
        default=os.environ.get("REDIS_PASSWORD"), description="Redis password"
    )
    session_ttl: int = Field(
        default=int(os.environ.get("REDIS_SESSION_TTL", "86400")),
        description="Session TTL in seconds (default: 24 hours)",
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
        default=os.environ.get("NEO4J_PASSWORD", ""), description="Neo4j password"
    )


class Config(BaseModel):
    api_key: str = Field(
        default=os.environ.get("API_KEY", ""),
        description="API key for webhook authentication",
    )
    debug: bool = Field(
        default=os.environ.get("DEBUG", "False").lower() == "true",
        description="Debug mode",
    )
    llm_debug: bool = Field(
        default=os.environ.get("LLM_DEBUG", "False").lower() == "true",
        description="LLM debug mode",
    )
    hf_token: str = Field(
        default=os.environ.get("HF_TOKEN", ""), description="Hugging Face token"
    )
    openai_api_key: str = Field(
        default=os.environ.get("OPENAI_API_KEY", ""), description="OpenAI API key"
    )
    openrouter_api_key: str = Field(
        default=os.environ.get("OPENROUTER_API_KEY", ""),
        description="OpenRouter API key",
    )
    anthropic_api_key: str = Field(
        default=os.environ.get("ANTHROPIC_API_KEY", ""), description="Anthropic API key"
    )
    elevenlabs_api_key: str = Field(
        default=os.environ.get("ELEVENLABS_API_KEY", ""),
        description="ElevenLabs API key",
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
        default=os.environ.get("LOG_LEVEL", "DEBUG").strip(), description="Log level"
    )
    host: str = Field(default=os.environ.get("HOST", "0.0.0.0"), description="Host")
    port: int = Field(default=int(os.environ.get("PORT", "5000")), description="Port")
    client_assets_folder: str = Field(
        default=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "neuron_client", "dist")
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
    static_require_auth: bool = Field(
        default=os.environ.get("STATIC_REQUIRE_AUTH", "True").lower() == "true",
        description="Require authentication for static content",
    )
    homeassistant: HomeAssistantConfig = HomeAssistantConfig()
    temp_folder: str = Field(
        default=os.path.abspath(os.environ.get("TEMP_FOLDER", "./tmp")),
        description="Temp folder",
    )
    # Workaround for Docker container access to the host's filesystem
    parent_temp_folder: str = Field(
        default=os.path.abspath(os.environ.get("PARENT_TEMP_FOLDER", "./tmp")),
        description="Parent temp folder",
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
    glados_endpoint: str = Field(
        default=os.environ.get("GLADOS_ENDPOINT", "http://192.168.1.160:7612"),
        description="GLaDOS TTS API URL",
    )
    firecrawl_api_key: str = Field(
        default=os.environ.get("FIRECRAWL_API_KEY", ""),
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
            ".webm",
            ".heic",
            ".heif",
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

    # CSRF Configuration
    secret_key: str = Field(
        default=os.environ.get(
            "SECRET_KEY", "dev-secret-key-only-for-local-development"
        ),
        description="Secret key for CSRF token signing. MUST be set in production!",
    )
    csrf_cookie_max_age: int = Field(
        default=int(os.environ.get("CSRF_COOKIE_MAX_AGE", "86400")),  # 24 hours
        description="CSRF cookie max age in seconds",
    )
    csrf_token_rotation: bool = Field(
        default=os.environ.get("CSRF_TOKEN_ROTATION", "True").lower() == "true",
        description="Enable CSRF token rotation on each request",
    )
    is_production: bool = Field(
        default=os.environ.get("ENVIRONMENT", "development").lower() == "production",
        description="Whether the application is running in production",
    )
    serve_client: bool = Field(
        default=os.environ.get("SERVE_CLIENT", "False").lower() == "true",
        description="Whether to serve client files from the Python server",
    )


config = Config()
