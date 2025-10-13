"use client";

import { motion } from "framer-motion";
import type { PropsWithChildren } from "react";

/**
 * Props for the AnimatedMount component
 */
interface AnimatedMountProps extends PropsWithChildren {
  /** Animation delay in seconds */
  delay?: number;
  /** Custom animation duration in seconds */
  duration?: number;
}

/**
 * Default animation configuration
 */
const DEFAULT_ANIMATION = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  duration: 0.4,
} as const;

/**
 * Animated mount wrapper component using Framer Motion
 * Provides smooth fade-in and slide-up animation for child elements
 *
 * @param children - Child elements to animate
 * @param delay - Animation delay in seconds (default: 0)
 * @param duration - Animation duration in seconds (default: 0.4)
 * @returns Animated wrapper component
 */
export function AnimatedMount({
  children,
  delay = 0,
  duration = DEFAULT_ANIMATION.duration,
}: AnimatedMountProps) {
  return (
    <motion.div
      initial={DEFAULT_ANIMATION.initial}
      animate={DEFAULT_ANIMATION.animate}
      transition={{
        duration,
        delay,
        ease: "easeOut",
      }}
    >
      {children}
    </motion.div>
  );
}
