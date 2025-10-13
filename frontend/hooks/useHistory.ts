import { useState, useEffect, useCallback } from "react";
import type { HistoryItem } from "@/types";
import { logger } from "@/lib/logger";

interface UseHistoryReturn {
  searchHistory: HistoryItem[];
  chatHistory: HistoryItem[];
  loading: boolean;
  error: string | null;
  refreshHistory: () => Promise<void>;
  clearHistory: () => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Hook for managing search and chat history from backend
 */
export function useHistory(): UseHistoryReturn {
  const [searchHistory, setSearchHistory] = useState<HistoryItem[]>([]);
  const [chatHistory, setChatHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch search history from backend
   */
  const fetchSearchHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/search/history?limit=20`);
      if (!response.ok) {
        // If auth required or error, fallback to empty array
        logger.warn("[useHistory] Failed to fetch search history:", response.status);
        return [];
      }
      const data = await response.json();

      // Transform backend data to HistoryItem format
      // Note: backend returns 'query' field (from original_query)
      return (data || []).map((item: any) => ({
        id: item.search_id,
        query: item.query || item.original_query, // Backend returns 'query' field
        display_name: item.display_name || null,
        timestamp: formatTimestamp(item.timestamp),
      }));
    } catch (err) {
      logger.error("[useHistory] Error fetching search history:", err);
      return [];
    }
  }, []);

  /**
   * Fetch chat history from backend
   */
  const fetchChatHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/chat/history?limit=20`);
      if (!response.ok) {
        logger.warn("[useHistory] Failed to fetch chat history:", response.status);
        return [];
      }
      const data = await response.json();

      // Transform backend session data to HistoryItem format
      // Note: backend returns 'first_message' and 'updated_at'
      return ((data.sessions || []) as any[]).map((session: any) => ({
        id: session.session_id,
        query: session.first_message || "Chat session",
        display_name: session.display_name || null, // LLM-generated title
        timestamp: formatTimestamp(session.updated_at || session.created_at),
      }));
    } catch (err) {
      logger.error("[useHistory] Error fetching chat history:", err);
      return [];
    }
  }, []);

  /**
   * Refresh history from backend
   */
  const refreshHistory = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [searchData, chatData] = await Promise.all([fetchSearchHistory(), fetchChatHistory()]);

      setSearchHistory(searchData);
      setChatHistory(chatData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [fetchSearchHistory, fetchChatHistory]);

  /**
   * Load history on mount (only once)
   */
  useEffect(() => {
    refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Clear history (client-side only - doesn't delete from backend)
   */
  const clearHistory = useCallback(() => {
    setSearchHistory([]);
    setChatHistory([]);
  }, []);

  return {
    searchHistory,
    chatHistory,
    loading,
    error,
    refreshHistory,
    clearHistory,
  };
}

/**
 * Format timestamp to relative time (e.g., "2 hours ago")
 * Handles both UTC and local timestamps correctly
 */
function formatTimestamp(timestamp: string | Date): string {
  // Parse the timestamp - if it's a string, ensure it's treated as UTC if it has 'Z' or '+00:00'
  let date: Date;
  if (typeof timestamp === "string") {
    // If timestamp doesn't have timezone info, assume it's already in local time
    date = new Date(timestamp);
  } else {
    date = timestamp;
  }

  const now = new Date();

  logger.log("[formatTimestamp] Original timestamp:", timestamp);
  logger.log("[formatTimestamp] Parsed date:", date.toISOString());
  logger.log("[formatTimestamp] Current time:", now.toISOString());

  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);

  logger.log("[formatTimestamp] Time difference (hours):", diffHours);

  if (diffSeconds < 60) {
    return "Just now";
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  } else if (diffDays < 7) {
    return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
  } else if (diffWeeks < 4) {
    return `${diffWeeks} week${diffWeeks === 1 ? "" : "s"} ago`;
  } else {
    return date.toLocaleDateString();
  }
}
