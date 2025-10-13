/**
 * Real API service for search functionality
 * Simple and direct connection to backend FastAPI server
 */

import { SearchAPIResponse } from "@/types";

/**
 * Configuration for API connection
 */
const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  endpoints: {
    search: "/api/v1/search",
    history: "/api/v1/search/history",
    record: "/api/v1/search/record",
  },
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
};

/**
 * Search API service class - Supports multiple concurrent searches
 */
export class SearchAPIService {
  private baseUrl: string;
  private controllers: Map<string, AbortController> = new Map();

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || API_CONFIG.baseUrl;
  }

  /**
   * Get user's search history
   *
   * @param limit - Maximum number of history items
   * @returns Array of search history records
   */
  async getHistory(limit: number = 20): Promise<
    Array<{
      search_id: string;
      query: string;
      timestamp: string;
    }>
  > {
    try {
      const response = await fetch(
        `${this.baseUrl}${API_CONFIG.endpoints.history}?limit=${limit}`,
        {
          headers: API_CONFIG.headers,
        }
      );

      if (!response.ok) {
        console.error(`Failed to get history: ${response.status}`);
        return [];
      }

      return await response.json();
    } catch (error) {
      console.error("[SearchAPI] History error:", error);
      return [];
    }
  }

  /**
   * Get a specific search record by ID
   *
   * @param searchId - The search ID to retrieve
   * @returns The search record or null if not found
   */
  async getSearchRecord(searchId: string): Promise<SearchAPIResponse | null> {
    try {
      const response = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.record}/${searchId}`, {
        headers: API_CONFIG.headers,
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error(`Failed to get record: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("[SearchAPI] Get record error:", error);
      return null;
    }
  }

  /**
   * Streaming search method - receives SSE events from backend
   * Each search runs independently using searchId
   *
   * @param query - User's search query
   * @param callbacks - Event handlers for different event types
   * @param deepThinking - Enable deep thinking mode for complex queries
   * @param searchId - Unique identifier for this search (auto-generated if not provided)
   */
  async searchStream(
    query: string,
    callbacks: {
      onMetadata: (data: any) => void;
      onChunk: (content: string) => void;
      onDone: () => void;
      onError: (error: string) => void;
    },
    deepThinking: boolean = false,
    searchId?: string
  ): Promise<void> {
    // Generate unique ID if not provided
    const sid = searchId || `search_${Date.now()}_${Math.random()}`;

    // Cancel previous request for THIS search only
    this.controllers.get(sid)?.abort();

    // Create new abort controller
    const controller = new AbortController();
    this.controllers.set(sid, controller);

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/search/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          query,
          deep_thinking: deepThinking,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Stream failed: ${response.status}`);
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

          // Check if this request was superseded
          if (this.controllers.get(sid) !== controller) {
            console.log(`[SearchAPI] Search ${sid} superseded`);
            return;
          }

          try {
            const jsonStr = line.substring(6);
            const event = JSON.parse(jsonStr);

            switch (event.type) {
              case "metadata":
                console.log("[SearchAPI] Received metadata event", event.data);
                callbacks.onMetadata(event.data);
                break;

              case "sources":
                console.log("[SearchAPI] Received sources event", event.data);
                // Sources event contains candidates and related_searches
                callbacks.onMetadata(event.data);
                break;

              case "chunk":
                console.log("[SearchAPI] Received chunk:", event.content.substring(0, 50));
                callbacks.onChunk(event.content);
                break;

              case "done":
                console.log("[SearchAPI] Stream done");
                callbacks.onDone();
                return;

              case "error":
                console.error("[SearchAPI] Stream error:", event.message);
                callbacks.onError(event.message);
                return;

              default:
                console.warn("[SearchAPI] Unknown event type:", event.type);
            }
          } catch (err) {
            console.error("[SearchAPI] Failed to parse SSE event:", err);
          }
        }
      }
    } catch (error: any) {
      // Only handle errors for the current request
      if (this.controllers.get(sid) !== controller) {
        console.log(`[SearchAPI] Ignoring error from superseded search ${sid}`);
        return;
      }

      if (error.name === "AbortError") {
        callbacks.onError("Search was cancelled");
      } else if (error instanceof TypeError && error.message.includes("fetch")) {
        callbacks.onError(
          "Cannot connect to backend server. Please check if it is running on port 8000."
        );
      } else {
        callbacks.onError(error.message || "Stream failed");
      }
    } finally {
      // Only clear if this is still the current controller
      if (this.controllers.get(sid) === controller) {
        this.controllers.delete(sid);
      }
    }
  }

  /**
   * Cancel specific search by ID
   */
  cancelSearch(searchId: string): void {
    const controller = this.controllers.get(searchId);
    if (controller) {
      controller.abort();
      this.controllers.delete(searchId);
    }
  }

  /**
   * Cancel all ongoing searches
   */
  cancelAll(): void {
    this.controllers.forEach(controller => controller.abort());
    this.controllers.clear();
  }

  /**
   * Legacy method - cancels all searches
   * @deprecated Use cancelAll() instead
   */
  cancelOngoingRequest(): void {
    this.cancelAll();
  }

  /**
   * Check if the API backend is available
   *
   * @returns True if backend is reachable
   */
  async isAvailable(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${this.baseUrl}/health`, {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Export singleton instance for convenience
export const searchAPI = new SearchAPIService();

// Also export class for testing or custom instances
export default SearchAPIService;
