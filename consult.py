#!/usr/bin/env python3
"""
consult.py — Hedge-fund consult wrapper with thesis injection.

Runs TradingAgents on a single ticker with an external thesis file injected
into the bull/bear/portfolio-manager prompts, so the debate stress-tests
your existing position rather than generating arguments from a blank slate.

Usage:
    python consult.py --ticker SILJ --thesis theses/silj.md
    python consult.py --ticker SILJ --thesis theses/silj.md --date 2026-05-01

Output:
    Reports written to ~/.tradingagents/logs/<TICKER>_<TIMESTAMP>/
    Same folder structure as a normal run: 1_analysts/ 2_research/ etc.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import types
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent


def _install_portfolio_manager_stub() -> None:
    """Avoid circular import when loading the real portfolio manager from this repo.

    ``portfolio_manager.py`` imports ``tradingagents.agents.schemas``, which loads
    ``tradingagents.agents`` before ``portfolio_manager`` has finished executing.
    A temporary stub satisfies ``agents/__init__.py``; we replace it right after
    ``import tradingagents.graph``.
    """
    stub = types.ModuleType("tradingagents.agents.managers.portfolio_manager")

    def create_portfolio_manager(_llm):
        def portfolio_manager_node(_state):
            return {}

        return portfolio_manager_node

    stub.create_portfolio_manager = create_portfolio_manager
    sys.modules["tradingagents.agents.managers.portfolio_manager"] = stub


def _preload_local_thesis_modules() -> None:
    """Register repo-local thesis patches before ``import tradingagents.graph``.

    The wheel/site-packages build omits ``user_thesis`` on ``AgentState`` and uses
    stock bull/bear prompts. LangGraph drops state keys that are not part of the
    schema, so we inject patched submodules ahead of graph import. Portfolio manager
    is loaded separately (see :func:`_swap_real_portfolio_manager`).
    """
    ta_root = _REPO_ROOT / "tradingagents"
    pairs = [
        ("tradingagents.agents.utils.structured", ta_root / "agents/utils/structured.py"),
        ("tradingagents.agents.utils.agent_states", ta_root / "agents/utils/agent_states.py"),
        ("tradingagents.agents.researchers.bull_researcher", ta_root / "agents/researchers/bull_researcher.py"),
        ("tradingagents.agents.researchers.bear_researcher", ta_root / "agents/researchers/bear_researcher.py"),
        ("tradingagents.graph.propagation", ta_root / "graph/propagation.py"),
    ]
    for modname, path in pairs:
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(modname, path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)


def _swap_real_portfolio_manager() -> None:
    """Replace the stub with the repo ``portfolio_manager`` and patch ``graph.setup``."""
    path = _REPO_ROOT / "tradingagents/agents/managers/portfolio_manager.py"
    if not path.is_file():
        return
    spec = importlib.util.spec_from_file_location(
        "tradingagents.agents.managers.portfolio_manager", path
    )
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tradingagents.agents.managers.portfolio_manager"] = mod
    spec.loader.exec_module(mod)
    import tradingagents.graph.setup as graph_setup

    graph_setup.create_portfolio_manager = mod.create_portfolio_manager


_install_portfolio_manager_stub()
_preload_local_thesis_modules()

from tradingagents.graph.trading_graph import TradingAgentsGraph

_swap_real_portfolio_manager()


def _merged_default_config() -> dict:
    """Use the installed package defaults, overlaid by repo `tradingagents/default_config.py`.

    `pip install tradingagents` leaves site-packages on sys.path ahead of this repo,
    so a plain `from tradingagents.default_config import DEFAULT_CONFIG` ignores your
    local Ollama settings. Loading the repo file explicitly matches the README workflow.
    """
    from tradingagents.default_config import DEFAULT_CONFIG as _pkg_defaults

    cfg: dict = dict(_pkg_defaults)
    local_path = _REPO_ROOT / "tradingagents" / "default_config.py"
    if not local_path.is_file():
        return cfg
    spec = importlib.util.spec_from_file_location(
        "_ta_local_default_config", local_path
    )
    if spec is None or spec.loader is None:
        return cfg
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    overlay = getattr(mod, "DEFAULT_CONFIG", None)
    if isinstance(overlay, dict):
        cfg.update(overlay)
    return cfg


DEFAULT_CONFIG = _merged_default_config()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g. SILJ)")
    parser.add_argument(
        "--thesis",
        type=Path,
        required=True,
        help="Path to a markdown file containing the existing thesis to stress-test.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Trade date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Stream node-by-node trace to stdout while the graph runs.",
    )
    args = parser.parse_args()

    if not args.thesis.exists():
        print(f"ERROR: thesis file not found: {args.thesis}", file=sys.stderr)
        return 1

    user_thesis = args.thesis.read_text(encoding="utf-8").strip()
    if not user_thesis:
        print(f"ERROR: thesis file is empty: {args.thesis}", file=sys.stderr)
        return 1

    print("=" * 70)
    print(f"Hedge-fund consult: {args.ticker} on {args.date}")
    print(f"Thesis source: {args.thesis} ({len(user_thesis)} chars)")
    print(f"Backend: {DEFAULT_CONFIG['llm_provider']} / {DEFAULT_CONFIG['deep_think_llm']}")
    print(f"Debate rounds: {DEFAULT_CONFIG['max_debate_rounds']}")
    print("=" * 70)

    # Build the graph
    ta = TradingAgentsGraph(debug=args.debug, config=DEFAULT_CONFIG)

    # Bind thesis into initial state (repo ``propagation.py`` adds ``user_thesis``).
    original_create = ta.propagator.create_initial_state

    def _create_with_thesis(company_name, trade_date, past_context=""):
        try:
            return original_create(
                company_name,
                trade_date,
                past_context=past_context,
                user_thesis=user_thesis,
            )
        except TypeError:
            state = original_create(company_name, trade_date, past_context=past_context)
            state["user_thesis"] = user_thesis
            return state

    ta.propagator.create_initial_state = _create_with_thesis

    # Run
    final_state, decision = ta.propagate(args.ticker, args.date)

    print("\n" + "=" * 70)
    print("FINAL DECISION")
    print("=" * 70)
    print(decision if isinstance(decision, str) else final_state.get("final_trade_decision", ""))
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
