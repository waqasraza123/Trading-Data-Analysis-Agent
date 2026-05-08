import type { CSSProperties, ReactNode, ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/ui/cn";

export type MotionPreset = "fade-up" | "fade-in" | "scale-subtle" | "none";
export type MotionVariant = "up" | "scale" | "fade";

type MotionStyleVariables = CSSProperties & {
  "--motion-delay"?: string;
  "--motion-duration"?: string;
};

export type MotionRevealStyle = MotionStyleVariables;

type AnimatedElement = "div" | "section" | "article" | "main" | "header" | "aside" | "nav" | "ol" | "ul" | "li";

export type AnimateChildrenProps = ComponentPropsWithoutRef<"section"> & {
  as?: AnimatedElement;
  children: ReactNode;
  preset?: MotionPreset;
  delayMs?: number;
  durationMs?: number;
  style?: MotionStyleVariables;
};

export type AnimateListItemProps = AnimateChildrenProps & {
  index?: number;
  staggerMs?: number;
};

export const BASE_MOTION_DELAY_MS = 60;
const BASE_MOTION_DURATION_MS = 560;

const legacyVariantToPreset: Record<MotionVariant, MotionPreset> = {
  up: "fade-up",
  scale: "scale-subtle",
  fade: "fade-in",
};

const presetClassName: Record<MotionPreset, string> = {
  "fade-up": "motion-fade-up",
  "fade-in": "motion-fade-in",
  "scale-subtle": "motion-scale-subtle",
  none: "motion-no-motion",
};

const withMotionDefaults = (
  style: MotionStyleVariables | undefined,
  options: { preset?: MotionPreset; delayMs?: number; durationMs?: number; index?: number; staggerMs?: number },
): MotionStyleVariables => {
  const baseDelay = options.delayMs !== undefined ? options.delayMs : 0;
  const indexDelay = options.index !== undefined && options.index >= 0 ? options.index * (options.staggerMs ?? BASE_MOTION_DELAY_MS) : 0;
  const duration = options.durationMs !== undefined && options.durationMs > 0 ? options.durationMs : BASE_MOTION_DURATION_MS;
  const merged: MotionStyleVariables = {
    "--motion-delay": `${Math.max(0, Math.floor(baseDelay + indexDelay))}ms`,
    "--motion-duration": `${Math.max(0, Math.floor(duration))}ms`,
    ...style,
  };
  if (options.preset === "none") {
    return merged;
  }
  return merged;
};

function motionClass(preset: MotionPreset): string {
  return cn("motion-reveal", preset !== "none" && presetClassName[preset]);
}

function resolveTag(as: AnimatedElement): AnimatedElement {
  return as;
}

export function AnimatedSection({
  as = "section",
  children,
  preset = "fade-up",
  delayMs,
  durationMs,
  className,
  style,
  ...props
}: AnimateChildrenProps): JSX.Element {
  const Tag = resolveTag(as);
  const mergedStyle = withMotionDefaults(style, { preset, delayMs, durationMs });
  return (
    <Tag
      {...props}
      className={cn(motionClass(preset), className)}
      style={mergedStyle}
    >
      {children}
    </Tag>
  );
}

export function AnimatedListItem({
  as = "div",
  children,
  preset = "fade-up",
  index,
  staggerMs,
  delayMs,
  durationMs,
  className,
  style,
  ...props
}: AnimateListItemProps): JSX.Element {
  const Tag = resolveTag(as);
  const mergedStyle = withMotionDefaults(style, { preset, delayMs, durationMs, index, staggerMs });
  return (
    <Tag
      {...props}
      className={cn(motionClass(preset), className)}
      style={mergedStyle}
    >
      {children}
    </Tag>
  );
}

export function ShimmerSkeleton({ className, ariaLabel = "loading" }: { className?: string; ariaLabel?: string }): JSX.Element {
  return <div aria-label={ariaLabel} className={cn("motion-shimmer rounded-xl", className)} />;
}

export function PulseDot({ className }: { className?: string }): JSX.Element {
  return <span aria-hidden="true" className={cn("motion-pulse-dot inline-block rounded-full", className)} />;
}

export function motionRevealClass(variant: MotionVariant = "up"): string {
  return motionClass(legacyVariantToPreset[variant]);
}

export function motionRevealStyle(index = 0, stepMs = BASE_MOTION_DELAY_MS, durationMs?: number): MotionRevealStyle {
  const normalizedIndex = Math.max(0, Math.floor(index));
  const normalizedStep = Math.max(0, Math.floor(stepMs));
  return withMotionDefaults(undefined, {
    index: normalizedIndex,
    staggerMs: normalizedStep,
    durationMs,
    preset: "fade-up",
  });
}

export const motionCardClass = "motion-card";
