type TimeframeSelectionStepProps = {
  timeframes: string[];
  selectedTimeframes: string[];
  onChange: (timeframes: string[]) => void;
};

export function TimeframeSelectionStep({
  timeframes,
  selectedTimeframes,
  onChange,
}: TimeframeSelectionStepProps) {
  function toggleTimeframe(timeframe: string) {
    if (selectedTimeframes.includes(timeframe)) {
      onChange(selectedTimeframes.filter((value) => value !== timeframe));
      return;
    }
    onChange([...selectedTimeframes, timeframe]);
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Symbols/timeframes</p>
        <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">Timeframe selection</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">Select candle intervals for final-candle readiness checks.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {timeframes.map((timeframe) => (
          <button
            key={timeframe}
            type="button"
            onClick={() => toggleTimeframe(timeframe)}
            className={`rounded-md border px-4 py-2 text-sm font-semibold ${
              selectedTimeframes.includes(timeframe)
                ? "border-teal-300 bg-teal-50 text-teal-800 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-100"
                : "border-[var(--line)] bg-[var(--panel)] text-slate-600 dark:text-slate-300"
            }`}
          >
            {timeframe}
          </button>
        ))}
      </div>
    </section>
  );
}
