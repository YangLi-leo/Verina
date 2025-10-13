"use client";

import React from "react";
import { Brain } from "lucide-react";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import {
  getDeepThinkingBorderStyle,
  getNormalBorderStyle,
  DEEP_THINKING_COLORS,
} from "@/lib/constants/deep-thinking-styles";

interface SearchInputProps {
  value?: string;
  onChange?: (value: string) => void;
  onSubmit?: (event: React.FormEvent<HTMLFormElement>) => void;
  placeholder?: string;
  isLoading?: boolean;
  autoFocus?: boolean;
  deepThinking: boolean;
  onDeepThinkingToggle: () => void;
  name?: string;
  widthClass?: string;
}

/**
 * Search input with Deep Thinking mode toggle.
 * Shows animated gradient border when Deep Thinking is enabled.
 */
const SearchInput = React.memo(function SearchInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Search...",
  isLoading = false,
  autoFocus = false,
  deepThinking,
  onDeepThinkingToggle,
  name = "q",
  widthClass = "w-full max-w-[600px]",
}: SearchInputProps) {
  return (
    <div className={`flex items-center gap-3 ${widthClass}`}>
      <div className="h-12 flex-1">
        <div
          className="h-full w-full rounded-[24px] border-2 bg-white"
          style={deepThinking ? getDeepThinkingBorderStyle() : getNormalBorderStyle()}
        >
          <form onSubmit={onSubmit} className="h-full">
            <div className="flex h-full items-center px-6">
              <input
                type="text"
                name={name}
                value={value}
                onChange={e => onChange?.(e.target.value)}
                placeholder={placeholder}
                autoFocus={autoFocus}
                autoComplete="off"
                className="flex-1 bg-transparent text-base text-gray-900 placeholder-gray-500 focus:outline-none"
                aria-label="Search query"
              />

              <div className="ml-2 flex items-center gap-2">
                <button
                  type="submit"
                  className={`p-1 transition-colors ${
                    deepThinking ? "text-transparent" : "text-gray-400 hover:text-gray-600"
                  }`}
                  aria-label="Search"
                >
                  {isLoading ? (
                    <LoadingSpinner size="sm" />
                  ) : (
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
                          <linearGradient id="search-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
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
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <button
        onClick={onDeepThinkingToggle}
        className="p-2"
        aria-label="Toggle deep thinking mode"
        title={deepThinking ? "Deep Thinking Mode ON" : "Deep Thinking Mode OFF"}
      >
        {deepThinking ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" strokeWidth="2.5">
            <defs>
              <linearGradient id="brain-gradient" x1="0%" y1="0%" x2="200%" y2="0%">
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
            {/* Brain SVG paths */}
            <path
              stroke="url(#brain-gradient)"
              d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"
            />
            <path
              stroke="url(#brain-gradient)"
              d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"
            />
            <path stroke="url(#brain-gradient)" d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
            <path stroke="url(#brain-gradient)" d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
            <path stroke="url(#brain-gradient)" d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
            <path stroke="url(#brain-gradient)" d="M3.477 10.896a4 4 0 0 1 .585-.396" />
            <path stroke="url(#brain-gradient)" d="M19.938 10.5a4 4 0 0 1 .585.396" />
            <path stroke="url(#brain-gradient)" d="M6 18a4 4 0 0 1-1.967-.516" />
            <path stroke="url(#brain-gradient)" d="M19.967 17.484A4 4 0 0 1 18 18" />
          </svg>
        ) : (
          <Brain size={20} strokeWidth={1.5} className="text-gray-400" />
        )}
      </button>
    </div>
  );
});

export { SearchInput };
