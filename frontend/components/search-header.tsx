"use client";

import Link from "next/link";
import { Brain, Clock, LogIn, MessageCircle, Settings, User, UserPlus } from "lucide-react";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  getDeepThinkingBorderStyle,
  getNormalBorderStyle,
  DEEP_THINKING_COLORS,
} from "@/lib/constants/deep-thinking-styles";

interface SearchHeaderProps {
  query: string;
  setQuery: (query: string) => void;
  onSearch: (query: string, deepThinking: boolean) => void;
  isLoading: boolean;
  isWaitingForAnswer: boolean;
  currentKeyword: string;
  deepThinking: boolean;
  setDeepThinking: (value: boolean) => void;
  onChatToggle: () => void;
  onHistoryToggle: () => void;
  isAnimating: boolean;
}

/**
 * Header for search results page with search input, Deep Thinking toggle,
 * chat toggle, history sidebar toggle, and user menu.
 */
export function SearchHeader({
  query,
  setQuery,
  onSearch,
  isLoading,
  isWaitingForAnswer,
  currentKeyword,
  deepThinking,
  setDeepThinking,
  onChatToggle,
  onHistoryToggle,
  isAnimating,
}: SearchHeaderProps) {
  return (
    <header className="sticky top-0 z-50 h-20 flex-shrink-0 border-b border-gray-100 bg-white">
      <div className="relative flex h-full items-center">
        <div className="flex h-full w-full items-center px-6 lg:ml-[60px] lg:px-0">
          <div className="flex-shrink-0">
            <Link
              href="/"
              className="flex items-center justify-center rounded-lg px-2 py-1"
              aria-label="Return to homepage"
            >
              <Brand variant="wordmark" size="md" />
            </Link>
          </div>
          <div className="flex flex-1 items-center gap-3 pl-6">
            <div className="relative h-12 w-full max-w-[690px]">
              <div
                className="h-full w-full rounded-[24px] border-2 bg-white"
                style={deepThinking ? getDeepThinkingBorderStyle() : getNormalBorderStyle()}
              >
                <form
                  onSubmit={e => {
                    e.preventDefault();
                    const trimmedQuery = query.trim();
                    if (trimmedQuery && !isLoading) {
                      onSearch(trimmedQuery, deepThinking);
                    }
                  }}
                  className="flex h-full items-center px-6"
                >
                  <input
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    placeholder="Search..."
                    autoComplete="off"
                    className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-500 focus:outline-none"
                  />
                  <div className="ml-2 flex items-center gap-2">
                    {isWaitingForAnswer ? (
                      <div className="flex select-none items-center gap-2 pr-1">
                        <div className="relative">
                          {deepThinking ? (
                            // Deep mode: Brain with pulse
                            <>
                              <Brain
                                className="h-5 w-5 animate-pulse-slow"
                                stroke="url(#grad-deep)"
                                strokeWidth="2"
                              />
                              <svg
                                className="absolute inset-0 h-5 w-5 opacity-0"
                                viewBox="0 0 24 24"
                              >
                                <defs>
                                  <linearGradient
                                    id="grad-deep"
                                    x1="0%"
                                    y1="0%"
                                    x2="100%"
                                    y2="100%"
                                  >
                                    <stop offset="0%" stopColor="#ef4444">
                                      <animate
                                        attributeName="stop-color"
                                        values="#ef4444;#eab308;#22c55e;#ef4444"
                                        dur="2s"
                                        repeatCount="indefinite"
                                      />
                                    </stop>
                                    <stop offset="50%" stopColor="#eab308">
                                      <animate
                                        attributeName="stop-color"
                                        values="#eab308;#22c55e;#ef4444;#eab308"
                                        dur="2s"
                                        repeatCount="indefinite"
                                      />
                                    </stop>
                                    <stop offset="100%" stopColor="#22c55e">
                                      <animate
                                        attributeName="stop-color"
                                        values="#22c55e;#ef4444;#eab308;#22c55e"
                                        dur="2s"
                                        repeatCount="indefinite"
                                      />
                                    </stop>
                                  </linearGradient>
                                </defs>
                              </svg>
                              <div className="absolute inset-0 h-5 w-5 animate-ping opacity-30">
                                <div className="h-full w-full rounded-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500" />
                              </div>
                            </>
                          ) : (
                            // Standard mode: Spinning search icon
                            <>
                              <svg
                                className="h-5 w-5 animate-spin"
                                viewBox="0 0 24 24"
                                fill="none"
                                xmlns="http://www.w3.org/2000/svg"
                              >
                                <defs>
                                  <linearGradient
                                    id="grad-search"
                                    x1="0%"
                                    y1="0%"
                                    x2="100%"
                                    y2="100%"
                                  >
                                    <stop offset="0%" stopColor="#3b82f6">
                                      <animate
                                        attributeName="stop-color"
                                        values="#3b82f6;#8b5cf6;#ec4899;#3b82f6"
                                        dur="2s"
                                        repeatCount="indefinite"
                                      />
                                    </stop>
                                    <stop offset="100%" stopColor="#8b5cf6">
                                      <animate
                                        attributeName="stop-color"
                                        values="#8b5cf6;#ec4899;#3b82f6;#8b5cf6"
                                        dur="2s"
                                        repeatCount="indefinite"
                                      />
                                    </stop>
                                  </linearGradient>
                                </defs>
                                <circle
                                  cx="11"
                                  cy="11"
                                  r="8"
                                  stroke="url(#grad-search)"
                                  strokeWidth="2"
                                  fill="none"
                                />
                                <path
                                  d="m21 21-4.35-4.35"
                                  stroke="url(#grad-search)"
                                  strokeWidth="2"
                                  strokeLinecap="round"
                                />
                              </svg>
                              <div className="absolute inset-0 h-5 w-5 animate-ping opacity-20">
                                <svg viewBox="0 0 24 24" fill="none">
                                  <circle
                                    cx="11"
                                    cy="11"
                                    r="8"
                                    stroke="url(#grad-search)"
                                    strokeWidth="1"
                                  />
                                </svg>
                              </div>
                            </>
                          )}
                        </div>
                        <span className="animate-pulse text-xs font-medium sm:text-sm">
                          <span
                            className={`bg-[length:200%_auto] bg-clip-text text-transparent ${
                              deepThinking
                                ? "animate-gradient-flow bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                                : "animate-gradient bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"
                            }`}
                          >
                            {deepThinking
                              ? currentKeyword
                                ? `${currentKeyword}...`
                                : "Deep thinking..."
                              : currentKeyword
                                ? `${currentKeyword}...`
                                : "Searching..."}
                          </span>
                        </span>
                      </div>
                    ) : (
                      <button
                        className={`p-1 ${
                          deepThinking ? "text-transparent" : "text-gray-400 hover:text-gray-600"
                        }`}
                        aria-label="Search"
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke={deepThinking ? "url(#search-gradient)" : "currentColor"}
                          strokeWidth="2"
                        >
                          {deepThinking && (
                            <defs>
                              <linearGradient
                                id="search-gradient"
                                x1="0%"
                                y1="0%"
                                x2="100%"
                                y2="100%"
                              >
                                <stop offset="0%" stopColor="#fecdd3">
                                  <animate
                                    attributeName="stop-color"
                                    values={DEEP_THINKING_COLORS.animationSequence}
                                    dur={DEEP_THINKING_COLORS.duration}
                                    repeatCount="indefinite"
                                  />
                                </stop>
                                <stop offset="50%" stopColor="#fde68a">
                                  <animate
                                    attributeName="stop-color"
                                    values={DEEP_THINKING_COLORS.animationSequence2}
                                    dur={DEEP_THINKING_COLORS.duration}
                                    repeatCount="indefinite"
                                  />
                                </stop>
                                <stop offset="100%" stopColor="#86efac">
                                  <animate
                                    attributeName="stop-color"
                                    values={DEEP_THINKING_COLORS.animationSequence3}
                                    dur={DEEP_THINKING_COLORS.duration}
                                    repeatCount="indefinite"
                                  />
                                </stop>
                              </linearGradient>
                            </defs>
                          )}
                          <circle cx="11" cy="11" r="8" />
                          <path d="m21 21-4.35-4.35" />
                        </svg>
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>
            <button
              onClick={() => setDeepThinking(!deepThinking)}
              className="p-2"
              aria-label="Toggle deep thinking mode"
              title={deepThinking ? "Deep Thinking Mode ON" : "Deep Thinking Mode OFF"}
            >
              {deepThinking ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" strokeWidth="2.5">
                  <defs>
                    <linearGradient id="brain-gradient-search" x1="0%" y1="0%" x2="200%" y2="0%">
                      <stop offset="0%" stopColor="#fecdd3">
                        <animate
                          attributeName="stop-color"
                          values={DEEP_THINKING_COLORS.animationSequence}
                          dur={DEEP_THINKING_COLORS.duration}
                          repeatCount="indefinite"
                        />
                      </stop>
                      <stop offset="35%" stopColor="#fde68a">
                        <animate
                          attributeName="stop-color"
                          values={DEEP_THINKING_COLORS.animationSequence2}
                          dur={DEEP_THINKING_COLORS.duration}
                          repeatCount="indefinite"
                        />
                      </stop>
                      <stop offset="70%" stopColor="#86efac">
                        <animate
                          attributeName="stop-color"
                          values={DEEP_THINKING_COLORS.animationSequence3}
                          dur={DEEP_THINKING_COLORS.duration}
                          repeatCount="indefinite"
                        />
                      </stop>
                      <stop offset="100%" stopColor="#fecdd3">
                        <animate
                          attributeName="stop-color"
                          values={DEEP_THINKING_COLORS.animationSequence}
                          dur={DEEP_THINKING_COLORS.duration}
                          repeatCount="indefinite"
                        />
                      </stop>
                    </linearGradient>
                  </defs>
                  <path
                    stroke="url(#brain-gradient-search)"
                    d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"
                  />
                  <path
                    stroke="url(#brain-gradient-search)"
                    d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"
                  />
                  <path
                    stroke="url(#brain-gradient-search)"
                    d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"
                  />
                  <path stroke="url(#brain-gradient-search)" d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
                  <path stroke="url(#brain-gradient-search)" d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
                  <path
                    stroke="url(#brain-gradient-search)"
                    d="M3.477 10.896a4 4 0 0 1 .585-.396"
                  />
                  <path stroke="url(#brain-gradient-search)" d="M19.938 10.5a4 4 0 0 1 .585.396" />
                  <path stroke="url(#brain-gradient-search)" d="M6 18a4 4 0 0 1-1.967-.516" />
                  <path stroke="url(#brain-gradient-search)" d="M19.967 17.484A4 4 0 0 1 18 18" />
                </svg>
              ) : (
                <Brain size={20} strokeWidth={1.5} className="text-gray-400" />
              )}
            </button>
            <button
              onClick={onChatToggle}
              disabled={isAnimating}
              className="p-2 text-gray-400 transition-colors hover:text-gray-600 disabled:opacity-50"
              aria-label="Toggle chat mode"
              title="Chat"
            >
              <MessageCircle size={20} strokeWidth={1.5} />
            </button>
          </div>
        </div>
        <div className="pointer-events-none absolute right-6 top-1/2 -translate-y-1/2">
          <div className="pointer-events-auto flex items-center gap-4">
            <button
              onClick={onHistoryToggle}
              className="flex h-6 w-6 cursor-pointer items-center justify-center text-gray-500 transition-colors hover:text-gray-700"
              aria-label="Open history sidebar"
            >
              <Clock size={24} />
            </button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10 rounded-full border border-gray-200 bg-white shadow-sm hover:border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-0 focus:ring-offset-0 focus-visible:ring-0 focus-visible:ring-offset-0"
                  aria-label="Open user menu"
                >
                  <User className="h-5 w-5 text-gray-800" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 rounded-xl p-2">
                <Link href="/login">
                  <DropdownMenuItem className="flex items-center gap-3 px-3 py-2.5 text-sm outline-none hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-0">
                    <LogIn className="h-4 w-4 text-gray-500" />
                    Sign in
                  </DropdownMenuItem>
                </Link>
                <Link href="/signup">
                  <DropdownMenuItem className="flex items-center gap-3 px-3 py-2.5 text-sm outline-none hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-0">
                    <UserPlus className="h-4 w-4 text-gray-500" />
                    Sign up
                  </DropdownMenuItem>
                </Link>
                <Link href="/personal-info">
                  <DropdownMenuItem className="flex items-center gap-3 px-3 py-2.5 text-sm outline-none hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-0">
                    <Settings className="h-4 w-4 text-gray-500" />
                    Personal Info
                  </DropdownMenuItem>
                </Link>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </header>
  );
}
