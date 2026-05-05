import type { JsonRecord, UUID } from "@/lib/api/types";

export type ChartCandle = {
  id: UUID;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  isFinal: boolean;
  qualityScore: number | null;
};

export type ChartCandleSlot =
  | {
      kind: "candle";
      index: number;
      timestamp: string;
      candle: ChartCandle;
    }
  | {
      kind: "gap";
      index: number;
      timestamp: string;
      missingCount: number;
    };

export type ChartPadding = {
  top: number;
  right: number;
  bottom: number;
  left: number;
};

export type ChartDimensions = {
  width: number;
  height: number;
  padding: ChartPadding;
};

export type ChartPriceDomain = {
  min: number;
  max: number;
};

export type ChartScales = {
  width: number;
  height: number;
  padding: ChartPadding;
  plotWidth: number;
  plotHeight: number;
  domain: ChartPriceDomain;
  candleWidth: number;
  xForIndex: (index: number) => number;
  yForPrice: (price: number) => number;
};

export type ChartTone = "neutral" | "good" | "warning" | "danger" | "info";

export type ChartZoneKind =
  | "observation"
  | "invalidation"
  | "target"
  | "supportResistance";

export type ChartZone = {
  id: string;
  label: string;
  detail: string | null;
  kind: ChartZoneKind;
  tone: ChartTone;
  lower: number | null;
  upper: number | null;
  level: number | null;
  source: string | null;
};

export type ChartSignalWindow = {
  start: string | null;
  end: string | null;
  label: string;
};

export type ChartPatternMarker = {
  timestamp: string | null;
  label: string;
  detail: string | null;
};

export type ChartOutcomeMarkerKind =
  | "followThrough"
  | "reversal"
  | "noFollowThrough"
  | "insufficient";

export type ChartOutcomeMarker = {
  id: string;
  timestamp: string | null;
  label: string;
  detail: string | null;
  kind: ChartOutcomeMarkerKind;
};

export type ChartBadge = {
  label: string;
  value: string;
  tone: ChartTone;
};

export type ChartWarning = {
  code: string;
  message: string;
};

export type ChartOverlays = {
  zones: ChartZone[];
  signalWindow: ChartSignalWindow | null;
  patternMarker: ChartPatternMarker | null;
  outcomeMarkers: ChartOutcomeMarker[];
};

export type RawZoneRecord = JsonRecord & {
  lower?: string | number | null;
  upper?: string | number | null;
  midpoint?: string | number | null;
  level?: string | number | null;
  price?: string | number | null;
  source?: string | null;
  zoneType?: string | null;
  role?: string | null;
  confidence?: string | null;
};
