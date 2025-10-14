"use client";

import React, { useRef, useEffect } from "react";
import { MessageCircle, Monitor, PenSquare } from "lucide-react";
import ThinkingSteps from "@/components/chat/ThinkingSteps";
import ArtifactCard from "@/components/chat/ArtifactCard";
import MarkdownRenderer from "@/components/markdown-renderer";
import ContextIndicator from "@/components/chat/ContextIndicator";
import type { ChatMessageUI } from "@/types";

interface ChatInterfaceProps {
  messages: ChatMessageUI[];
  isTyping: boolean;
  error: string | null;
  input: string;
  onInputChange: (value: string) => void;
  onSendMessage: () => void;
  onStopGeneration?: () => void;
  isAgentMode: boolean;
  onAgentModeToggle: () => void;
  isLoading: boolean;
  onNewChat: () => void;
  promptTokens?: number;
  isResearchMode?: boolean;
  researchElapsedSeconds?: number;
  isHILMode?: boolean; // HIL planning stage indicator
}

/**
 * Chat interface with message display, thinking steps visualization,
 * artifact preview, and Chat/Agent mode toggle.
 */
export function ChatInterface({
  messages,
  isTyping,
  error,
  input,
  onInputChange,
  onSendMessage,
  onStopGeneration,
  isAgentMode,
  onAgentModeToggle,
  isLoading,
  onNewChat,
  promptTokens = 0,
  isResearchMode = false,
  researchElapsedSeconds = 0,
  isHILMode = false,
}: ChatInterfaceProps) {
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);

  // Format elapsed seconds to MM:SS format
  const formatElapsedTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    // Use requestAnimationFrame to ensure DOM is fully rendered before scrolling
    // This is crucial for artifact cards which may take time to render
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        scrollToBottom();
      });
    });
  }, [messages, isTyping]);

  // Auto-adjust textarea height
  const adjustTextareaHeight = (textarea: HTMLTextAreaElement) => {
    if (!textarea.value.trim()) {
      textarea.style.height = "32px";
      return;
    }

    textarea.style.height = "auto";
    const scrollHeight = textarea.scrollHeight;
    const newHeight = Math.min(Math.max(scrollHeight, 32), 200);
    textarea.style.height = `${newHeight}px`;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onInputChange(e.target.value);
    adjustTextareaHeight(e.target);
  };

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const textarea = e.currentTarget;
    setTimeout(() => {
      adjustTextareaHeight(textarea);
    }, 0);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!input.trim() || isLoading) return;

    onSendMessage();

    // Reset textarea height after sending
    setTimeout(() => {
      if (chatInputRef.current) {
        chatInputRef.current.style.height = "32px";
      }
    }, 0);
  };

  return (
    <>
      <section className="w-[700px] flex-shrink-0" aria-label="Chat interface">
        <div className="flex h-[calc(100vh-81px)] flex-col">
          <div className="relative flex h-14 items-center border-b border-gray-100 bg-white px-6">
            {/* HIL Planning Stage Indicator - Left Side */}
            {isHILMode && !isResearchMode && (
              <div className="absolute left-6 flex items-center gap-2 text-sm">
                <div className="flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-blue-500"></div>
                  <span className="font-medium text-blue-700">Planning</span>
                </div>
                <span className="text-xs text-gray-500">Analyzing request</span>
              </div>
            )}

            {/* Research Mode Timer - Left Side */}
            {isResearchMode && (
              <div className="absolute left-6 flex items-center gap-2 text-sm">
                <div className="flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-amber-500"></div>
                  <span className="font-mono font-medium text-amber-700">
                    {formatElapsedTime(researchElapsedSeconds)}
                  </span>
                </div>
                <span className="text-xs text-gray-500">Research in progress</span>
              </div>
            )}

            {/* Title - Centered */}
            <h2 className="flex-1 text-center text-base font-medium text-gray-700">Deep Search Chat</h2>

            <button
              onClick={onNewChat}
              className="absolute right-6 rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
              aria-label="Start new chat"
              title="New Chat"
            >
              <PenSquare className="h-4 w-4" />
            </button>

            {/* Loading Progress Bar - shown when waiting for LLM response */}
            {isLoading && !isTyping && !isHILMode && !isResearchMode && (
              <div className="absolute bottom-0 left-0 h-0.5 w-full overflow-hidden bg-gray-100">
                <div className="h-full w-full origin-left animate-pulse bg-gradient-to-r from-transparent via-blue-500 to-transparent"></div>
              </div>
            )}
          </div>
          <div
            ref={chatAreaRef}
            className="scrollbar-hide flex-1 space-y-4 overflow-y-auto bg-white px-6 py-4"
          >
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <MessageCircle size={48} className="mx-auto mb-4 text-gray-300" />
                  <h3 className="mb-2 text-lg font-medium text-gray-900">Start a conversation</h3>
                  <p className="text-sm text-gray-500">Ask me anything or explore ideas together</p>
                </div>
              </div>
            ) : (
              <>
                {messages.map(message => (
                  <div
                    key={message.id}
                    className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {message.type === "user" ? (
                      <div className="max-w-[70%] rounded-xl bg-gray-100 px-4 py-3 text-sm leading-relaxed text-gray-900">
                        {message.content}
                      </div>
                    ) : (
                      <div className="w-full">
                        {message.thinking_steps && message.thinking_steps.length > 0 && (
                          <ThinkingSteps steps={message.thinking_steps} />
                        )}
                        <MarkdownRenderer
                          content={message.content}
                          sources={message.sources || []}
                        />

                        {/* Show artifact card if present */}
                        {message.artifact && <ArtifactCard artifact={message.artifact} />}
                      </div>
                    )}
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="flex items-center space-x-1 text-gray-500">
                      <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
                      <div
                        className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                        style={{ animationDelay: "0.1s" }}
                      ></div>
                      <div
                        className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                        style={{ animationDelay: "0.2s" }}
                      ></div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
          <div className="bg-white px-6 pb-4 pt-2">
            {error && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
                ⚠️ {error}
              </div>
            )}

            {/* Main Input Container */}
            <div
              className="relative border border-gray-200 bg-orange-50/30 shadow-sm"
              style={{ borderRadius: "12px" }}
            >
              {/* Context Window Indicator */}
              {promptTokens > 0 && <ContextIndicator promptTokens={promptTokens} />}

              {/* Input Area */}
              <div className="px-5 py-4">
                <textarea
                  ref={chatInputRef}
                  value={input}
                  onChange={handleInputChange}
                  onInput={handleInput}
                  onKeyPress={handleKeyPress}
                  placeholder="Plan, search, build anything"
                  className="scrollbar-hide h-auto max-h-[200px] min-h-[32px] w-full resize-none overflow-y-auto break-words bg-transparent text-base text-gray-800 placeholder-gray-400 focus:outline-none"
                  rows={1}
                  style={{ height: "32px", wordWrap: "break-word", overflowWrap: "break-word" }}
                />
              </div>

              {/* Bottom Bar */}
              <div className="flex items-center justify-between px-4 py-2.5">
                {/* Left Side - Mode Toggle */}
                <div className="flex items-center gap-2">
                  {/* Mode Toggle Button */}
                  <button
                    onClick={onAgentModeToggle}
                    className="relative flex w-[85px] items-center gap-1.5 rounded-full border border-gray-200 px-3 py-1 transition-colors hover:bg-white/50"
                    style={{ top: "2px", left: "-8px" }}
                  >
                    {isAgentMode ? (
                      <>
                        <Monitor className="h-3 w-3 text-gray-500" strokeWidth={2} />
                        <span className="font-mono text-xs text-gray-700">Agent</span>
                      </>
                    ) : (
                      <>
                        <MessageCircle className="h-3 w-3 text-gray-500" strokeWidth={2} />
                        <span className="font-mono text-xs text-gray-700">Chat</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Right Side - Action Buttons */}
                <div className="flex items-center gap-2">
                  {/* Send / Stop Button */}
                  {isLoading ? (
                    <button
                      onClick={onStopGeneration}
                      className="relative rounded-full bg-amber-600 p-1.5 text-white transition-colors hover:bg-amber-700"
                      style={{ top: "2px" }}
                      aria-label="Stop generation"
                    >
                      <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
                        <rect x="6" y="6" width="12" height="12" />
                      </svg>
                    </button>
                  ) : (
                    <button
                      onClick={handleSend}
                      disabled={!input.trim()}
                      className={`relative rounded-full p-1.5 transition-colors ${
                        input.trim()
                          ? "bg-amber-600 text-white hover:bg-amber-700"
                          : "cursor-not-allowed bg-gray-100 text-gray-400"
                      }`}
                      style={{ top: "2px" }}
                      aria-label="Send message"
                    >
                      <svg
                        className="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 10l7-7m0 0l7 7m-7-7v18"
                        />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
