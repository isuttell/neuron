# Tools

Neuron provides a comprehensive suite of tools that personalities can use to extend their capabilities. Tools are organized into tool sets (groups of related tools) that you select when creating or configuring a personality. You don't pick individual tools - instead, you choose tool sets that provide related functionality together.

## Available Tool Sets

Each tool set below contains multiple related tools that work together. When you enable a tool set for a personality, all tools in that set become available.

### Image
**Image Generation & Manipulation Tool Set**
- **Replicate Image Generation**: Create AI-generated images using advanced models like Flux
- **Kontext Image**: Generate context-aware images with scene understanding
- **Inspect Image**: Analyze and describe uploaded images in detail
- **App Image**: Application-specific image processing and generation

### Audio
**Audio Processing & Generation Tool Set**
- **FFmpeg**: Professional audio/video processing and format conversion
- **ElevenLabs Sound Effects**: Generate realistic sound effects
- **Music Generation**: Create original music tracks and compositions
- **Whisper STT**: Speech-to-text transcription for audio files

### TTS (Text-to-Speech)
**Voice Synthesis Tool Set**
- **ElevenLabs TTS**: High-quality voice synthesis with 20+ character voices
- **PlayDialog**: Natural conversational text-to-speech
- **Kokoro TTS**: Advanced Japanese and multilingual voice synthesis
- **FFmpeg**: Audio processing and format conversion
- **Whisper STT**: Speech transcription capabilities

### Video
**Video Creation & Processing Tool Set**
- **Video Generation**: AI-powered video creation from text prompts
- **FFmpeg**: Professional video editing and format conversion
- **Audio Generation**: Create soundtracks for videos
- **Music Generation**: Generate background music
- **Image Inspection**: Analyze video frames

### Search
**Web & Document Search Tool Set**
- **Tavily Search**: Advanced web search with filtering capabilities
- **Document Inspection**: Extract and analyze content from online documents

### ArXiv
**Academic Research Tool Set**
- **ArXiv Search**: Search academic papers and publications
- **ArXiv Summary**: Generate summaries of research papers
- **ArXiv Recall**: Retrieve and reference previously accessed papers

### Graph
**Knowledge Graph Management Tool Set**
- **Graph Question**: Query knowledge graph for semantic relationships
- **ArXiv Import**: Import research papers into knowledge graph
- **Graph Import**: Add documents to knowledge graph
- **Website Import**: Import web content into knowledge graph
- **ArXiv Search**: Search for papers to import

### Memory
**Information Persistence Tool Set**
- **Memory Store**: Save information for long-term recall
- **Memory Recall**: Retrieve previously stored information using semantic search

### Code Interpreter
**Code Execution Tool Set**
- **Code Interpreter**: Execute Python code with scientific libraries
- **Pyodide Code Interpreter**: Browser-based Python execution environment

### Astronomy (Astro)
**Astronomical Tool Set**
- **Moon Tool**: Moon phases and lunar information
- **Sun Tool**: Sunrise, sunset, and solar position data
- **Astrospheric Forecast**: Astronomical weather forecasting
- **Coordinates Tool**: Celestial coordinate conversions
- **Target Search**: Find astronomical objects
- **Object Search**: Query celestial object databases
- **Observability Tool**: Calculate object visibility
- **Finder Image**: Generate star charts and finder images
- **Weather Tools**: Current conditions and forecasts

### Weather
**Weather Information Tool Set**
- **Astrospheric Forecast**: Specialized weather for astronomy
- **OpenWeatherMap Overview**: Current weather conditions
- **OpenWeatherMap Forecast**: Detailed weather forecasts

### Finance
**Financial Data Tool Set**
- **AlphaVantage**: Stock market data, quotes, and financial indicators

### Dice
**Random Generation Tool Set**
- **Dice Tool**: Roll dice and generate random numbers for games and decisions

### HD2 (Helldivers 2)
**Game Data Tool Set**
- **Galactic War Report**: Current war status and planet liberation data
- **Liberation History**: Historical campaign and liberation records

### GLaDOS
**Character Voice Tool Set**
- **GLaDOS TTS**: Portal character voice synthesis (locally generated)

### Neuron
**System Tool Set**
- **Release Commits**: Track Neuron system updates and changes

## System Tools

These tools are automatically available to all personalities:

### Media Lists
Manage collections of generated content:
- Create, read, update, and delete media lists
- Add and remove items from lists
- Reorder list contents
- Control access permissions

### Schedule Tools
Time-based task management:
- Schedule prompts for future execution
- List scheduled tasks
- Remove scheduled items

### Thread Memory
Conversation-specific memory:
- Read thread-specific stored information
- Set thread memory for context persistence

### Inspect Tools
Content analysis (enabled by default):
- **Inspect Image**: Analyze and describe images
- **Inspect Document**: Extract and analyze document content

---

## How Tool Sets Work

When configuring a personality, you select which tool sets to enable rather than individual tools. Each tool set provides a complete group of related functionality. For example:
- Selecting the **Image** tool set gives the personality all image generation and analysis capabilities
- Choosing **ArXiv** provides the full suite of academic research tools
- Enabling **Astro** includes all astronomy-related tools plus weather integration

Tool sets are designed to work together - you can combine multiple sets to create personalities with diverse capabilities. The system ensures all tools within each selected set integrate seamlessly with the conversation flow.

---

Tool sets are continuously being expanded and improved. Each set is carefully curated to provide comprehensive functionality for its domain while maintaining natural interactions.
