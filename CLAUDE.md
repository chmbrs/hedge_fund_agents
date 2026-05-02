# CLAUDE.md

## Project Intent

This repository is a lean fork of TradingAgents for thesis-driven investment
consults. The user does not want a source-ingestion product. They want Claude to
curate noisy trusted-source summaries into a strong markdown thesis, then have
TradingAgents stress-test that thesis with a structured bull/bear/risk debate.

The core design rule:

> Claude-curated thesis in, structured debate out.

Do not reintroduce a separate source corpus, ingestion CLI, or retrieval layer
unless the user explicitly changes direction.

## Current Architecture

- `consult.py` is the primary entry point.
- `theses/*.md` are the maintained decision inputs.
- `tradingagents/default_config.py` sets local Ollama defaults.
- `tradingagents/graph/propagation.py` adds `user_thesis` to graph state.
- `tradingagents/agents/utils/agent_states.py` declares `user_thesis`.
- `tradingagents/agents/researchers/bull_researcher.py` steelmans the thesis.
- `tradingagents/agents/researchers/bear_researcher.py` red-teams the thesis.
- `tradingagents/agents/managers/portfolio_manager.py` decides whether the
  debate strengthens, weakens, or invalidates the thesis.

This repo currently contains local overlays and depends on the installed
`tradingagents` package for upstream graph pieces that have not yet been copied
or rewritten into the fork.

## Product Direction

Keep the fork narrow:

- Favor local-first Ollama execution.
- Keep only the parts that support thesis stress-testing.
- Prefer markdown thesis files over databases, corpora, or ingestion scripts.
- Let Claude do the high-context source distillation outside the repo.
- Preserve reports as outputs, not as maintained source material.

## Thesis Workflow

The expected human loop:

1. The user pastes Gemini/YouTube summaries into Claude over time.
2. Claude extracts ticker mentions, positions, dates, price levels, time
   horizons, disagreements, and changes from prior source views.
3. At consult time, Claude writes or updates `theses/<ticker>.md`.
4. The user runs `python consult.py --ticker <TICKER> --thesis theses/<ticker>.md`.
5. The final portfolio-manager output is used as a decision aid.

Good thesis files include:

- Position context and sizing.
- Current conviction.
- Trusted-source convergence and divergence.
- The exact decision question.
- Explicit out-of-scope guardrails.
- Hard personal or portfolio constraints.

## Cleanup Guidance

Stale direction to avoid:

- `ingest.py`
- `sources/`
- source frontmatter schemas
- commands like `python ingest.py list`
- language/provider expansion that makes the fork broad again

When editing docs, keep the README framed around the lean thesis workflow, not
the upstream full TradingAgents platform.

When editing code, avoid broad refactors unless they directly simplify the
consult path. The next likely useful cleanup is to replace the remaining
installed-package dependency with a small local graph that contains only the
agents this workflow actually uses.
