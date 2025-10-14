/**
 * useChat Hook - Manages chat state and interactions
 * Handles session management, message sending, and real-time streaming
 * Single-session mode: switching sessions cancels ongoing requests
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { ChatService } from "@/services/chat";
import type { ChatResponse, ChatRequest, ChatMessageUI } from "@/types";
import { logger } from "@/lib/logger";

interface UseChatReturn {
  // State
  messages: ChatMessageUI[];
  isLoading: boolean;
  error: string | null;
  sessionId: string | null;

  // Actions
  sendMessage: (content: string, mode?: "chat" | "agent") => Promise<void>;
  stopGeneration: () => void; // Stop ongoing generation
  clearMessages: () => void;
  startNewChat: () => void; // New: Start a fresh chat session

  // Metadata
  lastResponse: ChatResponse | null;
  currentPromptTokens: number; // Real-time prompt tokens (updates during thinking steps)

  // Timer (for Agent Mode research phase)
  isResearchMode: boolean; // True when in Agent Mode research phase
  researchElapsedSeconds: number; // Elapsed time in seconds since research started

  // Agent Mode HIL stage indicator
  isHILMode: boolean; // True when in Agent Mode HIL (Human-in-Loop) planning stage
}

/**
 * Custom hook for chat functionality
 *
 * @param initialSessionId - Optional search_id from URL to use as session_id
 */
export function useChat(initialSessionId?: string | null): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessageUI[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId || null);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [currentPromptTokens, setCurrentPromptTokens] = useState<number>(0);

  // Ref to track if component is mounted (prevents memory leaks)
  const isMountedRef = useRef<boolean>(true);

  // Ref to track which session is currently sending a message
  const sendingSessionRef = useRef<string | null>(null);

  // Timer state for Agent Mode research phase
  const [isResearchMode, setIsResearchMode] = useState(false);
  const [researchStartTime, setResearchStartTime] = useState<number | null>(null);
  const [researchElapsedSeconds, setResearchElapsedSeconds] = useState(0);

  // Agent Mode HIL (Human-in-Loop) planning stage
  const [isHILMode, setIsHILMode] = useState(false);

  /**
   * Timer effect - Update elapsed seconds every second when in research mode
   */
  useEffect(() => {
    if (!isResearchMode || !researchStartTime) {
      return;
    }

    const intervalId = setInterval(() => {
      const elapsed = Math.floor((Date.now() - researchStartTime) / 1000);
      setResearchElapsedSeconds(elapsed);
    }, 1000);

    return () => clearInterval(intervalId);
  }, [isResearchMode, researchStartTime]);

  /**
   * Load session ID from initialSessionId (URL parameter only)
   * No localStorage fallback - complete decoupling between search and chat
   *
   * NOTE: When switching sessions, current ongoing request will be cancelled
   * This prevents message mixing between different sessions
   */
  useEffect(() => {
    if (initialSessionId) {
      // Cancel previous session's ongoing request if switching sessions
      if (sessionId && sessionId !== initialSessionId) {
        logger.log("[useChat] Cancelling previous session before switching:", sessionId);
        ChatService.cancelOngoingRequest();
      }

      // Use session_id from URL
      logger.log("[useChat] Setting sessionId from URL:", initialSessionId);
      setSessionId(initialSessionId);
      // Reset loading state when switching sessions
      setIsLoading(false);
      setError(null);
    } else {
      // Cancel ongoing request if any
      if (sessionId) {
        logger.log("[useChat] Cancelling session before clearing:", sessionId);
        ChatService.cancelOngoingRequest();
      }

      // No session_id in URL = start fresh (don't load from localStorage)
      logger.log("[useChat] No sessionId in URL, starting fresh");
      setSessionId(null);
      setMessages([]); // Clear messages when no session
      setIsLoading(false);
      setError(null);
    }
  }, [initialSessionId]);

  /**
   * Load conversation history when sessionId changes (page refresh)
   * Restores complete ChatResponse objects with thinking_steps and artifact
   */
  useEffect(() => {
    const loadHistory = async () => {
      if (!sessionId) {
        logger.log("[useChat] Skipping history load: no sessionId");
        return;
      }

      // Skip loading if this session is currently sending a message
      if (sendingSessionRef.current === sessionId) {
        logger.log(
          "[useChat] Skipping history load: message currently being sent for this session"
        );
        return;
      }

      try {
        logger.log("[useChat] Loading history for session:", sessionId);
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${baseUrl}/api/v1/chat/session/${sessionId}`);

        if (response.ok) {
          const data = await response.json();
          logger.log("[useChat] History API response:", data);

          // New format: responses array with complete ChatResponse objects
          if (data.responses && data.responses.length > 0) {
            const chatMessages: ChatMessageUI[] = [];

            // Each response contains one user+assistant exchange
            data.responses.forEach((chatResponse: any, idx: number) => {
              // Add user message
              chatMessages.push({
                id: `user-${idx}`,
                type: "user",
                content: chatResponse.user_message,
                timestamp: new Date(chatResponse.timestamp),
              });

              // Add assistant message with complete metadata
              chatMessages.push({
                id: `assistant-${idx}`,
                type: "assistant",
                content: chatResponse.assistant_message,
                timestamp: new Date(chatResponse.timestamp),
                thinking_steps: chatResponse.thinking_steps,
                sources: chatResponse.sources,
                used_tools: chatResponse.used_tools,
                has_code: chatResponse.has_code,
                has_web_results: chatResponse.has_web_results,
                artifact: chatResponse.artifact,
              });
            });

            setMessages(chatMessages);
            logger.log(
              `[useChat] ✅ Restored ${chatMessages.length} messages (${data.responses.length} exchanges) for session ${sessionId}`
            );
          } else {
            // No history yet - this is normal for new sessions
            logger.log("[useChat] No history found yet (new session)");
            // Don't clear messages - they might be currently being sent
          }
        } else if (response.status === 404) {
          // 404 is normal - session doesn't exist in backend yet or message still processing
          logger.log("[useChat] Session not found (404) - normal for new sessions");
          // Don't clear messages - they might be currently being sent
        } else {
          // Other errors
          logger.warn("[useChat] History API returned unexpected status:", response.status);
          // Don't clear messages to avoid losing user's current conversation
        }
      } catch (error) {
        logger.warn("[useChat] Could not load history:", error);
        // Don't clear messages to avoid losing user's current conversation
      }
    };

    loadHistory();
  }, [sessionId]);

  /**
   * Note: We no longer save session ID to localStorage
   * Session persistence is handled entirely through URL parameters
   * This ensures complete decoupling between search and chat
   */

  /**
   * Send a chat message with real-time streaming (thinking steps + answer)
   */
  const sendMessage = useCallback(
    async (content: string, mode: "chat" | "agent" = "chat") => {
      if (!content.trim() || isLoading) return;

      const trimmedContent = content.trim();
      setError(null);
      setIsLoading(true);

      // Start HIL mode if Agent Mode
      if (mode === "agent") {
        setIsHILMode(true);
        logger.log("[useChat] Starting HIL planning stage");
      }

      // Mark this session as currently sending
      const sendingSessionId = sessionId || `temp_${Date.now()}`;
      sendingSessionRef.current = sendingSessionId;
      logger.log("[useChat] Marked session as sending:", sendingSessionId);

      // Add user message immediately
      const userMessage: ChatMessageUI = {
        id: `user-${Date.now()}`,
        type: "user",
        content: trimmedContent,
        timestamp: new Date(),
        isAnimating: true,
      };

      setMessages(prev => [...prev, userMessage]);

      // Remove animation after delay
      setTimeout(() => {
        setMessages(prev =>
          prev.map(msg => (msg.id === userMessage.id ? { ...msg, isAnimating: false } : msg))
        );
      }, 250);

      // Create assistant message placeholder
      const assistantId = `assistant-${Date.now()}`;
      const assistantMessage: ChatMessageUI = {
        id: assistantId,
        type: "assistant",
        content: "",
        timestamp: new Date(),
        thinking_steps: undefined,
        used_tools: false,
        has_code: false,
        has_web_results: false,
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Real-time streaming variables
      let accumulatedSteps: any[] = [];
      let accumulatedText = "";
      let currentSessionId = sessionId;

      try {
        // Prepare request
        const request: ChatRequest = {
          message: trimmedContent,
          session_id: sessionId || undefined,
          mode: mode, // Include mode parameter
        };

        // Stream events from backend using single-session service
        await ChatService.sendMessageStream(request, {
          // Session created (for new conversations)
          onSessionCreated: newSessionId => {
            if (!isMountedRef.current) return;
            logger.log("[useChat] New session created:", newSessionId);
            currentSessionId = newSessionId;
            setSessionId(newSessionId);

            // Update sending session ref to the real session ID
            sendingSessionRef.current = newSessionId;
            logger.log("[useChat] Updated sending session ref to real ID:", newSessionId);
          },

          // Stage switch (Agent Mode: hil -> research)
          onStageSwitch: stage => {
            if (!isMountedRef.current) return;
            logger.log("[useChat] Stage switch:", stage);
            if (stage === "research") {
              // Exit HIL mode, enter Research mode
              setIsHILMode(false);
              setIsResearchMode(true);
              setResearchStartTime(Date.now());
              setResearchElapsedSeconds(0);
            }
          },

          // Real-time thinking step updates
          onThinkingStep: step => {
            if (!isMountedRef.current) return;
            accumulatedSteps.push(step);

            // Update assistant message with latest thinking steps
            setMessages(prev =>
              prev.map(msg =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      thinking_steps: accumulatedSteps,
                      used_tools: true,
                    }
                  : msg
              )
            );
          },

          // Real-time text chunks (typing effect)
          onChunk: chunk => {
            if (!isMountedRef.current) return;
            accumulatedText += chunk;

            // Update content in real-time
            setMessages(prev =>
              prev.map(msg => (msg.id === assistantId ? { ...msg, content: accumulatedText } : msg))
            );
          },

          // Final complete response
          onComplete: response => {
            if (!isMountedRef.current) return;
            // Update session ID if new conversation
            if (!currentSessionId && response.session_id) {
              currentSessionId = response.session_id;
              setSessionId(response.session_id);
            }

            // Store complete response
            setLastResponse(response);

            // Update current prompt tokens
            if (response.prompt_tokens) {
              setCurrentPromptTokens(response.prompt_tokens);
            }

            // Stop timer and clear stages when response completes
            setIsHILMode(false);
            setIsResearchMode(false);
            setResearchStartTime(null);

            // Final update with all metadata
            setMessages(prev =>
              prev.map(msg =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content: response.assistant_message,
                      thinking_steps: response.thinking_steps || undefined,
                      sources: response.sources || undefined,
                      used_tools: response.used_tools,
                      has_code: response.has_code,
                      has_web_results: response.has_web_results,
                      artifact: response.artifact || undefined,
                      timestamp: new Date(response.timestamp),
                    }
                  : msg
              )
            );

            setIsLoading(false);

            // Clear sending session marker
            if (sendingSessionRef.current === sendingSessionId) {
              sendingSessionRef.current = null;
              logger.log("[useChat] Cleared sending session marker");
            }
          },

          // Error handling
          onError: errorMsg => {
            if (!isMountedRef.current) return;

            // User cancellation is not an error - handle silently
            if (errorMsg === "Chat was cancelled") {
              logger.log("Chat generation cancelled by user");
              setIsLoading(false);

              // Stop timer and clear stages
              setIsHILMode(false);
              setIsResearchMode(false);
              setResearchStartTime(null);

              // Clear sending session marker
              if (sendingSessionRef.current === sendingSessionId) {
                sendingSessionRef.current = null;
                logger.log("[useChat] Cleared sending session marker (cancelled)");
              }
              return;
            }

            // Real errors - log and show to user
            logger.error("Stream error:", errorMsg);
            setError(errorMsg);

            // Update message with error
            setMessages(prev =>
              prev.map(msg =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content:
                        "Sorry, I encountered an error processing your message. Please try again.",
                    }
                  : msg
              )
            );

            setIsLoading(false);

            // Clear sending session marker
            if (sendingSessionRef.current === sendingSessionId) {
              sendingSessionRef.current = null;
              logger.log("[useChat] Cleared sending session marker (error)");
            }
          },
        });
      } catch (err) {
        if (!isMountedRef.current) return;

        logger.error("Send message error:", err);
        setError(err instanceof Error ? err.message : "Failed to send message");

        // Add error message
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content:
                    "Sorry, I encountered an error processing your message. Please try again.",
                }
              : msg
          )
        );

        setIsLoading(false);

        // Stop timer and clear stages
        setIsHILMode(false);
        setIsResearchMode(false);
        setResearchStartTime(null);

        // Clear sending session marker
        if (sendingSessionRef.current === sendingSessionId) {
          sendingSessionRef.current = null;
          logger.log("[useChat] Cleared sending session marker (exception)");
        }
      }
    },
    [sessionId, isLoading]
  );

  /**
   * Cleanup effect - mark as unmounted when component unmounts
   */
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  /**
   * Clear all messages and reset session
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setLastResponse(null);
    setError(null);
  }, []);

  /**
   * Stop ongoing generation for this session only
   */
  const stopGeneration = useCallback(() => {
    if (sessionId) {
      logger.log(`[useChat] Stopping generation for session: ${sessionId}`);
      ChatService.cancelOngoingRequest();
      setIsLoading(false);

      // Stop timer and clear all stage indicators
      setIsHILMode(false);
      setIsResearchMode(false);
      setResearchStartTime(null);
      setResearchElapsedSeconds(0);
      logger.log("[useChat] Cleared HIL/Research states and timer");

      // Clear sending session marker
      if (sendingSessionRef.current === sessionId) {
        sendingSessionRef.current = null;
        logger.log("[useChat] Cleared sending session marker (stopped)");
      }
    }
  }, [sessionId]);

  /**
   * Start a new chat session (clear current and reset sessionId)
   */
  const startNewChat = useCallback(() => {
    logger.log("[useChat] Starting new chat session");
    setMessages([]);
    setSessionId(null);
    setLastResponse(null);
    setError(null);
    setIsLoading(false); // Reset loading state
    setCurrentPromptTokens(0); // Clear token count
    setIsHILMode(false); // Stop HIL mode
    setIsResearchMode(false); // Stop research mode
    setResearchStartTime(null); // Clear research timer
    setResearchElapsedSeconds(0); // Reset elapsed time
  }, []);

  return {
    messages,
    isLoading,
    error,
    sessionId,
    sendMessage,
    stopGeneration,
    clearMessages,
    startNewChat,
    lastResponse,
    currentPromptTokens,
    isResearchMode,
    researchElapsedSeconds,
    isHILMode,
  };
}

export default useChat;
