import type { SymbolRead } from "@/lib/api/types";
import { OnboardingEmptyState } from "./OnboardingEmptyState";

type SymbolSelectionStepProps = {
  symbols: SymbolRead[];
  selectedSymbolIds: string[];
  onChange: (symbolIds: string[]) => void;
};

export function SymbolSelectionStep({ symbols, selectedSymbolIds, onChange }: SymbolSelectionStepProps) {
  function toggleSymbol(symbolId: string) {
    if (selectedSymbolIds.includes(symbolId)) {
      onChange(selectedSymbolIds.filter((id) => id !== symbolId));
      return;
    }
    onChange([...selectedSymbolIds, symbolId]);
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase text-slate-500">Step 2</p>
        <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">Symbol selection</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">Choose one or more active symbols to validate.</p>
      </div>
      {symbols.length === 0 ? (
        <OnboardingEmptyState title="No symbols returned" message="Seed symbols in the API before readiness checks can run." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {symbols.map((symbol) => (
            <label key={symbol.id} className="muted-surface flex cursor-pointer items-start gap-3 rounded-lg p-4">
              <input
                type="checkbox"
                checked={selectedSymbolIds.includes(symbol.id)}
                onChange={() => toggleSymbol(symbol.id)}
                className="mt-1"
              />
              <span>
                <span className="block font-semibold text-[var(--strong)]">{symbol.symbol}</span>
                <span className="mt-1 block text-sm text-slate-500">{symbol.display_name}</span>
              </span>
            </label>
          ))}
        </div>
      )}
    </section>
  );
}
