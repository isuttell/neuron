# Dashboard Viewer Backend Structure

The dashboard viewer backend has been refactored into logical modules:

## Module Structure

- **`config.py`** - Configuration management
  - Environment variables (URLs, ports, tokens)
  - Path definitions

- **`models.py`** - Pydantic data models
  - `SensorConfig` - Individual sensor configuration
  - `DashboardSensorConfig` - Overall sensor configuration with YAML loading

- **`websocket.py`** - WebSocket connection management
  - `ConnectionManager` - Handles WebSocket connections and broadcasting

- **`polling.py`** - Background polling tasks and state management
  - `PollingState` - Manages polling state for images and sensors
  - `fetch_and_cache_image()` - Image fetching and caching
  - `fetch_sensor_states()` - HomeAssistant sensor state fetching
  - `poll_for_sensors()` - Background task for sensor polling
  - `poll_for_changes()` - Background task for image change detection

- **`routes.py`** - API route definitions
  - Image endpoints (`/image`, `/image` HEAD)
  - WebSocket endpoint (`/ws`)
  - API endpoints (`/api/config`, `/api/status`, `/api/sensors`)
  - Test endpoints

- **`server.py`** - Main application entry point
  - FastAPI app initialization
  - Lifespan management
  - Static file serving
  - Main entry point

## Data Flow

1. **Startup**: Server loads configuration, initializes polling state, starts background tasks
2. **Image Polling**: Periodically checks for image changes via ETag
3. **Sensor Polling**: Fetches sensor states from HomeAssistant every 60 seconds
4. **WebSocket**: Broadcasts updates to connected clients when changes occur
5. **API**: Provides REST endpoints for current state queries
