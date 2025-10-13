"use client";

import { Brand } from "@/components/brand";
import { Header } from "@/components/header";
import { HistorySidebar } from "@/components/history-sidebar";
import { SearchInput } from "@/components/search-input";
import React from "react";
import { useRouter } from "next/navigation";
import { useHistory } from "@/hooks/useHistory";
import { MessageCircle } from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false);
  const [deepThinking, setDeepThinking] = React.useState(false); // Deep thinking mode state
  const { searchHistory, chatHistory, loading } = useHistory();

  const toggleSidebar = React.useCallback(() => {
    setIsSidebarOpen(prev => !prev);
  }, []);

  // Prefetch search page resources to reduce initial rendering jank
  React.useEffect(() => {
    try {
      router.prefetch("/search");
    } catch {}
  }, [router]);

  const handleSearch = React.useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const formData = new FormData(event.currentTarget);
      const query = (formData.get("q") as string) || "";
      const q = query.trim();
      if (q) {
        // Pass deepThinking parameter to search page
        const params = new URLSearchParams({ q });
        if (deepThinking) {
          params.append("deep", "true");
        }
        router.push(`/search?${params.toString()}`);
      }
    },
    [router, deepThinking]
  );

  const handleSearchHistoryClick = React.useCallback(
    (searchId: string) => {
      // Find the history item to get the query
      const historyItem = searchHistory.find(item => item.id === searchId);
      if (historyItem) {
        router.push(`/search?search_id=${searchId}&q=${encodeURIComponent(historyItem.query)}`);
      } else {
        router.push(`/search?search_id=${searchId}`);
      }
      setIsSidebarOpen(false);
    },
    [router, searchHistory]
  );

  const handleChatHistoryClick = React.useCallback(
    (chatId: string) => {
      // Navigate to search page with session_id, will auto-switch to chat mode
      router.push(`/search?session_id=${chatId}`);
      setIsSidebarOpen(false);
    },
    [router]
  );

  const handleStartChat = React.useCallback(() => {
    // Navigate to search page with chat=true to trigger chat mode
    router.push("/search?chat=true");
  }, [router]);

  return (
    <div className="relative flex h-screen w-full flex-col overflow-hidden bg-white font-sans text-black">
      <HistorySidebar
        isOpen={isSidebarOpen}
        onClose={toggleSidebar}
        searchHistory={searchHistory}
        chatHistory={chatHistory}
        onSearchClick={handleSearchHistoryClick}
        onChatClick={handleChatHistoryClick}
      />

      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-20 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      <div
        className={`flex h-screen flex-col transition-all duration-300 ease-out ${
          isSidebarOpen ? "ml-80 w-[calc(100%-320px)]" : "w-full"
        }`}
      >
        <Header onHistoryClick={toggleSidebar} />
        <main className="flex h-full flex-1 flex-col">
          <div className="flex flex-1 flex-col items-center pt-16">
            <div className="flex w-full max-w-2xl flex-col items-center gap-8 px-4">
              <Brand variant="wordmark" size="xl" />
              <div className="flex w-full flex-col items-center gap-4">
                <SearchInput
                  onSubmit={handleSearch}
                  placeholder="What's on your mind now?"
                  autoFocus={true}
                  isLoading={loading}
                  deepThinking={deepThinking}
                  onDeepThinkingToggle={() => setDeepThinking(!deepThinking)}
                />
                <button
                  onClick={handleStartChat}
                  className="group flex items-center gap-2 rounded-full border border-gray-200 bg-white px-6 py-3 text-sm font-medium text-gray-700 shadow-sm transition-all duration-150 hover:border-gray-300 hover:bg-gray-50 hover:shadow"
                >
                  <MessageCircle className="h-4 w-4 text-gray-500 transition-colors group-hover:text-gray-700" />
                  <span>Start a Chat</span>
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
