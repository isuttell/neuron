import { SidebarTrigger } from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function Privacy() {
  return (
    <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex items-center justify-between mb-6 border-b pb-4 mobile-safe-top">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-lg lg:text-2xl font-bold">Privacy</h1>
        <div className="flex-1" />
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-6 max-w-2xl mx-auto">
          <section>
            <p className="text-muted-foreground leading-relaxed">
              Neuron is designed with privacy and data control in mind. This policy explains how your data is handled,
              stored, and shared within the system.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">System Administration</h2>
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <p className="text-blue-800 dark:text-blue-200 text-sm leading-relaxed">
                <strong>Please note:</strong> Neuron is Isaac's development project. As the system administrator,
                Isaac has full access to the infrastructure and data for maintenance, debugging, and development purposes.
                Do not share anything with Neuron that you are not comfortable with Isaac potentially seeing if he needs
                to work on or debug the system.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Where Your Data Lives</h2>
            <p className="text-muted-foreground leading-relaxed">
              Your data is stored locally in Isaac's homelab infrastructure, located in his garage.
              This includes your message history, personality configurations, thread conversations, and all generated content.
              The goal is to maintain control over your data rather than storing it with third-party services.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">How Data Sharing Works</h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium mb-2">Personalities</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  You own the personalities you create. You can choose to share them with other users,
                  giving them access to interact with your personality configurations.
                </p>
              </div>

              <div>
                <h3 className="font-medium mb-2">Conversations (Threads)</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Your conversations are private by default. You can invite specific users to individual
                  threads to share conversations and collaborate.
                </p>
              </div>

              <div>
                <h3 className="font-medium mb-2">Personality Memories</h3>
                <p className="text-muted-foreground text-sm leading-relaxed mb-3">
                  When you interact with a personality, it can form memories from your conversations.
                  These memories are shared among all users who have access to that personality.
                </p>
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                  <p className="text-amber-800 dark:text-amber-200 text-sm font-medium mb-1">Important to know:</p>
                  <p className="text-amber-700 dark:text-amber-300 text-sm">
                    If you ask a personality to remember something private, other users with access to that
                    personality may see that information. Consider personality memories as shared within the user group.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Cloud Service Usage</h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium">AI Model Interactions</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  When you interact with personalities, required data (messages, context, memories) is sent to remote
                  cloud AI providers using Isaac's personal API keys. Training has been disabled on these requests
                  where possible. The privacy policies of individual AI providers (OpenAI, Anthropic, Google, etc.)
                  apply to this data transmission.
                </p>
              </div>
              <div>
                <h3 className="font-medium">Tool Integrations</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Various tools connect to cloud services for image generation, text-to-speech, video creation,
                  web search, and other functions. When using these tools, necessary data is sent to the respective
                  service providers to complete your request. Results are then downloaded and stored permanently
                  in the local homelab. Each service provider's privacy policy applies to their specific usage.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Data Control Philosophy</h2>
            <p className="text-muted-foreground leading-relaxed">
              The goal of this project is to maintain control over as much user data as possible, only sending
              data to cloud services when absolutely required for functionality. We store results locally to
              minimize ongoing data sharing with external providers.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Future Plans</h2>
            <p className="text-muted-foreground leading-relaxed">
              The long-term goal is to run high-quality AI models and generation tools locally when it becomes
              more economically feasible. This would further reduce data sharing with external services and
              provide even greater control over your information.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Third-Party Services</h2>
            <p className="text-muted-foreground leading-relaxed">
              When your data is processed by external cloud providers, their respective privacy policies apply.
              This includes but is not limited to AI model providers, image generation services, and other
              integrated tools. We recommend reviewing the privacy policies of services you actively use.
            </p>
          </section>

          <section className="border-t pt-4">
            <p className="text-xs text-muted-foreground">
              This privacy policy reflects the current implementation and may be updated as the system evolves.
            </p>
          </section>
        </div>
      </ScrollArea>
    </div>
  );
}
