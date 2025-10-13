"use client";

import React, { useEffect, useState } from "react";
import type { SearchCandidate } from "@/types";

interface RecommendSectionProps {
  items: SearchCandidate[];
  title?: string;
  showTitle?: boolean;
  maxItems?: number;
  className?: string;
  isSelectionMode?: boolean;
  selectedSources?: string[];
  onSourceToggle?: (sourceId: string) => void;
  getSelectionNumber?: (sourceId: string) => number | null;
  showSelectionCircles?: boolean;
}

interface SearchResultItemProps {
  item: SearchCandidate;
  index: number;
  isSelectionMode?: boolean;
  isSelected?: boolean;
  selectionNumber?: number | null;
  onToggle?: () => void;
  showSelectionCircles?: boolean;
  animationDelay?: number;
}

/**
 * Individual search result item component with Google search results style
 */
function SearchResultItem({
  item,
  index,
  isSelectionMode,
  isSelected,
  selectionNumber,
  onToggle,
  showSelectionCircles,
  animationDelay = 0,
}: SearchResultItemProps): React.ReactElement {
  const [isAnimated, setIsAnimated] = useState(false);
  const [hasAppeared, setHasAppeared] = useState(false);

  useEffect(() => {
    if (showSelectionCircles && isSelectionMode) {
      const timer = setTimeout(() => {
        setIsAnimated(true);
      }, animationDelay);
      return () => clearTimeout(timer);
    } else {
      setIsAnimated(false);
      return;
    }
  }, [showSelectionCircles, isSelectionMode, animationDelay]);

  // Stagger animation on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setHasAppeared(true);
    }, index * 60); // 60ms stagger
    return () => clearTimeout(timer);
  }, [index]);

  const handleClick = (e: React.MouseEvent) => {
    if (isSelectionMode) {
      e.preventDefault();
      onToggle?.();
    }
  };

  const handleTitleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <div
      className={`relative mb-6 transition-all duration-500 ease-out ${
        isSelectionMode ? "cursor-pointer" : ""
      } ${hasAppeared ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}
      style={{ marginBottom: "24px", paddingLeft: "24px" }}
      onClick={isSelectionMode ? handleClick : undefined}
    >
      <div
        className={`absolute -left-2 top-1 flex h-5 w-5 cursor-pointer items-center justify-center rounded-full border-2 transition-opacity duration-200 ease-out ${
          isSelectionMode && isAnimated
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0"
        } ${isSelected ? "border-black bg-black" : "border-gray-300 bg-transparent hover:border-gray-400"}`}
        onClick={handleClick}
      >
        {isSelected && selectionNumber && (
          <span className="text-xs font-bold leading-none text-white">{selectionNumber}</span>
        )}
      </div>

      <div className="flex-1">
        <h3 className="mb-1 text-[16px] leading-tight">
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="cursor-pointer text-[#1a0dab] hover:underline"
            onClick={handleTitleClick}
          >
            {item.title}
          </a>
        </h3>

        <div className="overflow-wrap-anywhere mb-2 break-words text-[13px] leading-tight text-[#006621]">
          {item.url}
        </div>

        <p className="break-words text-[14px] leading-relaxed text-[#4d5156]">{item.snippet}</p>
      </div>
    </div>
  );
}

/**
 * Sources section component with Google search results style
 */
export default function RecommendSection({
  items,
  title = "Sources",
  showTitle = true,
  maxItems = 20,
  className = "",
  isSelectionMode = false,
  selectedSources = [],
  onSourceToggle,
  getSelectionNumber,
  showSelectionCircles = false, // Add default value for new prop
}: RecommendSectionProps) {
  const displayItems = items.slice(0, maxItems);
  const selectedCount = selectedSources.length;

  if (!items.length) {
    return <div className={`h-full bg-white ${className}`} />;
  }

  return (
    <div className={`flex h-full flex-col bg-white ${className}`}>
      {showTitle && (
        <div className="flex flex-shrink-0 items-center justify-between px-4 py-4">
          <h2 className="text-base font-medium text-gray-800">{title}</h2>
          <span className="text-sm text-gray-500">
            {displayItems.length} of {items.length}
          </span>
        </div>
      )}

      <div
        className="flex-1 overflow-y-auto"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: "#d1d5db transparent",
        }}
      >
        <style jsx>{`
          div::-webkit-scrollbar {
            width: 6px;
          }
          div::-webkit-scrollbar-track {
            background: transparent;
          }
          div::-webkit-scrollbar-thumb {
            background-color: #d1d5db;
            border-radius: 3px;
          }
          div::-webkit-scrollbar-thumb:hover {
            background-color: #9ca3af;
          }
        `}</style>

        <div className="px-4 py-2">
          {displayItems.map((item, index) => (
            <SearchResultItem
              key={index}
              item={item}
              index={index}
              isSelectionMode={isSelectionMode}
              isSelected={selectedSources.includes(item.url)}
              selectionNumber={getSelectionNumber?.(item.url)}
              onToggle={() => onSourceToggle?.(item.url)}
              showSelectionCircles={showSelectionCircles}
              animationDelay={index * 50}
            />
          ))}
        </div>

        {isSelectionMode && selectedCount > 0 && (
          <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
            <p className="text-[13px] text-gray-600">
              {selectedCount} source{selectedCount !== 1 ? "s" : ""} selected
            </p>
          </div>
        )}

        {isSelectionMode && selectedCount === 0 && showSelectionCircles && (
          <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
            <p className="text-[13px] text-gray-500">Select sources to continue</p>
          </div>
        )}
      </div>
    </div>
  );
}
