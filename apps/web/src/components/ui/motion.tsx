import type { CSSProperties, ReactNode, ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/ui/cn";

export const MOTION_VARIANTS = ["up", "scale", "fade"] as const;
export const MOTION_PRESETS = ["fade-up", "fade-in", "scale-subtle", "none"] as const;
export const DEFAULT_MOTION_PRESET = "fade-up" as const;

export const BASE_MOTION_DELAY_MS = 60;
export const BASE_MOTION_DURATION_MS = 560;
export const DEFAULT_MOTION_REVEAL_STEP_MS = 45;
export const COMFORT_MOTION_REVEAL_STEP_MS = 60;
export const MOTION_INTERACTIVE_CLASS =
  "motion-hover-lift focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)]";

export type MotionVariant = (typeof MOTION_VARIANTS)[number];
export type MotionPreset = (typeof MOTION_PRESETS)[number];
export type MotionRevealDensity = "compact" | "regular" | "comfortable";

export type MotionStyleVariables = CSSProperties & {
  "--motion-delay"?: string;
  "--motion-duration"?: string;
};

export type MotionRevealProfile = {
  preset?: MotionPreset;
  stepMs?: number;
  delayMs?: number;
  durationMs?: number;
};

type MotionDefaultsOptions = {
  preset?: MotionPreset;
  delayMs?: number;
  durationMs?: number;
  index?: number;
  staggerMs?: number;
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

function clampMotionNumber(input: number, fallback: number): number {
  if (!Number.isFinite(input)) {
    return fallback;
  }
  return Math.max(0, Math.floor(input));
}

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

export const MOTION_REVEAL_PROFILES: Record<MotionRevealDensity, MotionRevealProfile> = {
  compact: { preset: "scale-subtle", stepMs: 30 },
  regular: { preset: "fade-up", stepMs: DEFAULT_MOTION_REVEAL_STEP_MS },
  comfortable: { preset: "fade-up", stepMs: COMFORT_MOTION_REVEAL_STEP_MS },
};

const withMotionDefaults = (
  style: MotionStyleVariables | undefined,
  options: MotionDefaultsOptions,
): MotionStyleVariables => {
  const baseDelay = options.delayMs !== undefined ? clampMotionNumber(options.delayMs, 0) : 0;
  const indexValue = options.index !== undefined ? clampMotionNumber(options.index, 0) : 0;
  const indexDelay = indexValue * clampMotionNumber(options.staggerMs ?? BASE_MOTION_DELAY_MS, BASE_MOTION_DELAY_MS);
  const duration = options.durationMs !== undefined ? clampMotionNumber(options.durationMs, BASE_MOTION_DURATION_MS) : BASE_MOTION_DURATION_MS;
  const merged: MotionStyleVariables = {
    "--motion-delay": `${baseDelay + indexDelay}ms`,
    "--motion-duration": `${duration}ms`,
    ...style,
  };
  if (options.preset === "none") {
    return merged;
  }
  return merged;
};

function motionClass(preset: MotionPreset): string {
  return cn("motion-reveal", presetClassName[preset]);
}

function resolveTag(as: AnimatedElement): AnimatedElement {
  return as;
}

export function AnimatedSection({
  as = "section",
  children,
  preset = DEFAULT_MOTION_PRESET,
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
  preset = DEFAULT_MOTION_PRESET,
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

export function ShimmerSkeleton({
  className,
  ariaLabel = "loading",
  ariaHidden = true,
}: {
  className?: string;
  ariaLabel?: string;
  ariaHidden?: boolean;
}): JSX.Element {
  return (
    <div
      aria-hidden={ariaHidden}
      aria-label={ariaLabel}
      className={cn("motion-shimmer rounded-xl", className)}
    />
  );
}

export function PulseDot({ className }: { className?: string }): JSX.Element {
  return <span aria-hidden="true" className={cn("motion-pulse-dot inline-block rounded-full", className)} />;
}

export function motionRevealClass(variant: MotionVariant = "up"): string {
  return motionClass(legacyVariantToPreset[variant]);
}

export function motionRevealStyle(index = 0, stepMs = DEFAULT_MOTION_REVEAL_STEP_MS, durationMs?: number): MotionRevealStyle {
  const normalizedIndex = clampMotionNumber(index, 0);
  const normalizedStep = clampMotionNumber(stepMs, BASE_MOTION_DELAY_MS);
  return withMotionDefaults(undefined, {
    index: normalizedIndex,
    staggerMs: normalizedStep,
    durationMs,
    preset: "fade-up",
  });
}

export function motionRevealProfileStyle(
  index = 0,
  profile: MotionRevealProfile = {},
): MotionRevealStyle {
  const normalizedIndex = clampMotionNumber(index, 0);
  const normalizedStep = clampMotionNumber(profile.stepMs ?? DEFAULT_MOTION_REVEAL_STEP_MS, DEFAULT_MOTION_REVEAL_STEP_MS);
  const normalizedDelay = clampMotionNumber(profile.delayMs ?? 0, 0);
  const durationMs = profile.durationMs !== undefined ? clampMotionNumber(profile.durationMs, BASE_MOTION_DURATION_MS) : BASE_MOTION_DURATION_MS;
  const preset = profile.preset ?? DEFAULT_MOTION_PRESET;

  return withMotionDefaults(undefined, {
    index: normalizedIndex,
    delayMs: normalizedDelay,
    durationMs,
    staggerMs: normalizedStep,
    preset,
  });
}

export function motionRevealDensityStyle(index = 0, density: MotionRevealDensity = "regular", durationMs?: number): MotionRevealStyle {
  const profile = MOTION_REVEAL_PROFILES[density];
  return withMotionDefaults(undefined, {
    index,
    delayMs: profile.delayMs ?? 0,
    durationMs,
    staggerMs: profile.stepMs ?? DEFAULT_MOTION_REVEAL_STEP_MS,
    preset: profile.preset ?? DEFAULT_MOTION_PRESET,
  });
}

export const motionCardClass = "motion-card";
