import { SidebarTrigger } from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function Help() {
  return (
    <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex items-center justify-between mb-6 border-b pb-4 mobile-safe-top">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-lg lg:text-2xl font-bold">Help</h1>
        <div className="flex-1" />
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-6 max-w-2xl mx-auto">
          <section>
            <p className="text-muted-foreground leading-relaxed">
              Welcome to Neuron! This guide will help you get started and make the most of the platform's features.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Getting Started</h2>
            <p className="text-muted-foreground leading-relaxed mb-3">
              The default personality is <strong>Neuron</strong>. From the home page, you can jump right into a conversation
              by entering your message and hitting go. This creates a new thread that's private to you where you can
              interact with the AI personality.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              You can share threads with other users in the system through the actions menu in the top corner of any thread.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">How Conversations Work</h2>
            <p className="text-muted-foreground leading-relaxed mb-3">
              Neuron isn't a traditional chat app. Every time you hit enter, it sends a complete prompt to the AI model,
              allowing for more thoughtful and comprehensive responses rather than quick back-and-forth messages.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Each conversation happens in a "thread" - think of it as a dedicated space for a particular topic or project
              where the AI can maintain context throughout your interaction.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Adding Context to Conversations</h2>
            <div className="space-y-3">
              <div>
                <h3 className="font-medium mb-1">File Uploads</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Upload images, PDFs, text files, and other documents to provide additional context for your conversations.
                  The AI can analyze and reference this content in its responses.
                </p>
              </div>
              <div>
                <h3 className="font-medium mb-1">Website Fetching</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Ask the personality to fetch a website, and it will retrieve the content to use as context in the conversation.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Generated Content & Media</h2>
            <p className="text-muted-foreground leading-relaxed mb-3">
              When the AI generates content (images, documents, etc.), it appears inline within your conversation.
              You can also access a dedicated media viewer from the top right corner of the thread view.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              The media viewer shows only the generated content without the messages, making it easier to find
              and review media from earlier in your conversation.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Memory & Persistence</h2>
            <p className="text-muted-foreground leading-relaxed">
              Personalities can remember information across conversations. Simply ask them to remember something
              by saying phrases like "remember this for later" or "please remember that I prefer..."
              The AI will store this information for future reference.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Voice Features</h2>
            <div className="space-y-3">
              <div>
                <h3 className="font-medium mb-1">Audio Recording</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Use the audio record function in the message form to record from your configured microphone.
                  The system will transcribe your speech and automatically send it as a message.
                </p>
              </div>
              <div>
                <h3 className="font-medium mb-1">Text-to-Speech</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Ask a personality to respond with text-to-speech (TTS) to have a voice conversation.
                  This enables basic spoken interactions with the AI.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Quick Actions & Shortcuts</h2>
            <div className="space-y-3">
              <div>
                <h3 className="font-medium mb-1">Prompt Menu</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Access predefined prompts for common tasks through the prompt menu, saving you time on frequently used commands.
                </p>
              </div>
              <div>
                <h3 className="font-medium mb-1">Clickable Prompts</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Light blue prompts that appear in messages are clickable and will automatically execute that prompt,
                  making it easy to follow suggested actions.
                </p>
              </div>
            </div>
          </section>

          <section>
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight mb-4">Tools & Capabilities</h2>
              <p className="text-muted-foreground text-base leading-relaxed max-w-3xl">
                Neuron personalities can be equipped with specialized toolsets to enhance their capabilities.
                Configure which tools are available when creating or editing a personality.
              </p>
            </div>

            <div className="space-y-8">
              <div className="bg-blue-50/50 dark:bg-blue-950/20 rounded-lg p-6 border border-blue-200/50 dark:border-blue-800/30">
                <h3 className="text-lg font-semibold mb-4 text-blue-900 dark:text-blue-100">Core Toolsets</h3>
                <p className="text-sm text-blue-700 dark:text-blue-300 mb-4">Default tools enabled for all personalities</p>
                <div className="space-y-4">
                  <div className="flex flex-col gap-1">
                    <span className="font-semibold text-blue-700 dark:text-blue-300">Image Generation & Analysis</span>
                    <p className="text-sm text-blue-600 dark:text-blue-400">Generate high-quality images using AI models like Flux and Recraft. Analyze and describe uploaded images with detailed descriptions.</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-semibold text-blue-700 dark:text-blue-300">Web Search</span>
                    <p className="text-sm text-blue-600 dark:text-blue-400">Advanced web search with filtering capabilities. Extract and analyze content from documents and websites.</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-semibold text-blue-700 dark:text-blue-300">Text-to-Speech</span>
                    <p className="text-sm text-blue-600 dark:text-blue-400">Convert text to natural-sounding speech with multiple voice options for enhanced conversations.</p>
                  </div>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-green-50/50 dark:bg-green-950/20 rounded-lg p-6 border border-green-200/50 dark:border-green-800/30">
                  <h3 className="text-lg font-semibold mb-3 text-green-900 dark:text-green-100">Media & Content Creation</h3>
                  <div className="space-y-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-green-700 dark:text-green-300">Audio & Music</span>
                      <p className="text-sm text-green-600 dark:text-green-400">Generate music and audio content. Professional TTS with 20+ character voices via ElevenLabs.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-green-700 dark:text-green-300">Video Processing</span>
                      <p className="text-sm text-green-600 dark:text-green-400">Create and edit videos using AI generation and FFmpeg processing tools.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-green-700 dark:text-green-300">GLaDOS Voice</span>
                      <p className="text-sm text-green-600 dark:text-green-400">Specialized Portal character voice synthesis generated locally using Isaac's hardware.</p>
                    </div>
                  </div>
                </div>

                <div className="bg-purple-50/50 dark:bg-purple-950/20 rounded-lg p-6 border border-purple-200/50 dark:border-purple-800/30">
                  <h3 className="text-lg font-semibold mb-3 text-purple-900 dark:text-purple-100">Technical & Scientific</h3>
                  <div className="space-y-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-purple-700 dark:text-purple-300">Code Interpreter</span>
                      <p className="text-sm text-purple-600 dark:text-purple-400">Execute Python code with scientific libraries. Data analysis, visualization, and computation.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-purple-700 dark:text-purple-300">Astronomy Tools</span>
                      <p className="text-sm text-purple-600 dark:text-purple-400">Astronomical calculations, sky observations, moon phases, and weather forecasting for stargazing.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-purple-700 dark:text-purple-300">Weather Forecasting</span>
                      <p className="text-sm text-purple-600 dark:text-purple-400">Current conditions and detailed forecasts for any location worldwide.</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-orange-50/50 dark:bg-orange-950/20 rounded-lg p-6 border border-orange-200/50 dark:border-orange-800/30">
                  <h3 className="text-lg font-semibold mb-3 text-orange-900 dark:text-orange-100">Knowledge & Research</h3>
                  <div className="space-y-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-orange-700 dark:text-orange-300">Knowledge Graph</span>
                      <p className="text-sm text-orange-600 dark:text-orange-400">Import and query research papers, documents, and semantic relationships.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-orange-700 dark:text-orange-300">Memory System</span>
                      <p className="text-sm text-orange-600 dark:text-orange-400">Store and recall information across conversations using semantic search.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-orange-700 dark:text-orange-300">Academic Research</span>
                      <p className="text-sm text-orange-600 dark:text-orange-400">Search ArXiv papers, generate summaries, and retrieve research publications.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-orange-700 dark:text-orange-300">Document Analysis</span>
                      <p className="text-sm text-orange-600 dark:text-orange-400">Analyze documents and images, extract content and metadata for examination.</p>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-50/50 dark:bg-slate-950/20 rounded-lg p-6 border border-slate-200/50 dark:border-slate-800/30">
                  <h3 className="text-lg font-semibold mb-3 text-slate-900 dark:text-slate-100">Utilities & Gaming</h3>
                  <div className="space-y-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">Notifications</span>
                      <p className="text-sm text-slate-600 dark:text-slate-400">Send system notifications and alerts to keep you informed of important events.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">Dice & Random</span>
                      <p className="text-sm text-slate-600 dark:text-slate-400">Random number generation and dice rolling for games and decision-making.</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">Helldivers 2 Data</span>
                      <p className="text-sm text-slate-600 dark:text-slate-400">Access Galactic War reports and liberation campaign history for HD2 players.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-border">
              <h3 className="text-lg font-semibold mb-4">Example Prompts</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div className="bg-muted/50 rounded-md p-3">
                    <p className="text-sm font-medium mb-1">Image Generation</p>
                    <p className="text-xs text-muted-foreground">"Create a cyberpunk cityscape at night with neon lights"</p>
                  </div>
                  <div className="bg-muted/50 rounded-md p-3">
                    <p className="text-sm font-medium mb-1">Data Analysis</p>
                    <p className="text-xs text-muted-foreground">"Analyze this CSV file and create a visualization of the trends"</p>
                  </div>
                  <div className="bg-muted/50 rounded-md p-3">
                    <p className="text-sm font-medium mb-1">Research</p>
                    <p className="text-xs text-muted-foreground">"Find recent papers on quantum computing and summarize the key findings"</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="bg-muted/50 rounded-md p-3">
                    <p className="text-sm font-medium mb-1">Astronomy</p>
                    <p className="text-xs text-muted-foreground">"When will Jupiter be visible tonight from San Francisco?"</p>
                  </div>
                  <div className="bg-muted/50 rounded-md p-3">
                    <p className="text-sm font-medium mb-1">Music Creation</p>
                    <p className="text-xs text-muted-foreground">"Generate a 30-second ambient background track for meditation"</p>
                  </div>
                  <div className="bg-muted/50 rounded-md p-3">
                    <p className="text-sm font-medium mb-1">Weather</p>
                    <p className="text-xs text-muted-foreground">"What's the weather forecast for hiking this weekend in Colorado?"</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                <strong>Configuration:</strong> Tools are configurable per personality during creation or editing.
                Generated content is automatically stored and accessible via the media viewer.
                Default toolsets include Image, Search, and TTS.
              </p>
            </div>
          </section>

          <section className="border-t pt-4">
            <p className="text-xs text-muted-foreground">
              Need more help? Try asking Neuron directly - it can provide guidance on using its features and capabilities.
            </p>
          </section>
        </div>
      </ScrollArea>
    </div>
  );
}
