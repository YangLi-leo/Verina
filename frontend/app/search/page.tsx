"use client";
import type React from "react";
import { HistorySidebar } from "@/components/history-sidebar";
import { SearchHeader } from "@/components/search-header";
import { ChatInterface } from "@/components/chat-interface";
import { AnimatedMount } from "@/components/animated-mount";
import MainSearchResults from "@/components/main-search-results";
import RecommendSection from "@/components/recommend-section";
import { useSearchAPI } from "@/hooks/useSearchAPI";
import { searchAPI } from "@/services/search-api";
import { useChat } from "@/hooks/useChat";
import { useHistory } from "@/hooks/useHistory";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { getRandomKeyword } from "@/lib/constants/loading-keywords";
import { logger } from "@/lib/logger";

/**
 * Search page component that displays search results with sources and Q&A sections
 * Features a responsive layout with fixed header and scrollable content areas
 */
export default function SearchPage() {
  // Handle URL params properly for client component
  const [query, setQuery] = useState("");
  const [hasValidQuery, setHasValidQuery] = useState(false);
  const router = useRouter();
  const urlParams = useSearchParams(); // Client-side URL params for reactive updates

  // All state declarations - must be before effects that use them
  const [isChatMode, setIsChatMode] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [isHistorySidebarOpen, setIsHistorySidebarOpen] = useState(false);
  const [deepThinking, setDeepThinking] = useState(false);
  const [isAgentMode, setIsAgentMode] = useState(false); // false = Chat (default), true = Agent

  // Ref to prevent automatic mode switching when user manually toggles
  const preventAutoSwitch = useRef(false);

  // Use search hook (old version - no multi-session support)
  const {
    search: originalSearch,
    restoreSearch,
    isLoading,
    isTyping,
    results,
    displayedAnswer,
    searchId, // For URL persistence
    error,
    answerDisplayRef, // Get ref for direct DOM streaming
  } = useSearchAPI();

  // Wrap search to update hasValidQuery
  const search = useCallback(
    (query: string, deepThinking: boolean = false) => {
      if (query.trim()) {
        setHasValidQuery(true);
        setQuery(query);
      }
      return originalSearch(query, deepThinking);
    },
    [originalSearch]
  );

  // Load history from backend
  const { searchHistory, chatHistory } = useHistory();

  // Extract session_id from URL for chat
  // Use urlParams directly to ensure reactivity to URL changes
  const chatSessionId = urlParams.get("session_id");

  // Use the real chat hook with session_id from URL
  const {
    messages: chatMessages,
    isLoading: isChatLoading,
    error: chatError,
    sendMessage: sendChatMessage,
    stopGeneration,
    startNewChat,
    sessionId: currentSessionId,
    currentPromptTokens,
    isResearchMode,
    researchElapsedSeconds,
  } = useChat(chatSessionId);

  // Chat typing state (derived from isLoading)
  const isChatTyping = isChatLoading;

  // Loading indicator control: show animation when loading OR when we have a query but no results yet
  const isWaitingForAnswer =
    isLoading || (hasValidQuery && !results.length && !displayedAnswer && !error);

  // Extract URL params as individual values for stable dependencies
  const urlQuery = urlParams.get("q")?.trim() || "";
  const urlDeep = urlParams.get("deep") === "true";
  const urlSearchId = urlParams.get("search_id") || "";
  const urlSessionId = urlParams.get("session_id") || "";
  const urlChatMode = urlParams.get("chat") === "true";

  // Initialize query from URL params and restore search results if search_id exists
  // This effect runs when URL params change (e.g., from homepage search or history click)
  useEffect(() => {
    let isCancelled = false;

    const initializeParams = async () => {
      logger.log("[SearchPage] URL params:", {
        q: urlQuery,
        deep: urlDeep,
        searchId: urlSearchId,
        sessionId: urlSessionId,
        chatMode: urlChatMode,
      });

      setQuery(urlQuery);
      setDeepThinking(urlDeep);
      setHasValidQuery(urlQuery.length > 0);

      // If session_id exists or chat=true, switch to Chat mode
      if (urlSessionId || urlChatMode) {
        logger.log("[SearchPage] Switching to Chat mode");
        setTimeout(() => !isCancelled && setIsChatMode(true), 100);
      }

      // Case 1: Restore from history or page refresh (has search_id)
      if (urlSearchId) {
        try {
          logger.log("[SearchPage] Restoring search from ID:", urlSearchId);
          const record = await searchAPI.getSearchRecord(urlSearchId);

          if (isCancelled) return;

          if (record) {
            // Restore search results from backend
            restoreSearch(record);
            logger.log("[SearchPage] Successfully restored search results");
          } else {
            logger.warn("[SearchPage] No record found for ID:", urlSearchId);
            // If restore fails but we have a query, trigger new search
            if (urlQuery) {
              logger.log("[SearchPage] Triggering new search as fallback");
              search(urlQuery, urlDeep);
            }
          }
        } catch (error) {
          if (isCancelled) return;

          logger.error("[SearchPage] Failed to restore search results:", error);
          // Fallback to new search if restore fails
          if (urlQuery) {
            logger.log("[SearchPage] Triggering new search after restore error");
            search(urlQuery, urlDeep);
          }
        }
      } else if (urlQuery) {
        // Case 2: New search from homepage - trigger search automatically
        logger.log("[SearchPage] New search triggered from homepage:", urlQuery);
        search(urlQuery, urlDeep);
      }
    };

    initializeParams();

    // Cleanup function to prevent state updates after unmount
    return () => {
      isCancelled = true;
    };
  }, [urlQuery, urlDeep, urlSearchId, urlSessionId, urlChatMode, search, restoreSearch]); // Proper dependencies - runs when URL params change

  // Update URL with search_id when search completes
  useEffect(() => {
    if (searchId && query && !isLoading) {
      const url = new URL(window.location.href);
      url.searchParams.set("search_id", searchId);
      window.history.replaceState({}, "", url.toString());
      logger.log("[SearchPage] Added search_id to URL:", searchId);
    }
  }, [searchId, query, isLoading]);

  // Switch to chat mode when session_id in URL changes (e.g., from history sidebar)
  // Note: urlSessionId is already defined above from urlParams
  useEffect(() => {
    // Don't auto-switch if user just manually toggled
    if (preventAutoSwitch.current) {
      logger.log("[SearchPage] Skipping auto-switch due to manual toggle");
      return;
    }

    if (urlSessionId && !isChatMode) {
      logger.log("[SearchPage] Switching to chat mode due to session_id in URL");
      setTimeout(() => setIsChatMode(true), 100);
    }
  }, [urlSessionId, isChatMode]);

  // Update URL with session_id only when creating a NEW chat (no existing session_id in URL)
  useEffect(() => {
    // Only update URL if:
    // 1. We have a currentSessionId from useChat
    // 2. There's NO session_id in the URL yet (new chat created)
    // 3. currentSessionId is different from what's in URL
    if (currentSessionId && !chatSessionId && currentSessionId !== chatSessionId) {
      const url = new URL(window.location.href);
      url.searchParams.set("session_id", currentSessionId);
      window.history.replaceState({}, "", url.toString());
      logger.log("[SearchPage] Added new session_id to URL:", currentSessionId);
    }
  }, [currentSessionId, chatSessionId]);

  // Rotating loading keywords (random every 5–7s)
  const [currentKeyword, setCurrentKeyword] = useState<string>("");
  const keywordTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const schedule = () => {
      const delay = 5000 + Math.floor(Math.random() * 2000); // 5–7s
      keywordTimerRef.current = window.setTimeout(() => {
        setCurrentKeyword(getRandomKeyword());
        schedule();
      }, delay);
    };
    if (isWaitingForAnswer) {
      setCurrentKeyword(getRandomKeyword());
      schedule();
    } else {
      setCurrentKeyword("");
    }
    return () => {
      if (keywordTimerRef.current) {
        clearTimeout(keywordTimerRef.current);
        keywordTimerRef.current = null;
      }
    };
  }, [isWaitingForAnswer]);

  const handleChatToggle = () => {
    if (isAnimating) return;

    setIsAnimating(true);

    // Mark as manual toggle to prevent automatic mode switching
    preventAutoSwitch.current = true;
    logger.log("[SearchPage] Manual toggle detected, preventing auto-switch");

    // If switching from chat to search mode, clear session_id from URL
    if (isChatMode) {
      const url = new URL(window.location.href);
      url.searchParams.delete("session_id");
      url.searchParams.delete("chat");
      // Keep search_id and q if they exist
      window.history.pushState({}, "", url.toString());
      logger.log("[SearchPage] Cleared session_id from URL when switching to search mode");
    }

    setTimeout(() => {
      setIsChatMode(!isChatMode);

      setTimeout(() => {
        setIsAnimating(false);
        // Reset the flag after animation completes
        setTimeout(() => {
          preventAutoSwitch.current = false;
          logger.log("[SearchPage] Re-enabled auto-switch");
        }, 200);
      }, 350);
    }, 50);
  };

  const toggleHistorySidebar = () => {
    setIsHistorySidebarOpen(prev => !prev);
  };

  const handleSearchHistoryClick = async (clickedSearchId: string) => {
    // Stop ongoing search if any
    if (isLoading) {
      logger.log("[SearchPage] Stopping ongoing search before switching");
      // Cancel current search (useSearchAPI will handle this via instanceId)
    }

    // Load the search record directly (don't rely on URL change effect)
    try {
      logger.log("[SearchPage] Loading search from history click:", clickedSearchId);
      const record = await searchAPI.getSearchRecord(clickedSearchId);

      if (record) {
        // Restore the search results
        restoreSearch(record);
        const queryText = (record as any).original_query || (record as any).query || "";
        setQuery(queryText);
        setHasValidQuery(queryText.length > 0);

        // Update URL (this won't trigger Effect 1 because searchId will already match)
        const url = new URL(window.location.href);
        url.searchParams.set("search_id", clickedSearchId);
        url.searchParams.set("q", queryText);
        // Keep session_id if exists
        const currentSessionId = urlParams.get("session_id");
        if (currentSessionId) {
          url.searchParams.set("session_id", currentSessionId);
        }
        window.history.pushState({}, "", url.toString());

        logger.log("[SearchPage] ✅ Loaded search from history");
      }
    } catch (error) {
      logger.error("[SearchPage] Failed to load search from history:", error);
    }

    setIsHistorySidebarOpen(false);
  };

  const handleChatHistoryClick = (chatId: string) => {
    // Stop ongoing chat if any
    if (isChatLoading) {
      logger.log("[SearchPage] Stopping ongoing chat before switching to chat:", chatId);
      stopGeneration(); // Stop current chat session
    }

    // Build URL preserving current search_id if exists
    const url = new URL(window.location.href);
    url.searchParams.set("session_id", chatId);
    // Keep search_id if exists
    const currentSearchId = urlParams.get("search_id");
    if (currentSearchId && currentSearchId !== "default") {
      url.searchParams.set("search_id", currentSearchId);
    }
    // Keep query if exists
    const currentQuery = urlParams.get("q");
    if (currentQuery) {
      url.searchParams.set("q", currentQuery);
    }

    router.push(url.pathname + url.search);
    setIsHistorySidebarOpen(false);
    // Switch to chat mode
    setTimeout(() => setIsChatMode(true), 100);
  };

  // Removed click-outside handler - sidebar now pushes content instead of overlaying

  // Chat message handler
  const handleSendMessage = async () => {
    if (!chatInput.trim() || isChatLoading) return;
    const message = chatInput.trim();
    setChatInput("");
    await sendChatMessage(message, isAgentMode ? "agent" : "chat");
  };

  // New chat handler - clear chat session but preserve search state
  const handleNewChat = () => {
    startNewChat();

    // Build URL preserving search_id and q, but removing session_id
    const url = new URL(window.location.href);
    url.searchParams.delete("session_id");
    url.searchParams.delete("chat");
    // Keep search_id and q if they exist
    const searchIdParam = urlParams.get("search_id");
    const queryParam = urlParams.get("q");

    if (!searchIdParam && !queryParam) {
      // If no search state, just go to clean /search
      router.push("/search");
    } else {
      // Preserve search state
      router.push(url.pathname + url.search);
    }
  };

  return (
    <div className="h-screen w-full overflow-hidden bg-white font-mono text-black">
      <HistorySidebar
        isOpen={isHistorySidebarOpen}
        onClose={toggleHistorySidebar}
        searchHistory={searchHistory}
        chatHistory={chatHistory}
        onSearchClick={handleSearchHistoryClick}
        onChatClick={handleChatHistoryClick}
      />

      <div
        className={`ease-[cubic-bezier(0.32,0.72,0,1)] flex h-full flex-col transition-all duration-300 ${
          isHistorySidebarOpen ? "ml-80 w-[calc(100%-320px)]" : "ml-0 w-full"
        }`}
      >
        <SearchHeader
          query={query}
          setQuery={setQuery}
          onSearch={search}
          isLoading={isLoading}
          isWaitingForAnswer={isWaitingForAnswer}
          currentKeyword={currentKeyword}
          deepThinking={deepThinking}
          setDeepThinking={setDeepThinking}
          onChatToggle={handleChatToggle}
          onHistoryToggle={toggleHistorySidebar}
          isAnimating={isAnimating}
        />

        <main className="flex-1 overflow-hidden" role="main">
          <div className="relative h-full w-full">
            {!isChatMode ? (
              <div className="flex h-full max-w-[1600px] gap-6 px-6 lg:ml-[176px]">
                {/* Left Column - AI Answer (独立滚动) */}
                <section
                  className={`duration-[350ms] scrollbar-hide h-full overflow-y-auto overflow-x-hidden pb-6 pt-10 transition-all ease-in-out lg:w-[600px] lg:flex-shrink-0 ${
                    isAnimating
                      ? "-translate-x-full transform opacity-0"
                      : "translate-x-0 transform opacity-100"
                  }`}
                  aria-label="AI answers"
                >
                  {hasValidQuery ? (
                    <AnimatedMount>
                      <MainSearchResults
                        isLoading={isLoading}
                        isTyping={isTyping}
                        displayedAnswer={displayedAnswer}
                        sources={results}
                        error={error}
                        answerDisplayRef={answerDisplayRef}
                      />
                    </AnimatedMount>
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <div className="px-6 text-center">
                        <div className="mb-4 text-4xl">🌊</div>
                        <h3 className="mb-2 text-lg font-medium text-gray-900">
                          Dive into some search?
                        </h3>
                        <p className="text-sm text-gray-500">
                          Your AI-powered answers will appear here
                        </p>
                      </div>
                    </div>
                  )}
                </section>
                <div
                  className="hidden h-full w-px bg-gradient-to-b from-transparent via-gray-200 to-transparent opacity-60 lg:block lg:self-stretch"
                  aria-hidden="true"
                />
                <aside
                  className={`duration-[350ms] transition-all ease-in-out lg:w-[520px] lg:flex-shrink-0 ${
                    isAnimating
                      ? "translate-x-0 transform opacity-100"
                      : "translate-x-0 transform opacity-100"
                  }`}
                  aria-label="Search results"
                >
                  <div className="flex h-[calc(100vh-80px)] flex-col pt-10 lg:pl-8">
                    <section className="scrollbar-hide min-h-0 flex-1 overflow-y-auto">
                      <AnimatedMount delay={0.2}>
                        <RecommendSection items={results} showTitle={false} />
                      </AnimatedMount>
                    </section>
                  </div>
                </aside>
              </div>
            ) : (
              // Chat mode: Two-column layout (Left: Search Results | Right: Chat)
              <div className="flex h-full max-w-[1600px] px-6 lg:ml-[104px]">
                {/* Left Column: Search Results */}
                <div
                  className="scrollbar-hide min-w-0 max-w-[600px] flex-1 overflow-y-auto"
                  aria-label="Search results"
                >
                  <div className="flex h-full flex-col">
                    <div className="flex-1 px-8 pt-10">
                      {results.length > 0 ? (
                        <RecommendSection items={results} showTitle={false} />
                      ) : (
                        <div className="flex h-full items-center justify-center">
                          <div className="px-6 text-center">
                            <div className="mb-4 text-4xl">🔍</div>
                            <h3 className="mb-2 text-lg font-medium text-gray-900">
                              Do you want to do some search today?
                            </h3>
                            <p className="text-sm text-gray-500">Search results will appear here</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Divider */}
                <div className="w-px flex-shrink-0 bg-gradient-to-b from-transparent via-gray-200 to-transparent opacity-60" />

                {/* Right Column: Chat - Always Present */}
                <ChatInterface
                  messages={chatMessages}
                  isTyping={isChatTyping}
                  error={chatError}
                  input={chatInput}
                  onInputChange={setChatInput}
                  onSendMessage={handleSendMessage}
                  onStopGeneration={stopGeneration}
                  isAgentMode={isAgentMode}
                  onAgentModeToggle={() => setIsAgentMode(!isAgentMode)}
                  isLoading={isChatLoading}
                  onNewChat={handleNewChat}
                  promptTokens={currentPromptTokens}
                  isResearchMode={isResearchMode}
                  researchElapsedSeconds={researchElapsedSeconds}
                />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
