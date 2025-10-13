"use client";

import { cn } from "@/lib/utils";

/**
 * Brand component props interface
 */
interface BrandProps {
  /** Brand display variant - mark shows only "V", wordmark shows full "Verina" */
  variant?: "mark" | "wordmark";
  /** Size of the brand text */
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  /** Additional CSS classes */
  className?: string;
}

/**
 * Size mapping for consistent typography scaling
 */
const BRAND_SIZE_MAP: Record<NonNullable<BrandProps["size"]>, string> = {
  xs: "text-xl",
  sm: "text-[26px]",
  md: "text-3xl",
  lg: "text-5xl",
  xl: "text-7xl",
} as const;

/**
 * Brand component for displaying the Verina logo/wordmark
 *
 * @param variant - Display variant (mark or wordmark)
 * @param size - Text size
 * @param className - Additional CSS classes
 * @returns JSX element with brand text
 */
export function Brand({ variant = "wordmark", size = "md", className }: BrandProps) {
  const brandText = variant === "mark" ? "V" : "Verina";

  return (
    <span className={cn("font-brand font-bold text-gray-800", BRAND_SIZE_MAP[size], className)}>
      {brandText}
    </span>
  );
}
