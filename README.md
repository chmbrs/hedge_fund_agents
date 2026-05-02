# TradingAgents Lean Thesis Fork

This fork keeps the useful part of TradingAgents: a structured investment
debate that stress-tests a position before you deploy capital.

The old direction was to build a source corpus and ingest YouTube summaries into
the repo. That is intentionally removed. The better workflow is:

1. You collect source summaries in conversation with Claude.
2. Claude curates those scattered summaries into one high-signal thesis file.
3. `consult.py` injects that thesis into TradingAgents.
4. Bull, bear, trader, risk, and portfolio-manager agents debate the thesis.
5. The final decision says whether the debate strengthens, weakens, or
   invalidates the position.

In other words: the thesis is the source of truth. There is no separate
`sources/` corpus to maintain.

## Why This Fork Exists

The original TradingAgents architecture is broad: datafeeds, several analyst
roles, multiple hosted LLM providers, memory, checkpoints, and a full CLI. This
fork is becoming much narrower:

- Run local-first on Ollama.
- Keep the multi-agent debate structure.
- Inject a curated thesis instead of asking local models to discover the whole
  context from scratch.
- Avoid a manual ingestion database for trusted analyst content.
- Use the consult only when a decision deserves a red-team.

The highest-value artifact is the markdown file in `theses/`. It should contain
your position context, trusted-source convergence or disagreement, the decision
question, and the boundaries of what the consult should not answer.

## Current Workflow

Create or update a thesis:

```bash
$EDITOR theses/silj.md
```

Run a consult:

```bash
python consult.py --ticker SILJ --thesis theses/silj.md
```

Optionally pin the trade date:

```bash
python consult.py --ticker SILJ --thesis theses/silj.md --date 2026-05-01
```

Use `--debug` when you want the graph stream printed node by node:

```bash
python consult.py --ticker SILJ --thesis theses/silj.md --debug
```

## Thesis Format

A thesis file is plain markdown. The structure in `theses/silj.md` is the
preferred shape:

- Position context: how this ticker fits your portfolio and time horizon.
- Current conviction: directional stance plus tactical nuance.
- Key drivers: the actual reasons you hold or are watching the asset.
- Source convergence: where your trusted humans agree or diverge.
- Consult trigger: the concrete decision question.
- Out-of-scope guardrails: what the agents should not waste time on.
- Hard constraints: sizing, cadence, tax, liquidity, or personal rules.

The thesis can include Claude-curated summaries from Pablo, VirtualBacon, Bravos
Research, CryptoMason, or any other trusted source, but those summaries should
be distilled into the thesis itself. Do not add them to a separate corpus.

## Architecture

`consult.py` is the runtime entry point. It loads the installed TradingAgents
graph, preloads this repo's thesis-aware modules, and monkey-patches initial
state creation so `user_thesis` reaches the graph.

Important local overlays:

| Path | Role |
|---|---|
| `consult.py` | CLI wrapper that injects a thesis into a TradingAgents run. |
| `theses/` | Curated thesis inputs. This is the maintained knowledge layer. |
| `tradingagents/default_config.py` | Local defaults, currently Ollama + `qwen3:30b-a3b`. |
| `tradingagents/graph/propagation.py` | Adds `user_thesis` to initial state. |
| `tradingagents/agents/utils/agent_states.py` | Keeps `user_thesis` in graph state. |
| `tradingagents/agents/researchers/bull_researcher.py` | Steelmans the thesis using available reports. |
| `tradingagents/agents/researchers/bear_researcher.py` | Red-teams the thesis using available reports. |
| `tradingagents/agents/managers/portfolio_manager.py` | Final decision explicitly evaluates the thesis. |

Many upstream files have been removed while this fork is being made leaner.
That is expected. The current code still relies on the installed `tradingagents`
package for the parts of the graph that have not yet been replaced locally.

## When To Run A Consult

Do not run this on every ticker. Trigger it when one of these is true:

- Source divergence: trusted sources disagree on near-term direction or timing.
- Source silence: no trusted source has covered the position recently and a
  deployment decision is queued.
- Binary event: a catalyst is close and you need a structured red-team.
- Position change: you are considering adding, trimming, or invalidating a hold.

Default state: keep the thesis updated, but skip the consult.

## What Good Output Looks Like

Read these first:

- `2_research/bull.md`
- `2_research/bear.md`
- `5_portfolio/decision.md`

Pass criteria:

- Bull and bear engage the specific thesis, not generic macro filler.
- Bear identifies real invalidation conditions.
- Bull separates structural conviction from tactical entry timing.
- The portfolio manager says whether the thesis is strengthened, weakened, or
  invalidated.
- Claims stay grounded in the thesis and available analyst reports.

Fail criteria:

- Invented news, dates, prices, or geopolitical events.
- Generic arguments that ignore the thesis.
- A final `Hold` or `Buy` with no explicit link back to the thesis.

## Local Model Setup

The default config expects Ollama:

```bash
ollama list | grep qwen3
ollama run qwen3:30b-a3b "Give me a one-line answer: what is SILJ?"
```

If that model is too slow, change both `deep_think_llm` and `quick_think_llm` in
`tradingagents/default_config.py` to a smaller local model.

## Outputs

Reports are written by the underlying TradingAgents graph. Existing local runs
in this repo show the intended shape:

```text
reports/<TICKER>_<TIMESTAMP>/
├── thesis.md
├── 1_analysts/
├── 2_research/
├── 3_trading/
├── 4_risk/
├── 5_portfolio/
└── complete_report.md
```

The final decision in `5_portfolio/decision.md` is the main artifact.

## Removed Direction

There is no longer an `ingest.py` flow and no maintained `sources/` directory.
YouTube/Gemini summaries should be pasted into Claude conversations, distilled
there, and promoted into a thesis only when they matter for a decision.
