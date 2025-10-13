"use client";

import React from "react";

interface ContextIndicatorProps {
  promptTokens: number;
  maxTokens?: number;
}

/**
 * ContextIndicator - Shows context window usage with percentage text + circular ring
 * Positioned in top-right corner of input area
 */
export default function ContextIndicator({
  promptTokens,
  maxTokens = 400000, // Default: 400k context window
}: ContextIndicatorProps) {
  // Calculate usage percentage
  const percentage = Math.min((promptTokens / maxTokens) * 100, 100);

  // Determine color based on usage
  const getColor = () => {
    if (percentage < 60) return "#22c55e"; // Green
    if (percentage < 80) return "#eab308"; // Yellow
    return "#ef4444"; // Red
  };

  const getTextColor = () => {
    if (percentage < 60) return "text-green-600";
    if (percentage < 80) return "text-yellow-600";
    return "text-red-600";
  };

  // SVG circle math
  const size = 20;
  const strokeWidth = 2;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  // Format token count
  const formatTokens = (tokens: number): string => {
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`;
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(0)}k`;
    return tokens.toString();
  };

  return (
    <div
      className="group absolute right-4 top-3 flex cursor-help items-center gap-2"
      title={`Context: ${formatTokens(promptTokens)} / ${formatTokens(maxTokens)} tokens (${percentage.toFixed(1)}%)`}
    >
      {/* Percentage text on the left */}
      <span className={`text-xs font-medium ${getTextColor()} transition-colors duration-300`}>
        {percentage.toFixed(1)}%
      </span>

      {/* Circular progress ring on the right */}
      <svg width={size} height={size} className="flex-shrink-0 -rotate-90 transform">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>

      {/* Enhanced tooltip on hover */}
      <div className="pointer-events-none absolute right-0 top-full z-10 mt-2 whitespace-nowrap opacity-0 transition-opacity group-hover:opacity-100">
        <div className="rounded-lg bg-gray-900 px-3 py-2 text-xs text-white shadow-lg">
          <div className="font-medium">Context Window</div>
          <div className="mt-1 text-gray-300">
            {formatTokens(promptTokens)} / {formatTokens(maxTokens)} tokens
          </div>
        </div>
      </div>
    </div>
  );
}
