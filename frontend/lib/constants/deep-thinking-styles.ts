/**
 * Deep Thinking Mode - Shared Gradient Animation Styles
 * Centralized constants for consistent theming across the application
 */

export const DEEP_THINKING_COLORS = {
  // Gradient color stops for border animation
  gradientStops:
    "#fecdd3 0%, #fda4af 15%, #fde68a 35%, #fcd34d 50%, #86efac 70%, #6ee7b7 85%, #fecdd3 100%",

  // Animation color sequence for SVG gradients
  animationSequence: "#fecdd3;#fda4af;#fde68a;#fcd34d;#86efac;#6ee7b7;#fecdd3",

  // Alternative animation sequences for variety
  animationSequence2: "#fde68a;#fcd34d;#86efac;#6ee7b7;#fecdd3;#fda4af;#fde68a",
  animationSequence3: "#86efac;#6ee7b7;#fecdd3;#fda4af;#fde68a;#fcd34d;#86efac",

  // Animation duration
  duration: "20s",
} as const;

/**
 * Generate inline style object for Deep Thinking mode border animation
 * Used for search input boxes with animated gradient borders
 */
export const getDeepThinkingBorderStyle = (): React.CSSProperties => ({
  borderColor: "transparent",
  backgroundImage: `linear-gradient(white, white), linear-gradient(90deg, ${DEEP_THINKING_COLORS.gradientStops})`,
  backgroundOrigin: "border-box",
  backgroundClip: "padding-box, border-box",
  backgroundSize: "auto, 200% 100%",
  animation: `gradient-flow ${DEEP_THINKING_COLORS.duration} linear infinite`,
});

/**
 * Normal style (non-Deep Thinking mode)
 */
export const getNormalBorderStyle = (): React.CSSProperties => ({
  borderColor: "#d1d5db",
});

/**
 * SVG Linear Gradient component for search icon
 * Props-based for reusability across different contexts
 */
export interface GradientDefsProps {
  id: string;
  /** Optional custom duration, defaults to DEEP_THINKING_COLORS.duration */
  duration?: string;
}

export const getSearchGradientProps = (id: string = "search-gradient"): GradientDefsProps => ({
  id,
  duration: DEEP_THINKING_COLORS.duration,
});

export const getBrainGradientProps = (id: string = "brain-gradient"): GradientDefsProps => ({
  id,
  duration: DEEP_THINKING_COLORS.duration,
});
