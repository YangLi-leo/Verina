/**
 * React Hook for managing search state and API calls
 * This is the bridge between our API service and UI components
 */
import { useState, useCallback, useRef, useEffect } from "react";
import { SearchCandidate } from "@/types";
import { searchAPI } from "@/services/search-api";
import { logger } from "@/lib/logger";

/**
 * Hook state interface - all the data we need to track
 */
interface UseSearchAPIState {
  // Loading states
  isLoading: boolean; // Is search in progress?
  isTyping: boolean; // Is answer being "typed"?

  // Data
  query: string; // Current search query
  results: SearchCandidate[]; // Search results
  answer: string; // AI-generated answer
  displayedAnswer: string; // Answer shown with typing effect

  // Metadata
  complexity: string; // 'simple' or 'complex'
  searchId: string | null; // Unique search ID
  timestamp: string | null; // When search was performed

  // Error handling
  error: string | null; // Error message if any
}

/**
 * Custom Hook: useSearchAPI
 *
 * What it does:
 * 1. Manages all search-related state
 * 2. Handles API calls
 * 3. Provides typing animation for answers
 * 4. Handles errors and loading states
 *
 * How to use in a component:
 * ```tsx
 * const { search, isLoading, results, displayedAnswer } = useSearchAPI();
 * ```
 */
export function useSearchAPI() {
  // Ref for direct DOM manipulation to bypass React batching
  const answerDisplayRef = useRef<HTMLSpanElement>(null);

  // Ref to track if component is mounted (prevents memory leaks)
  const isMountedRef = useRef<boolean>(true);

  // Unique ID for this search instance (persistent across renders)
  const instanceIdRef = useRef<string>(`instance_${Date.now()}_${Math.random()}`);

  // State management - useState is React's way to store data
  const [state, setState] = useState<UseSearchAPIState>({
    isLoading: false,
    isTyping: false,
    query: "",
    results: [],
    answer: "",
    displayedAnswer: "",
    complexity: "simple",
    searchId: null,
    timestamp: null,
    error: null,
  });

  /**
   * Main search function - this is what components call
   *
   * @param query - The search query from user input
   * @param deepThinking - Enable deep thinking mode for complex queries
   */
  const search = useCallback(async (query: string, deepThinking: boolean = false) => {
    // Validation
    if (!query.trim()) {
      setState(prev => ({ ...prev, error: "Please enter a search query" }));
      return;
    }

    // Clear the display ref for new search
    if (answerDisplayRef.current) {
      answerDisplayRef.current.textContent = "";
    }

    // Reset state and start loading
    // Keep previous results until new ones arrive (don't clear results immediately)
    setState(prev => ({
      ...prev,
      isLoading: true,
      isTyping: true,
      error: null,
      query: query,
      answer: "",
      displayedAnswer: "",
      // Don't clear results here - keep old ones until new ones arrive
    }));

    // Accumulate chunks without triggering re-renders
    let accumulatedAnswer = "";

    try {
      // Use streaming API with instance ID
      await searchAPI.searchStream(
        query,
        {
          // Receive metadata (candidates, queries, etc.)
          onMetadata: data => {
            if (!isMountedRef.current) return; // Prevent state updates after unmount

            // Save current DOM content before setState (which triggers re-render)
            const currentContent = answerDisplayRef.current?.textContent || "";

            setState(prev => ({
              ...prev,
              results: data.candidates || [],
              searchId: data.search_id || null,
            }));

            // Restore DOM content after setState
            // Use setTimeout to wait for React to finish re-rendering
            setTimeout(() => {
              if (isMountedRef.current && answerDisplayRef.current && currentContent) {
                answerDisplayRef.current.textContent = currentContent;
              }
            }, 0);
          },

          // Receive answer chunks in real-time
          onChunk: content => {
            if (!isMountedRef.current) return; // Prevent DOM manipulation after unmount

            logger.log("[useSearchAPI] Received chunk:", content);
            logger.log("[useSearchAPI] answerDisplayRef.current:", answerDisplayRef.current);

            // Accumulate chunks
            accumulatedAnswer += content;

            // Direct DOM manipulation - completely bypass React's rendering
            if (answerDisplayRef.current) {
              answerDisplayRef.current.textContent += content;
              logger.log(
                "[useSearchAPI] Updated DOM, current content:",
                answerDisplayRef.current.textContent
              );
            } else {
              // answerDisplayRef not ready yet - chunks will be shown when onDone sets state
              logger.log("[useSearchAPI] answerDisplayRef not ready yet, will show in onDone");
            }

            // DON'T setState here - it causes re-render which clears DOM content!
          },

          // Streaming complete
          onDone: () => {
            if (!isMountedRef.current) return; // Prevent state updates after unmount

            // Now update state with final answer
            setState(prev => ({
              ...prev,
              isLoading: false,
              isTyping: false,
              answer: accumulatedAnswer,
              displayedAnswer: accumulatedAnswer,
            }));
          },

          // Handle errors
          onError: error => {
            if (!isMountedRef.current) return; // Prevent state updates after unmount

            // Search cancellation is expected behavior, not an error
            if (error === "Search was cancelled") {
              logger.log("[useSearchAPI] Previous search cancelled");
              // Don't set error state for cancellations
              setState(prev => ({
                ...prev,
                isLoading: false,
                isTyping: false,
              }));
            } else {
              logger.error("[useSearchAPI] Stream error:", error);
              setState(prev => ({
                ...prev,
                isLoading: false,
                isTyping: false,
                error: error || "Search failed. Please try again.",
              }));
            }
          },
        },
        deepThinking,
        instanceIdRef.current // Pass instance ID for independent execution
      );
    } catch (error: any) {
      if (!isMountedRef.current) return; // Prevent state updates after unmount

      logger.error("[useSearchAPI] Search error:", error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        isTyping: false,
        error: error.message || "Search failed. Please try again.",
      }));
    }
  }, []);

  /**
   * Cleanup effect - mark as unmounted and cancel requests when component unmounts
   */
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      // Cancel ongoing search when switching away
      searchAPI.cancelSearch(instanceIdRef.current);
      logger.log("[useSearchAPI] Cancelled search on unmount:", instanceIdRef.current);
    };
  }, []);

  /**
   * Clear search results and reset state
   */
  const clearSearch = useCallback(() => {
    // Cancel only this instance's request
    searchAPI.cancelSearch(instanceIdRef.current);

    // Clear the display ref
    if (answerDisplayRef.current) {
      answerDisplayRef.current.textContent = "";
    }

    // Reset all state
    setState({
      isLoading: false,
      isTyping: false,
      query: "",
      results: [],
      answer: "",
      displayedAnswer: "",
      complexity: "simple",
      searchId: null,
      timestamp: null,
      error: null,
    });
  }, []);

  /**
   * Cancel ongoing search
   */
  const cancelSearch = useCallback(() => {
    searchAPI.cancelSearch(instanceIdRef.current);
    setState(prev => ({
      ...prev,
      isLoading: false,
      isTyping: false,
    }));
  }, []);

  /**
   * Restore search results from saved record (for page refresh)
   */
  const restoreSearch = useCallback((record: any) => {
    setState(prev => ({
      ...prev,
      query: record.original_query || record.query || "",
      results: record.candidates || [],
      answer: record.answer || "",
      displayedAnswer: record.answer || "",
      searchId: record.search_id || null,
    }));
  }, []);

  // Return everything components need
  return {
    // State
    ...state,

    // Actions
    search,
    clearSearch,
    cancelSearch,
    restoreSearch,

    // Ref for direct DOM streaming display
    answerDisplayRef,

    // Computed values
    hasResults: state.results.length > 0,
    hasAnswer: state.displayedAnswer.length > 0,
  };
}

/**
 * Optional: Hook for search history
 */
export function useSearchHistory() {
  const [history, setHistory] = useState<
    Array<{
      search_id: string;
      query: string;
      timestamp: string;
    }>
  >([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await searchAPI.getHistory(20);
      setHistory(data);
    } catch (error) {
      logger.error("Failed to load history:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadSearchRecord = useCallback(async (searchId: string) => {
    try {
      const record = await searchAPI.getSearchRecord(searchId);
      return record;
    } catch (error) {
      logger.error("Failed to load search record:", error);
      return null;
    }
  }, []);

  return {
    history,
    isLoading,
    loadHistory,
    loadSearchRecord,
  };
}
