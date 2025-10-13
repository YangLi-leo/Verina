"use client";

import React from "react";
import { X } from "lucide-react";
import { useRouter } from "next/navigation";
import type { SidebarProps } from "@/types";

interface HistorySidebarProps extends SidebarProps {
  onSearchClick?: (searchId: string) => void;
  onChatClick?: (chatId: string) => void;
}

const INITIAL_DISPLAY_COUNT = 10;

/** Slide-in sidebar displaying search and chat history. */
const HistorySidebar = React.memo(function HistorySidebar({
  isOpen,
  onClose,
  searchHistory,
  chatHistory,
  className = "",
  onSearchClick,
  onChatClick,
}: HistorySidebarProps) {
  const router = useRouter();

  const displayedSearches = searchHistory.slice(0, INITIAL_DISPLAY_COUNT);
  const displayedChats = chatHistory.slice(0, INITIAL_DISPLAY_COUNT);

  const hasMoreSearches = searchHistory.length > INITIAL_DISPLAY_COUNT;
  const hasMoreChats = chatHistory.length > INITIAL_DISPLAY_COUNT;

  return (
    <div
      className={`ease-[cubic-bezier(0.32,0.72,0,1)] fixed left-0 top-0 z-50 h-full w-80 border-r border-gray-200 bg-white shadow-lg transition-transform duration-300 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      } ${className}`}
    >
      <div
        className={`flex h-20 items-center justify-between border-b border-[#e5e5e7] px-6 transition-opacity delay-75 duration-300 ${
          isOpen ? "opacity-100" : "opacity-0"
        }`}
      >
        <h2 className="text-lg font-medium text-black">History</h2>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
          aria-label="Close sidebar"
        >
          <X className="h-6 w-6" />
        </button>
      </div>

      <div className="flex h-[calc(100%-80px)] flex-col px-6">
        {/* Searches Section - fixed 50% height, independently scrollable */}
        <div
          className={`flex flex-1 flex-col overflow-hidden transition-opacity delay-100 duration-300 ${
            isOpen ? "opacity-100" : "opacity-0"
          }`}
        >
          <div className="pb-3 pt-6">
            <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500">SEARCHES</h3>
          </div>
          <div className="custom-scrollbar flex-1 overflow-y-auto overflow-x-hidden">
            <div className="space-y-1 pr-2">
              {displayedSearches.map(item => (
                <div
                  key={item.id}
                  onClick={() => onSearchClick?.(item.id)}
                  className="flex h-10 cursor-pointer flex-col justify-center rounded-md px-3 transition-all duration-150 hover:scale-[1.02] hover:bg-[#f5f5f5] active:scale-[0.98] active:bg-[#ebebeb]"
                  title={item.query}
                >
                  <div className="truncate text-sm font-normal text-black">
                    {item.display_name || item.query}
                  </div>
                  <div className="text-xs text-gray-500">{item.timestamp}</div>
                </div>
              ))}
              {hasMoreSearches && (
                <button
                  onClick={() => router.push("/history")}
                  className="flex h-10 w-full cursor-pointer items-center justify-center rounded-md px-3 text-gray-500 transition-all duration-150 hover:scale-[1.02] hover:bg-[#f5f5f5] hover:text-gray-700 active:scale-[0.98] active:bg-[#ebebeb]"
                >
                  <span className="text-xs font-medium">View All</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Divider between sections */}
        <div className="my-3 h-px bg-gray-200" />

        {/* Chats Section - fixed 50% height, independently scrollable */}
        <div
          className={`flex flex-1 flex-col overflow-hidden transition-opacity delay-150 duration-300 ${
            isOpen ? "opacity-100" : "opacity-0"
          }`}
        >
          <div className="pb-3">
            <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500">CHATS</h3>
          </div>
          <div className="custom-scrollbar flex-1 overflow-y-auto overflow-x-hidden pb-6">
            <div className="space-y-1 pr-2">
              {displayedChats.map(item => (
                <div
                  key={item.id}
                  onClick={() => onChatClick?.(item.id)}
                  className="flex h-10 cursor-pointer flex-col justify-center rounded-md px-3 transition-all duration-150 hover:scale-[1.02] hover:bg-[#f5f5f5] active:scale-[0.98] active:bg-[#ebebeb]"
                  title={item.query}
                >
                  <div className="truncate text-sm font-normal text-black">
                    {item.display_name || item.query}
                  </div>
                  <div className="text-xs text-gray-500">{item.timestamp}</div>
                </div>
              ))}
              {hasMoreChats && (
                <button
                  onClick={() => router.push("/history")}
                  className="flex h-10 w-full cursor-pointer items-center justify-center rounded-md px-3 text-gray-500 transition-all duration-150 hover:scale-[1.02] hover:bg-[#f5f5f5] hover:text-gray-700 active:scale-[0.98] active:bg-[#ebebeb]"
                >
                  <span className="text-xs font-medium">View All</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

export { HistorySidebar };
