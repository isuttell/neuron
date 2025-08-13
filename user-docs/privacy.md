# Privacy

Neuron is designed with privacy and data control in mind. This policy explains how your data is handled, stored, and shared within the system.

## System Administration

**Please note:** Neuron is Isaac's development project. As the system administrator, Isaac has full access to the infrastructure and data for maintenance, debugging, and development purposes. Do not share anything with Neuron that you are not comfortable with Isaac potentially seeing if he needs to work on or debug the system.

## Where Your Data Lives

Your data is stored locally in Isaac's homelab infrastructure, located in his garage. This includes your message history, personality configurations, thread conversations, and all generated content. The goal is to maintain control over your data rather than storing it with third-party services.

## How Data Sharing Works

### Personalities
You own the personalities you create. You can choose to share them with other users, giving them access to interact with your personality configurations.

### Conversations (Threads)
Your conversations are private by default. You can invite specific users to individual threads to share conversations and collaborate.

### Personality Memories
When you interact with a personality, it can form memories from your conversations. These memories are shared among all users who have access to that personality.

**Important to know:** If you ask a personality to remember something private, other users with access to that personality may see that information. Consider personality memories as shared within the user group.

## Cloud Service Usage

### AI Model Interactions
When you interact with personalities, required data (messages, context, memories) is sent to remote cloud AI providers using Isaac's personal API keys. Training has been disabled on these requests where possible. The privacy policies of individual AI providers (OpenAI, Anthropic, Google, etc.) apply to this data transmission.

### Tool Integrations
Various tools connect to cloud services for image generation, text-to-speech, video creation, web search, and other functions. When using these tools, necessary data is sent to the respective service providers to complete your request. Results are then downloaded and stored permanently in the local homelab. Each service provider's privacy policy applies to their specific usage.

## Data Control Philosophy

The goal of this project is to maintain control over as much user data as possible, only sending data to cloud services when absolutely required for functionality. We store results locally to minimize ongoing data sharing with external providers.

## Future Plans

The long-term goal is to run high-quality AI models and generation tools locally when it becomes more economically feasible. This would further reduce data sharing with external services and provide even greater control over your information.

## Third-Party Services

When your data is processed by external cloud providers, their respective privacy policies apply. This includes but is not limited to AI model providers, image generation services, and other integrated tools. We recommend reviewing the privacy policies of services you actively use.

---

This privacy policy reflects the current implementation and may be updated as the system evolves.
