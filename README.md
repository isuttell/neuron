# Neuron

Neuron is an advanced AI chat platform that combines real-time conversation with powerful specialized tools. It actively helps you plan astrophotography sessions, generate AI art and videos, analyze research papers, and even control your smart home devices. It's built to be modular, so you can easily add new capabilities as you need them. Whether you're a researcher, creator, or tech enthusiast, Neuron provides a natural language interface to a growing suite of specialized tools that can help you get things done.

## What is it?

Neuron is a realtime chat application built with LangChain and LangGraph that provides an extensible platform for testing and experimenting with various LLM models and tool capabilities. It features:

- Threaded conversations with persistent memory
- Multiple specialized AI personalities with dedicated toolsets
- Rich integration with astronomical tools and data sources
- AI content generation for images, audio, and video
- Home automation and sensor monitoring
- Research assistance with arXiv integration
- Knowledge graph integration with Neo4j
- Media management with collections and sharing
- Scheduled prompts and automated tasks
- And more...

The system is designed to be highly modular, allowing easy addition of new tools and capabilities. Whether you need help planning an astrophotography session, generating creative content, or analyzing research papers, Neuron provides a flexible framework for natural language interaction with a growing suite of specialized tools.

## Architecture

Neuron consists of several key components:

- **Backend**: Python-based server using Quart for async HTTP and WebSocket support
- **Frontend**: React application with TypeScript, Redux, and Shadcn UI components
- **Database**: PostgreSQL with PGVector for vector storage
- **Knowledge Graph**: Neo4j for semantic data relationships
- **Cache**: Redis for pub/sub messaging and task scheduling
- **AI Integration**: LangChain and LangGraph for LLM workflows

The application uses a WebSocket-based event system for real-time communication between the client and server, with REST endpoints for resource management.

## Tools

Neuron integrates a diverse collection of tools designed to enhance its capabilities across multiple domains. At its core, it offers robust support for astronomical research and observation planning, complemented by powerful AI-driven media generation capabilities including image, audio, and video creation. The system can assist with research tasks through document analysis and knowledge graph integration, while also providing practical utilities like weather forecasting and home automation controls.

Tools are organized into categories that can be combined for different AI personalities:

| Category         | Description                                          |
| ---------------- | ---------------------------------------------------- |
| astro            | Astronomical tools for observation planning and data |
| arxiv            | Research paper search and analysis                   |
| audio            | Audio generation and processing tools                |
| code_interpreter | Python code execution in a sandboxed environment     |
| dice             | Random number generation and dice rolling            |
| graph            | Knowledge graph interaction and document import      |
| hd2              | Helldivers 2 game status tracking                    |
| homeassistant    | Smart home control and monitoring                    |
| image            | Image generation and analysis                        |
| inspect          | Document and image inspection                        |
| memory           | Long-term memory storage and retrieval               |
| reasoning        | Enhanced reasoning capabilities                      |
| search           | Web search integration                               |
| tts              | Text-to-speech synthesis                             |
| video            | Video generation and editing                         |
| weather          | Weather forecasting and conditions                   |

Below is a selection of available tools and their primary functions:

| Tool                         | Description                                     |
| ---------------------------- | ----------------------------------------------- |
| ArxivSearch                  | Search academic papers on arXiv                 |
| ArxivSummary                 | Generate summaries of arXiv papers              |
| AstroCoordinates             | Get RA/Dec coordinates of the sky zenith        |
| AstroFinderImage             | Get finder charts for astronomical objects      |
| AstroObjectSearch            | Search for astronomical objects                 |
| AstroObservability           | Get observability data for planning             |
| AstrosphericForecast         | Get astronomical viewing conditions             |
| AstroTargetSearch            | Search for targets in astronomical databases    |
| CodeInterpreter              | Run Python code in a sandboxed environment      |
| DalleTool                    | Generate images using DALL-E models             |
| DeepSeekReasoningTool        | Enhanced reasoning for complex problems         |
| DiceTool                     | Roll virtual dice with various configurations   |
| ElevenLabsTTSTool            | Generate realistic speech from text             |
| FFmpegTool                   | Edit and process audio and video files          |
| GraphArxivImportTool         | Import arXiv papers to knowledge graph          |
| GraphQuestionTool            | Ask questions of the knowledge graph            |
| GraphWebsiteImportTool       | Import websites to knowledge graph              |
| HD2GalacticWarReportTool     | Get Helldivers 2 war status reports             |
| InspectImageTool             | Analyze and describe image content              |
| MediaListTools               | Manage media collections and sharing            |
| MemoryRecallTool             | Retrieve information from long-term memory      |
| MemoryStoreTool              | Store information in long-term memory           |
| MoonTool                     | Get information about lunar phases and position |
| OpenWeatherMapTools          | Access weather forecasts and conditions         |
| ReplicateImageGenerationTool | Generate images using Replicate models          |
| ReplicateVideoGenerationTool | Create videos with AI models                    |
| SecurityCameraTool           | Access home security camera feeds               |
| SendNotificationTool         | Send notifications to mobile devices            |
| SunTool                      | Get information about solar position and events |
| WhisperSTTTool               | Convert speech to text                          |

## Use Cases

- Plan astrophotography sessions with weather and observability data
- Generate images, videos, and audio using state-of-the-art AI models
- Analyze research papers and generate summaries
- Build and query knowledge graphs from documents and websites
- Control home automation devices and monitor sensors
- Create and manage media collections with AI-generated content
- Get real-time Helldivers 2 war status updates
- Execute Python code for data analysis and visualization
- Schedule automated tasks and prompts
- Enhance photos with AI-powered tools

## Project Structure

- `src/neuron_server`: The main server application
  - `controllers`: API endpoints and WebSocket handlers
  - `tools`: LangChain tool implementations
  - `models`: Database models and business logic
  - `llms`: LLM integration and workflow definitions
  - `graph`: Knowledge graph integration
- `src/neuron_client`: The React frontend application
  - `src/components`: UI components and layouts
  - `src/slices`: Redux state management
  - `src/actions`: Redux actions and API calls
  - `src/routes`: Application routes and pages

## Installation and Setup

### Prerequisites

- Python 3.11
- Node.js 20+
- PostgreSQL with pgvector extension
- Neo4j 5.x
- Redis 7.x

### Environment Variables

Neuron uses various environment variables for configuration. Key variables include:

```
# Server configuration
DEBUG=False
HOST=0.0.0.0
PORT=5000

# Database configuration
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/neuron

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# API keys for various services
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
REPLICATE_API_KEY=your_replicate_key

# Optional integrations
HOMEASSISTANT_URL=http://homeassistant.local:8123
HOMEASSISTANT_TOKEN=your_long_lived_token
```

### Development Setup

1. Clone the repository:

```bash
git clone https://github.com/isuttell/neuron.git
cd neuron
```

2. Install Python dependencies using Poetry:

```bash
pipx install poetry
poetry install
```

3. Run tests and check code coverage:

```bash
# Run backend tests
poetry run pytest src/neuron_server/

# Run backend tests with coverage report
poetry run pytest src/neuron_server/ --cov=src/neuron_server/ --cov-report=term

# Lint backend code
poetry run ruff check --fix src/neuron_server/
```

4. Install frontend dependencies:

```bash
npm install
```

5. Start the development servers:

```bash
# Terminal 1: Start the backend
poetry run python -m neuron_server

# Terminal 2: Start the frontend
npm run dev
```

6. Access the application at http://localhost:5174

### Docker Deployment

Neuron can be deployed using Docker and Docker Compose:

```bash
docker-compose up -d
```

This will start the following services:

- Neuron server
- PostgreSQL database
- Neo4j graph database
- Redis cache

Access the application at http://localhost:5000

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for the LLM framework
- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Quart](https://github.com/pallets/quart) for the async web framework
- [React](https://reactjs.org/) for the frontend framework
- [Shadcn UI](https://ui.shadcn.com/) for the UI components
- All the amazing open-source projects that make Neuron possible

---

Neuron is continuously evolving with new tools and capabilities. Feel free to reach out with questions or suggestions!
