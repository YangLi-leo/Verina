/**
 * useAgentStage - Agent Mode State Machine
 *
 * Manages Agent mode stage state and timers
 * Syncs with backend AgentModeAgent state machine
 *
 * State transitions:
 * idle -> hil -> research -> idle
 *
 * @example
 * const { stage, elapsed, startHIL, startResearch, reset } = useAgentStage();
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { logger } from "@/lib/logger";

/**
 * Agent stage types
 * - idle: Initial state or Chat Mode
 * - hil: Agent Mode HIL (Human-in-Loop) planning stage
 * - research: Agent Mode Research deep investigation stage
 */
export type AgentStage = "idle" | "hil" | "research";

interface UseAgentStageReturn {
  // Current stage
  stage: AgentStage;

  // Research stage timer
  researchElapsedSeconds: number;

  // Convenient state checks
  isHILMode: boolean;
  isResearchMode: boolean;
  isIdle: boolean;

  // State transition methods
  startHIL: () => void;
  startResearch: () => void;
  reset: () => void;
}

/**
 * Agent state machine hook
 *
 * Responsibilities:
 * 1. Manage Agent stage state (idle/hil/research)
 * 2. Manage Research stage timer
 * 3. Provide clear state transition API
 * 4. Auto-cleanup timers to prevent memory leaks
 */
export function useAgentStage(): UseAgentStageReturn {
  // Core state
  const [stage, setStage] = useState<AgentStage>("idle");
  const [researchStartTime, setResearchStartTime] = useState<number | null>(null);
  const [researchElapsedSeconds, setResearchElapsedSeconds] = useState(0);

  // Timer reference (prevent memory leaks)
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Start HIL stage
   * Transition: idle -> hil
   */
  const startHIL = useCallback(() => {
    logger.log("[AgentStage] 🟦 Starting HIL planning stage");
    setStage("hil");
    setResearchStartTime(null);
    setResearchElapsedSeconds(0);
  }, []);

  /**
   * Start Research stage
   * Transition: hil -> research
   */
  const startResearch = useCallback(() => {
    logger.log("[AgentStage] 🟨 Starting Research stage");
    setStage("research");
    setResearchStartTime(Date.now());
    setResearchElapsedSeconds(0);
  }, []);

  /**
   * Reset to idle state
   * Transition: any -> idle
   * Cleans up all timers and state
   */
  const reset = useCallback(() => {
    logger.log("[AgentStage] ⬜ Resetting to idle");
    setStage("idle");
    setResearchStartTime(null);
    setResearchElapsedSeconds(0);

    // Clear timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  /**
   * Research timer effect
   * Updates elapsed time every second
   */
  useEffect(() => {
    // Only run timer in Research stage
    if (stage !== "research" || !researchStartTime) {
      // Clear timer if exists
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    // Start timer
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - researchStartTime) / 1000);
      setResearchElapsedSeconds(elapsed);
    }, 1000);

    // Cleanup function
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [stage, researchStartTime]);

  /**
   * Cleanup on unmount
   * Ensures timer is cleared to prevent memory leaks
   */
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  // Convenient state checks
  const isHILMode = stage === "hil";
  const isResearchMode = stage === "research";
  const isIdle = stage === "idle";

  return {
    stage,
    researchElapsedSeconds,
    isHILMode,
    isResearchMode,
    isIdle,
    startHIL,
    startResearch,
    reset,
  };
}

export default useAgentStage;
