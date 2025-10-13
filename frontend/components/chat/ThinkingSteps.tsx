"use client";

import React, { useState, useEffect } from "react";
import {
  Search,
  Globe,
  Code,
  FileText,
  FilePlus,
  FileEdit,
  FolderOpen,
  Play,
  MessageSquare,
  Minimize2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Terminal,
} from "lucide-react";
import type { ThinkingStep } from "@/types";

interface ThinkingStepsProps {
  steps?: ThinkingStep[];
  className?: string;
}

// Get tool icon
const getToolIcon = (toolName: string, size: string = "w-4 h-4") => {
  if (toolName.startsWith("mcp_chrome-devtools_")) {
    return <Globe className={size} />;
  }

  const icons: Record<string, React.ReactElement> = {
    web_search: <Search className={size} />,
    execute_python: <Play className={size} />,
    file_read: <FileText className={size} />,
    file_write: <FilePlus className={size} />,
    file_edit: <FileEdit className={size} />,
    file_list: <FolderOpen className={size} />,
    research_assistant: <MessageSquare className={size} />,
    compact_context: <Minimize2 className={size} />,
  };
  return icons[toolName] || <Code className={size} />;
};

/**
 * ThinkingSteps - Clean Notion-style display of AI thinking process
 * Shows reasoning, input, and output for each step
 */
export default function ThinkingSteps({ steps, className = "" }: ThinkingStepsProps) {
  const [currentStep, setCurrentStep] = useState<ThinkingStep | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  // Get the latest step
  useEffect(() => {
    if (!steps || steps.length === 0) {
      setCurrentStep(null);
      return;
    }

    const latestStep = steps[steps.length - 1];
    setCurrentStep(latestStep);
  }, [steps]);

  // Don't render if no steps
  if (!steps || steps.length === 0) {
    return null;
  }

  const toggleStepExpansion = (stepNumber: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepNumber)) {
        next.delete(stepNumber);
      } else {
        next.add(stepNumber);
      }
      return next;
    });
  };

  return (
    <div className={`${className} mb-3 max-w-full`}>
      {isExpanded ? (
        // Expanded: show all steps
        <div className="rounded-lg border border-gray-200 bg-gray-50/50 transition-colors hover:bg-gray-50">
          <div className="p-4">
            {/* Header */}
            <div
              className="mb-3 flex cursor-pointer items-center justify-between"
              onClick={() => setIsExpanded(false)}
            >
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>
                  {steps?.length || 0} thinking step{steps && steps.length !== 1 ? "s" : ""}
                </span>
              </div>
              <ChevronDown className="h-4 w-4 text-gray-400" />
            </div>

            {/* Steps list */}
            <div className="space-y-2">
              {steps?.map((step, idx) => {
                const isStepExpanded = expandedSteps.has(step.step);

                return (
                  <div
                    key={idx}
                    className="overflow-hidden rounded-lg border border-gray-200 bg-white"
                  >
                    <div className="flex items-start gap-3 p-3">
                      {/* Icon */}
                      <div className="mt-0.5 h-5 w-5 flex-shrink-0 text-gray-400">
                        {getToolIcon(step.tool, "w-4 h-4")}
                      </div>

                      {/* Content */}
                      <div className="min-w-0 flex-1">
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-700">
                            {step.tool.replace(/_/g, " ")}
                          </span>
                          {step.success ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5 text-red-500" />
                          )}
                        </div>

                        {/* Reasoning (thinking) - Always show */}
                        {step.thinking && (
                          <div className="mb-2">
                            <div className="mb-1 text-xs text-gray-500">Reasoning:</div>
                            <p className="text-sm leading-relaxed text-gray-700">{step.thinking}</p>
                          </div>
                        )}

                        {/* URLs for web_search */}
                        {step.tool === "web_search" && step.urls && step.urls.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {step.urls.slice(0, 2).map((url, urlIdx) => (
                              <a
                                key={urlIdx}
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 hover:underline"
                                onClick={e => e.stopPropagation()}
                              >
                                <Globe className="h-3 w-3 flex-shrink-0" />
                                <span className="truncate">{new URL(url).hostname}</span>
                              </a>
                            ))}
                            {step.urls.length > 2 && (
                              <span className="ml-4 text-xs text-gray-400">
                                +{step.urls.length - 2} more
                              </span>
                            )}
                          </div>
                        )}

                        {/* Toggle for Input/Output */}
                        {(step.input || step.output) && (
                          <button
                            onClick={e => toggleStepExpansion(step.step, e)}
                            className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                          >
                            <Terminal className="h-3 w-3" />
                            <span>{isStepExpanded ? "Hide" : "Show"} details</span>
                            <ChevronRight
                              className={`h-3 w-3 transition-transform ${isStepExpanded ? "rotate-90" : ""}`}
                            />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Expanded details */}
                    {isStepExpanded && (
                      <div className="ml-8 space-y-2 border-t border-gray-100 px-3 pb-3 pt-2">
                        {/* Input */}
                        {step.input && Object.keys(step.input).length > 0 && (
                          <div>
                            <div className="mb-1 text-xs text-gray-500">Input:</div>
                            <pre className="overflow-x-auto rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-700">
                              {JSON.stringify(step.input, null, 2)}
                            </pre>
                          </div>
                        )}

                        {/* Output */}
                        {step.output && (
                          <div>
                            <div className="mb-1 text-xs text-gray-500">Output:</div>
                            <pre className="max-h-[200px] overflow-x-auto rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-700">
                              {step.output}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        // Collapsed: show only latest step
        <div
          className="cursor-pointer rounded-lg border border-gray-200 bg-white transition-colors hover:bg-gray-50/50"
          onClick={() => setIsExpanded(true)}
        >
          <div className="px-4 py-3">
            {currentStep && (
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="mt-0.5 flex-shrink-0">
                  <CheckCircle2 className="h-4 w-4 text-gray-400" />
                </div>

                {/* Content */}
                <div className="min-w-0 flex-1">
                  <div className="mb-0.5 flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Thinking complete</span>
                    {steps && steps.length > 1 && (
                      <span className="text-xs text-gray-400">· {steps.length} steps</span>
                    )}
                  </div>

                  {currentStep.thinking && (
                    <p className="line-clamp-2 text-sm leading-relaxed text-gray-600">
                      {currentStep.thinking}
                    </p>
                  )}
                </div>

                {/* Expand indicator */}
                <ChevronRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-300" />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
