import Link from "next/link";
import type { ReactNode } from "react";
import { getProductConfig } from "@/config/product";

const featureGroups = [
  {
    index: "01",
    title: "Market data foundation",
    description:
      "Normalize CSV imports, provider polling, live candles, and Go worker ingestion into one auditable Postgres model.",
    tags: ["Final-candle analysis", "Provider health", "Gap recovery"],
  },
  {
    index: "02",
    title: "Deterministic intelligence",
    description:
      "Build signals from typed indicators, patterns, quality gates, market regimes, evidence, and reproducible engine runs.",
    tags: ["Signal classification", "Confidence", "Backtesting"],
  },
  {
    index: "03",
    title: "Grounded AI workflows",
    description:
      "Layer explanations and paper-only planning over persisted evidence without letting a model rewrite source signals.",
    tags: ["Evidence-first", "Paper plans", "Human review"],
  },
  {
    index: "04",
    title: "SaaS-ready operations",
    description:
      "Start with Neon-backed accounts, workspace RBAC, job queues, worker health, audit trails, and fail-soft dashboards.",
    tags: ["Session auth", "Workspaces", "Observability"],
  },
];

const stack = [
  ["WEB", "Next.js 15 · React 19 · TypeScript"],
  ["API", "FastAPI · SQLAlchemy · Alembic"],
  ["DATA", "Neon Postgres · Redis · normalized candles"],
  ["WORK", "Python workers · Go market sidecar"],
];

const reviewFlow = [
  "Ingest and validate market data",
  "Run deterministic analysis",
  "Rank setups for human review",
  "Explain only persisted evidence",
  "Record outcomes and journal notes",
];

export function LandingPage() {
  const product = getProductConfig();

  return (
    <main className="landing-grid min-h-screen overflow-hidden bg-[#050811] text-slate-100">
      <div className="landing-glow pointer-events-none fixed inset-0" />
      <header className="relative z-20 border-b border-white/10 bg-[#050811]/80 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-5 px-5 sm:px-8">
          <Link className="flex items-center gap-3 font-semibold tracking-tight" href="/">
            <BrandMark />
            <span className="hidden sm:inline">{product.name}</span>
            <span className="sm:hidden">Trading SaaS Kit</span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-slate-400 md:flex" aria-label="Landing navigation">
            <a className="transition hover:text-white" href="#features">Features</a>
            <a className="transition hover:text-white" href="#architecture">Architecture</a>
            <a className="transition hover:text-white" href="#quick-start">Quick start</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-300 transition hover:bg-white/5 hover:text-white" href="/login">
              Sign in
            </Link>
            <a className="rounded-lg border border-teal-300/30 bg-teal-300 px-3.5 py-2 text-sm font-bold text-slate-950 transition hover:bg-teal-200" href={product.templateUrl}>
              Use template
            </a>
          </div>
        </div>
      </header>

      <section className="relative z-10 mx-auto grid max-w-7xl gap-14 px-5 pb-24 pt-20 sm:px-8 lg:grid-cols-[1.08fr_0.92fr] lg:items-center lg:pb-32 lg:pt-28">
        <div className="motion-reveal motion-reveal-up">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-300/20 bg-teal-300/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-teal-200">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-300 shadow-[0_0_16px_#5eead4]" />
            Open-source · MIT licensed
          </div>
          <h1 className="max-w-3xl text-5xl font-semibold leading-[0.98] tracking-[-0.045em] text-white sm:text-6xl lg:text-7xl">
            Ship an AI trading SaaS without rebuilding the foundation.
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-400 sm:text-xl">
            A production-minded starter kit for market data, deterministic intelligence, grounded AI explanations, paper-only agent plans, and daily review workflows.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <a className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-teal-300 px-5 text-sm font-bold text-slate-950 shadow-[0_18px_60px_rgba(45,212,191,0.2)] transition hover:-translate-y-0.5 hover:bg-teal-200" href={product.templateUrl}>
              Start from this template <ArrowIcon />
            </a>
            <Link className="inline-flex min-h-12 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-5 text-sm font-bold text-white transition hover:border-white/30 hover:bg-white/10" href="/register">
              Create a workspace
            </Link>
          </div>
          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 font-mono text-xs text-slate-500">
            <span>Next.js 15</span><span>FastAPI</span><span>Neon Postgres</span><span>Go</span><span>Docker</span>
          </div>
        </div>
        <DashboardPreview />
      </section>

      <section className="relative z-10 border-y border-white/10 bg-white/[0.025]" aria-label="Safety boundary">
        <div className="mx-auto grid max-w-7xl gap-5 px-5 py-7 text-sm sm:px-8 md:grid-cols-[auto_1fr_auto] md:items-center">
          <span className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-teal-300">Built-in boundary</span>
          <p className="text-slate-300">Deterministic engines classify. AI explains supplied evidence. Humans review the result.</p>
          <span className="w-fit rounded-full border border-emerald-300/20 bg-emerald-300/5 px-3 py-1 text-xs font-semibold text-emerald-200">No broker execution</span>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-7xl px-5 py-24 sm:px-8 lg:py-32" id="features">
        <SectionHeading eyebrow="What you get" title="A vertical starter kit, not an empty dashboard." description="Use the full opinionated stack or replace modules behind typed boundaries as your product evolves." />
        <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 md:grid-cols-2">
          {featureGroups.map((feature) => (
            <article className="bg-[#080d18] p-7 sm:p-9" key={feature.index}>
              <span className="font-mono text-xs font-bold text-teal-300">{feature.index}</span>
              <h3 className="mt-5 text-2xl font-semibold tracking-tight text-white">{feature.title}</h3>
              <p className="mt-3 max-w-xl leading-7 text-slate-400">{feature.description}</p>
              <div className="mt-6 flex flex-wrap gap-2">
                {feature.tags.map((tag) => <span className="rounded-md border border-white/10 bg-white/[0.035] px-2.5 py-1 font-mono text-[11px] text-slate-400" key={tag}>{tag}</span>)}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="relative z-10 border-y border-white/10 bg-[#070b14]" id="architecture">
        <div className="mx-auto grid max-w-7xl gap-14 px-5 py-24 sm:px-8 lg:grid-cols-2 lg:items-center lg:py-32">
          <div>
            <SectionHeading eyebrow="Architecture" title="Clear ownership from browser to candle." description="Python remains the product brain. Go handles bounded ingestion work. Neon stores the auditable source of truth." />
            <div className="mt-9 space-y-3">
              {stack.map(([label, value]) => (
                <div className="grid grid-cols-[4rem_1fr] items-center gap-4 rounded-xl border border-white/10 bg-white/[0.025] p-4" key={label}>
                  <span className="font-mono text-xs font-bold text-teal-300">{label}</span>
                  <span className="text-sm text-slate-300">{value}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#050810] p-3 shadow-2xl shadow-black/40">
            <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-400/70" /><span className="h-2.5 w-2.5 rounded-full bg-amber-300/70" /><span className="h-2.5 w-2.5 rounded-full bg-emerald-300/70" />
              <span className="ml-2 font-mono text-[10px] text-slate-600">review-pipeline.ts</span>
            </div>
            <ol className="space-y-1 p-4 font-mono text-sm">
              {reviewFlow.map((item, index) => (
                <li className="flex items-center gap-4 rounded-lg px-3 py-3 text-slate-300" key={item}>
                  <span className="text-slate-600">{String(index + 1).padStart(2, "0")}</span>
                  <span className="h-px w-6 bg-teal-300/40" />
                  <span>{item}</span>
                  <span className="ml-auto text-emerald-300">✓</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-5xl px-5 py-24 text-center sm:px-8 lg:py-32" id="quick-start">
        <SectionHeading centered eyebrow="Quick start" title="From template to local cockpit." description="Bring up the full development stack, apply the schema, and seed deterministic defaults." />
        <div className="mt-10 overflow-hidden rounded-2xl border border-white/10 bg-[#03050a] text-left shadow-2xl shadow-black/40">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-3 font-mono text-xs text-slate-500"><span>terminal</span><span>three commands</span></div>
          <pre className="overflow-x-auto p-6 font-mono text-sm leading-8 text-slate-300"><code><span className="text-slate-600">$</span> make dev{"\n"}<span className="text-slate-600">$</span> make migrate{"\n"}<span className="text-slate-600">$</span> make seed</code></pre>
        </div>
        <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
          <a className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-teal-300 px-5 text-sm font-bold text-slate-950 transition hover:bg-teal-200" href={product.templateUrl}>Use the GitHub template <ArrowIcon /></a>
          <a className="inline-flex min-h-12 items-center justify-center rounded-xl border border-white/15 px-5 text-sm font-bold text-white transition hover:bg-white/5" href={`${product.repositoryUrl}#quick-start`}>Read the setup guide</a>
        </div>
      </section>

      <footer className="relative z-10 border-t border-white/10 bg-[#03050a]">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-9 text-sm text-slate-500 sm:px-8 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3 text-slate-300"><BrandMark /><span>{product.name}</span></div>
          <p>Market intelligence infrastructure. No broker execution or financial advice.</p>
          <div className="flex gap-5"><a className="hover:text-white" href={product.repositoryUrl}>GitHub</a><Link className="hover:text-white" href="/login">Sign in</Link></div>
        </div>
      </footer>
    </main>
  );
}

function DashboardPreview() {
  return (
    <div className="motion-reveal motion-reveal-scale relative mx-auto w-full max-w-xl [animation-delay:140ms]">
      <div className="absolute -inset-10 -z-10 bg-[radial-gradient(circle,rgba(45,212,191,0.12),transparent_65%)]" />
      <div className="overflow-hidden rounded-2xl border border-white/15 bg-[#080d17]/95 shadow-[0_30px_100px_rgba(0,0,0,0.55)]">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_12px_#6ee7b7]" /><span className="font-mono text-[10px] uppercase tracking-[0.15em] text-slate-400">Command center · Live model</span></div>
          <span className="font-mono text-[10px] text-slate-600">UTC 09:42</span>
        </div>
        <div className="grid grid-cols-3 gap-px bg-white/10">
          <PreviewMetric label="Readiness" value="92%" tone="text-emerald-300" />
          <PreviewMetric label="Review first" value="07" tone="text-white" />
          <PreviewMetric label="Data health" value="GOOD" tone="text-teal-300" />
        </div>
        <div className="grid gap-4 p-4 sm:grid-cols-[1.3fr_0.7fr]">
          <div className="rounded-xl border border-white/10 bg-black/20 p-4">
            <div className="mb-4 flex items-center justify-between"><span className="text-xs font-semibold text-slate-300">BTC / USD · 15m</span><span className="text-[10px] text-emerald-300">+2.41%</span></div>
            <CandleChart />
          </div>
          <div className="space-y-2">
            {["Evidence aligned", "Fresh final candle", "Review required"].map((item, index) => (
              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={item}>
                <div className="flex items-center gap-2"><span className={`h-1.5 w-1.5 rounded-full ${index === 2 ? "bg-amber-300" : "bg-teal-300"}`} /><span className="text-[10px] font-semibold text-slate-300">{item}</span></div>
                <div className="mt-2 h-1 rounded-full bg-white/10"><div className="h-1 rounded-full bg-teal-300/60" style={{ width: `${86 - index * 17}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
        <div className="border-t border-white/10 px-4 py-3 font-mono text-[10px] text-slate-500">Deterministic signal · grounded explanation · paper-only plan</div>
      </div>
    </div>
  );
}

function CandleChart() {
  const candles = [38, 52, 44, 65, 58, 76, 62, 84, 73, 91, 82, 100, 88, 110];
  return (
    <div className="relative flex h-40 items-end justify-between gap-1 overflow-hidden rounded-lg bg-[linear-gradient(rgba(255,255,255,.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.035)_1px,transparent_1px)] bg-[size:28px_28px] px-2 pb-3">
      <div className="absolute inset-x-0 top-[38%] border-t border-dashed border-teal-300/20" />
      {candles.map((height, index) => {
        const positive = index === 0 || height >= candles[index - 1];
        return <span className={`relative w-2 rounded-sm ${positive ? "bg-teal-300" : "bg-rose-400"} opacity-90 before:absolute before:left-1/2 before:top-[-9px] before:h-[calc(100%+18px)] before:w-px before:-translate-x-1/2 before:bg-current before:opacity-50`} key={`${height}-${index}`} style={{ height }} />;
      })}
    </div>
  );
}

function PreviewMetric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <div className="bg-[#080d17] p-4"><p className="font-mono text-[9px] uppercase tracking-[0.14em] text-slate-600">{label}</p><p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p></div>;
}

function SectionHeading({ eyebrow, title, description, centered = false }: { eyebrow: string; title: string; description: string; centered?: boolean }) {
  return <div className={centered ? "mx-auto max-w-3xl" : "max-w-3xl"}><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-teal-300">{eyebrow}</p><h2 className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">{title}</h2><p className="mt-5 text-lg leading-8 text-slate-400">{description}</p></div>;
}

function BrandMark() {
  return <span className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-teal-300/30 bg-teal-300/10 text-teal-200"><svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24"><path d="M3 17h4l3-9 4 6 3-9h4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" /></svg></span>;
}

function ArrowIcon(): ReactNode {
  return <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" /></svg>;
}
