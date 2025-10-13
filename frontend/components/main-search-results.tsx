"use client";
import { logger } from "@/lib/logger";

import type React from "react";
import { Copy, ThumbsUp, ThumbsDown } from "lucide-react";
import { useState } from "react";
import MarkdownRenderer from "./markdown-renderer";

interface MainSearchResultsProps {
  isLoading: boolean;
  isTyping: boolean;
  displayedAnswer: string;
  sources: Array<{ idx: number; title: string; url: string }>; // Add sources prop
  error: string | null;
  className?: string;
  answerDisplayRef?: React.RefObject<HTMLSpanElement | null>; // Ref for direct DOM streaming
}

interface ActionButtonProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick?: () => void;
  variant?: "default" | "active";
}

/**
 * Reusable action button component
 */
function ActionButton({ icon: Icon, label, onClick, variant = "default" }: ActionButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
        variant === "active"
          ? "bg-blue-50 text-blue-700 hover:bg-blue-100"
          : "text-gray-600 hover:bg-gray-100"
      }`}
      aria-label={label}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

/**
 * Main search results component displaying AI-generated responses
 * Now connects to real backend API instead of using mock data
 */
export default function MainSearchResults({
  isLoading,
  isTyping,
  displayedAnswer,
  sources,
  error,
  className = "",
  answerDisplayRef,
}: MainSearchResultsProps) {
  const [feedback, setFeedback] = useState<"helpful" | "not-helpful" | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(displayedAnswer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      logger.error("Failed to copy text:", error);
    }
  };

  const handleFeedback = (type: "helpful" | "not-helpful") => {
    setFeedback(type);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Main Answer Section */}
      <div className="rounded-lg bg-white">
        <div className="space-y-4">
          {/* Error State */}
          {error && !isLoading && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Answer Content - Show during streaming (isTyping) or when complete */}
          {(isTyping || displayedAnswer) && !error && (
            <>
              {/* Answer Text with Markdown Rendering */}
              {isTyping ? (
                // While typing, show plain text without cursor
                <div className="w-full max-w-none">
                  <div className="whitespace-pre-wrap break-words leading-relaxed text-black">
                    <span ref={answerDisplayRef} />
                  </div>
                </div>
              ) : (
                // After typing, render as Markdown with citations
                <div className="w-full max-w-none">
                  <MarkdownRenderer content={displayedAnswer} sources={sources} />
                </div>
              )}

              {/* Action Buttons - Only show when streaming is complete */}
              {!isTyping && (
                <div className="mt-6 flex items-center gap-2">
                  <ActionButton
                    icon={Copy}
                    label={copied ? "Copied!" : "Copy"}
                    onClick={handleCopy}
                  />
                  <ActionButton
                    icon={ThumbsUp}
                    label="Helpful"
                    onClick={() => handleFeedback("helpful")}
                    variant={feedback === "helpful" ? "active" : "default"}
                  />
                  <ActionButton
                    icon={ThumbsDown}
                    label="Not helpful"
                    onClick={() => handleFeedback("not-helpful")}
                    variant={feedback === "not-helpful" ? "active" : "default"}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
