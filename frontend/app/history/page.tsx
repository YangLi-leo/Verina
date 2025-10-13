"use client";

import React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Search, MessageCircle } from "lucide-react";
import { useHistory } from "@/hooks/useHistory";
import { Brand } from "@/components/brand";

export default function HistoryPage() {
  const router = useRouter();
  const { searchHistory, chatHistory } = useHistory();

  const handleSearchClick = (searchId: string) => {
    const historyItem = searchHistory.find(item => item.id === searchId);
    if (historyItem) {
      router.push(`/search?search_id=${searchId}&q=${encodeURIComponent(historyItem.query)}`);
    } else {
      router.push(`/search?search_id=${searchId}`);
    }
  };

  const handleChatClick = (chatId: string) => {
    router.push(`/search?session_id=${chatId}`);
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-white">
      {/* Header */}
      <header className="h-20 flex-shrink-0 border-b border-gray-100 bg-white">
        <div className="mx-auto flex h-full max-w-[1200px] items-center px-6">
          <Link href="/" className="flex items-center gap-3">
            <Brand variant="wordmark" size="md" />
          </Link>
          <div className="flex-1" />
          <Link
            href="/search"
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 transition-colors hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Search
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto flex w-full max-w-[1400px] flex-1 flex-col overflow-hidden px-6 py-10">
        <div className="mb-6 flex-shrink-0">
          <h1 className="mb-2 text-3xl font-semibold text-gray-900">History</h1>
          <p className="text-gray-600">View and manage your search and chat history</p>
        </div>

        {/* Two Column Layout - Flexible Height */}
        <div className="grid flex-1 grid-cols-2 gap-8 overflow-hidden">
          {/* Searches Column */}
          <div className="flex min-h-0 flex-col">
            <div className="mb-4 flex flex-shrink-0 items-center gap-2">
              <Search className="h-5 w-5 text-gray-600" />
              <h2 className="text-lg font-medium text-gray-900">Searches</h2>
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                {searchHistory.length}
              </span>
            </div>
            <div className="custom-scrollbar flex-1 space-y-2 overflow-y-auto overflow-x-hidden pr-2">
              {searchHistory.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 py-12 text-center">
                  <div className="mb-3 text-3xl">🔍</div>
                  <p className="text-sm text-gray-500">No search history yet</p>
                </div>
              ) : (
                searchHistory.map(item => (
                  <div
                    key={item.id}
                    onClick={() => handleSearchClick(item.id)}
                    className="group flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 transition-all duration-150 hover:border-gray-300 hover:bg-gray-50"
                  >
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 transition-colors group-hover:bg-gray-200">
                      <Search className="h-4 w-4 text-gray-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-gray-900">
                        {item.display_name || item.query}
                      </div>
                      <div className="mt-0.5 text-xs text-gray-500">{item.timestamp}</div>
                    </div>
                    <div className="flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
                      <ArrowLeft className="h-4 w-4 rotate-180 text-gray-400" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Chats Column */}
          <div className="flex min-h-0 flex-col">
            <div className="mb-4 flex flex-shrink-0 items-center gap-2">
              <MessageCircle className="h-5 w-5 text-gray-600" />
              <h2 className="text-lg font-medium text-gray-900">Chats</h2>
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                {chatHistory.length}
              </span>
            </div>
            <div className="custom-scrollbar flex-1 space-y-2 overflow-y-auto overflow-x-hidden pr-2">
              {chatHistory.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 py-12 text-center">
                  <div className="mb-3 text-3xl">💬</div>
                  <p className="text-sm text-gray-500">No chat history yet</p>
                </div>
              ) : (
                chatHistory.map(item => (
                  <div
                    key={item.id}
                    onClick={() => handleChatClick(item.id)}
                    className="group flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 transition-all duration-150 hover:border-gray-300 hover:bg-gray-50"
                  >
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 transition-colors group-hover:bg-gray-200">
                      <MessageCircle className="h-4 w-4 text-gray-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-gray-900">
                        {item.display_name || item.query}
                      </div>
                      <div className="mt-0.5 text-xs text-gray-500">{item.timestamp}</div>
                    </div>
                    <div className="flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
                      <ArrowLeft className="h-4 w-4 rotate-180 text-gray-400" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
