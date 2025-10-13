/**
 * Chat API service for conversation functionality
 * Handles SSE streaming for real-time chat responses
 */

import type { ChatRequest, ChatResponse, ThinkingStep } from "@/types";

/**
 * Chat service callbacks for streaming events
 */
interface ChatStreamCallbacks {
  onSessionCreated?: (sessionId: string) => void; // New: When session is auto-generated
  onThinkingStep?: (step: ThinkingStep) => void;
  onStageSwitch?: (stage: string) => void; // Agent Mode stage changes (hil -> research)
  onChunk?: (chunk: string) => void;
  onComplete?: (response: ChatResponse) => void;
  onError?: (error: string) => void;
}

/**
 * Chat API service class - Handles chat SSE streaming
 */
export class ChatAPIService {
  private baseUrl: string;
  private abortController: AbortController | null = null;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }

  /**
   * Send a chat message with streaming response
   */
  async sendMessageStream(request: ChatRequest, callbacks: ChatStreamCallbacks): Promise<void> {
    // Cancel any previous request
    if (this.abortController) {
      this.abortController.abort();
    }

    // Create new abort controller for this request
    const controller = new AbortController();
    this.abortController = controller;

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Chat stream failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim() || !line.startsWith("data: ")) continue;

          // Check if this request was cancelled
          if (controller !== this.abortController) {
            console.log("[ChatAPI] Request superseded by newer request");
            return;
          }

          try {
            const jsonStr = line.substring(6);
            const event = JSON.parse(jsonStr);

            switch (event.type) {
              case "session_created":
                console.log("[ChatAPI] Session created:", event.session_id);
                if (callbacks.onSessionCreated) {
                  callbacks.onSessionCreated(event.session_id);
                }
                break;

              case "thinking_step":
                if (callbacks.onThinkingStep) {
                  callbacks.onThinkingStep(event.data);
                }
                break;

              case "stage_switch":
                console.log("[ChatAPI] Stage switch:", event.data?.stage);
                if (callbacks.onStageSwitch) {
                  callbacks.onStageSwitch(event.data?.stage || "unknown");
                }
                break;

              case "chunk":
                if (callbacks.onChunk) {
                  // Backend sends chunk data in "data" field, not "content"
                  callbacks.onChunk(event.data || event.content);
                }
                break;

              case "complete":
                if (callbacks.onComplete) {
                  callbacks.onComplete(event.data);
                }
                return;

              case "error":
                if (callbacks.onError) {
                  callbacks.onError(event.message);
                }
                return;

              default:
                console.warn("[ChatAPI] Unknown event type:", event.type);
            }
          } catch (err) {
            console.error("[ChatAPI] Failed to parse SSE event:", err);
          }
        }
      }
    } catch (error: any) {
      // Only handle errors for the current request
      if (controller !== this.abortController) {
        console.log("[ChatAPI] Ignoring error from superseded request");
        return;
      }

      if (error.name === "AbortError") {
        if (callbacks.onError) {
          callbacks.onError("Chat was cancelled");
        }
      } else if (error instanceof TypeError && error.message.includes("fetch")) {
        if (callbacks.onError) {
          callbacks.onError("Cannot connect to backend server. Please check if it is running.");
        }
      } else {
        if (callbacks.onError) {
          callbacks.onError(error.message || "Chat stream failed");
        }
      }
    } finally {
      // Only clear if this is still the current controller
      if (controller === this.abortController) {
        this.abortController = null;
      }
    }
  }

  /**
   * Cancel any ongoing chat request
   */
  cancelOngoingRequest(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }
}

// Export singleton instance
export const ChatService = new ChatAPIService();

// Export class for custom instances
export default ChatAPIService;
