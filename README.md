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
- And more...

The system is designed to be highly modular, allowing easy addition of new tools and capabilities. Whether you need help planning an astrophotography session, generating creative content, or analyzing research papers, Neuron provides a flexible framework for natural language interaction with a growing suite of specialized tools.

## Tools

Neuron integrates a diverse collection of tools designed to enhance its capabilities across multiple domains. At its core, it offers robust support for astronomical research and observation planning, complemented by powerful AI-driven media generation capabilities including image, audio, and video creation. The system can assist with research tasks through document analysis and knowledge graph integration, while also providing practical utilities like weather forecasting and home automation controls. These tools enable Neuron to serve as a versatile assistant that can handle both technical and creative tasks, from planning astrophotography sessions to generating AI content. Below is a comprehensive list of available tools and their primary functions:

| Tool                                 | Description                              |
| ------------------------------------ | ---------------------------------------- |
| ArxivSearch                          | Search Arxiv                             |
| AstroCoordinates                     | Get RA/Dec coordinates of the sky zenith |
| AstroFinderImage                     | Get the finger image for an object       |
| AstroObjectSearch                    | Search for an astro object               |
| AstroObservability                   | Get observability data                   |
| AstrophotonsRecommendation           | Get recommendations for astrophotography |
| AstrosphericForecast                 | Get astrospheric forecast                |
| AstroTargetSearch                    | Search for a target in Simbad            |
| CodeInterpreter                      | Run python code                          |
| Dalle                                | Generate images using dalle-e            |
| Dice                                 | Roll virtual dice                        |
| ElevenLabsTTS                        | Generate speech                          |
| FFmpeg                               | Edit audio and video                     |
| GraphArxivImport                     | Import arxiv papers                      |
| GraphImport                          | Import documents                         |
| GraphQuestion                        | Ask a question of the knowledge graph    |
| GraphWebsiteImport                   | Import websites                          |
| HD2GalacticWarReport                 | Get a report on the HD galactic war      |
| HD2LiberationHistory                 | Planet liberation history                |
| HuggingFaceServerlessImageGeneration | Generate images                          |
| InspectImage                         | Inspect an image                         |
| Moon                                 | Get information about the moon           |
| OpenWeatherMapForecast               | Get forecast                             |
| OpenWeatherMapOverview               | Get overview                             |
| ReplicateAudioGeneration             | Generate foley audio                     |
| ReplicateImageGeneration             | Generate images using flux               |
| ReplicateSoundEffectGeneration       | Generate sound effects                   |
| ReplicateVideoGeneration             | Generate videos                          |
| SecurityCamera                       | Access home assistant security cameras   |
| SendNotification                     | Send a notification                      |
| Sun                                  | Get information about the sun            |

## Use Cases

- Plan an astrophotography session
- Generate images, videos and audio using the latest models
- Analyze research papers and generate summaries
- Get weather forecasts and observability data for astrophotography
- Control home automation and sensors
- Role playing
- Coding Assistant
- Generate an always up to date image on my smart tablet
- Hell Divers 2 live war status
- Bring still photos to life

## Project Structure

- `src/neuron_server`: The main server application that handles the chat interface, tool integration, and persistent memory.
- `src/neuron_server/tools`: Contains the tools that Neuron can use.
- `src/neuron_client`: The client application that allows you to interact with the server.
