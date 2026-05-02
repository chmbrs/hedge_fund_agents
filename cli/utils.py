import questionary
import re
import time
import typer
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from cli.models import AnalystType
try:
    from tradingagents.llm_clients.model_catalog import get_model_options
except Exception:
    # Local fallback used when model_catalog is unavailable in the workspace.
    _FALLBACK_MODEL_OPTIONS = {
        "deepseek": {
            "quick": [
                ("DeepSeek Chat (v3)", "deepseek-chat"),
                ("DeepSeek V4 Flash", "deepseek-v4-flash"),
                ("DeepSeek V4 Pro", "deepseek-v4-pro"),
            ],
            "deep": [
                ("DeepSeek Reasoner", "deepseek-reasoner"),
                ("DeepSeek V4 Flash", "deepseek-v4-flash"),
                ("DeepSeek V4 Pro", "deepseek-v4-pro"),
            ],
        },
        "openai": {
            "quick": [("GPT-4o Mini", "gpt-4o-mini")],
            "deep": [("o4-mini", "o4-mini")],
        },
        "anthropic": {
            "quick": [("Claude Sonnet 4.6", "claude-sonnet-4-6")],
            "deep": [("Claude Sonnet 4.6", "claude-sonnet-4-6")],
        },
        "google": {
            "quick": [("Gemini 2.5 Flash", "gemini-2.5-flash")],
            "deep": [("Gemini 2.5 Pro", "gemini-2.5-pro")],
        },
        "qwen": {
            "quick": [("Qwen Plus", "qwen-plus")],
            "deep": [("Qwen Max", "qwen-max")],
        },
        "xai": {
            "quick": [("Grok 3 Mini", "grok-3-mini")],
            "deep": [("Grok 3 Beta", "grok-3-beta")],
        },
        "glm": {
            "quick": [("GLM-4-Flash", "glm-4-flash")],
            "deep": [("GLM-4-Plus", "glm-4-plus")],
        },
        "azure": {
            "quick": [],
            "deep": [],
        },
        "ollama": {
            "quick": [("qwen3:30b-a3b", "qwen3:30b-a3b")],
            "deep": [("qwen3:30b-a3b", "qwen3:30b-a3b")],
        },
    }

    def get_model_options(provider: str, mode: str):
        provider_options = _FALLBACK_MODEL_OPTIONS.get(provider.lower(), {})
        options = provider_options.get(mode.lower(), [])
        if provider.lower() == "ollama":
            return options
        return options + [("Custom model ID", "custom")]

console = Console()

TICKER_INPUT_EXAMPLES = "Examples: SPY, CNC.TO, 7203.T, 0700.HK"

ANALYST_ORDER = [
    ("Market Analyst", AnalystType.MARKET),
    ("Social Media Analyst", AnalystType.SOCIAL),
    ("News Analyst", AnalystType.NEWS),
    ("Fundamentals Analyst", AnalystType.FUNDAMENTALS),
]


def get_ticker() -> str:
    """Prompt the user to enter a ticker symbol."""
    ticker = questionary.text(
        f"Enter the exact ticker symbol to analyze ({TICKER_INPUT_EXAMPLES}):",
        validate=lambda x: len(x.strip()) > 0 or "Please enter a valid ticker symbol.",
        style=questionary.Style(
            [
                ("text", "fg:green"),
                ("highlighted", "noinherit"),
            ]
        ),
    ).ask()

    if not ticker:
        console.print("\n[red]No ticker symbol provided. Exiting...[/red]")
        exit(1)

    return normalize_ticker_symbol(ticker)


def normalize_ticker_symbol(ticker: str) -> str:
    """Normalize ticker input while preserving exchange suffixes."""
    return ticker.strip().upper()


def get_analysis_date() -> str:
    """Prompt the user to enter a date in YYYY-MM-DD format."""
    import re
    from datetime import datetime

    def validate_date(date_str: str) -> bool:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    date = questionary.text(
        "Enter the analysis date (YYYY-MM-DD):",
        validate=lambda x: validate_date(x.strip())
        or "Please enter a valid date in YYYY-MM-DD format.",
        style=questionary.Style(
            [
                ("text", "fg:green"),
                ("highlighted", "noinherit"),
            ]
        ),
    ).ask()

    if not date:
        console.print("\n[red]No date provided. Exiting...[/red]")
        exit(1)

    return date.strip()


def select_analysts() -> List[AnalystType]:
    """Select analysts using an interactive checkbox."""
    choices = questionary.checkbox(
        "Select Your [Analysts Team]:",
        choices=[
            questionary.Choice(display, value=value) for display, value in ANALYST_ORDER
        ],
        instruction="\n- Press Space to select/unselect analysts\n- Press 'a' to select/unselect all\n- Press Enter when done",
        validate=lambda x: len(x) > 0 or "You must select at least one analyst.",
        style=questionary.Style(
            [
                ("checkbox-selected", "fg:green"),
                ("selected", "fg:green noinherit"),
                ("highlighted", "noinherit"),
                ("pointer", "noinherit"),
            ]
        ),
    ).ask()

    if not choices:
        console.print("\n[red]No analysts selected. Exiting...[/red]")
        exit(1)

    return choices


def select_research_depth() -> int:
    """Select research depth using an interactive selection."""

    # Define research depth options with their corresponding values
    DEPTH_OPTIONS = [
        ("Shallow - Quick research, few debate and strategy discussion rounds", 1),
        ("Medium - Middle ground, moderate debate rounds and strategy discussion", 3),
        ("Deep - Comprehensive research, in depth debate and strategy discussion", 5),
    ]

    choice = questionary.select(
        "Select Your [Research Depth]:",
        choices=[
            questionary.Choice(display, value=value) for display, value in DEPTH_OPTIONS
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:yellow noinherit"),
                ("highlighted", "fg:yellow noinherit"),
                ("pointer", "fg:yellow noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]No research depth selected. Exiting...[/red]")
        exit(1)

    return choice


def _fetch_openrouter_models() -> List[Tuple[str, str]]:
    """Fetch available models from the OpenRouter API."""
    import requests
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        resp.raise_for_status()
        models = resp.json().get("data", [])
        return [(m.get("name") or m["id"], m["id"]) for m in models]
    except Exception as e:
        console.print(f"\n[yellow]Could not fetch OpenRouter models: {e}[/yellow]")
        return []


def _fetch_ollama_models() -> List[Tuple[str, str]]:
    """Query local Ollama daemon for installed models. Returns [] on any error."""
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        models_sorted = sorted(models, key=lambda m: m.get("size", 0), reverse=True)
        result = []
        for m in models_sorted:
            name = m.get("name", "")
            if not name:
                continue
            size_bytes = m.get("size", 0)
            display = f"{name} ({size_bytes / (1024**3):.1f}GB)" if size_bytes else name
            result.append((display, name))
        return result
    except Exception:
        return []


def select_openrouter_model() -> str:
    """Select an OpenRouter model from the newest available, or enter a custom ID."""
    models = _fetch_openrouter_models()

    choices = [questionary.Choice(name, value=mid) for name, mid in models[:5]]
    choices.append(questionary.Choice("Custom model ID", value="custom"))

    choice = questionary.select(
        "Select OpenRouter Model (latest available):",
        choices=choices,
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style([
            ("selected", "fg:magenta noinherit"),
            ("highlighted", "fg:magenta noinherit"),
            ("pointer", "fg:magenta noinherit"),
        ]),
    ).ask()

    if choice is None or choice == "custom":
        return questionary.text(
            "Enter OpenRouter model ID (e.g. google/gemma-4-26b-a4b-it):",
            validate=lambda x: len(x.strip()) > 0 or "Please enter a model ID.",
        ).ask().strip()

    return choice


def _prompt_custom_model_id() -> str:
    """Prompt user to type a custom model ID."""
    return questionary.text(
        "Enter model ID:",
        validate=lambda x: len(x.strip()) > 0 or "Please enter a model ID.",
    ).ask().strip()


def _select_model(provider: str, mode: str) -> str:
    """Select a model for the given provider and mode (quick/deep)."""
    if provider.lower() == "openrouter":
        return select_openrouter_model()

    if provider.lower() == "azure":
        return questionary.text(
            f"Enter Azure deployment name ({mode}-thinking):",
            validate=lambda x: len(x.strip()) > 0 or "Please enter a deployment name.",
        ).ask().strip()

    if provider.lower() == "ollama":
        live = _fetch_ollama_models()
        if live:
            choices = [questionary.Choice(d, value=v) for d, v in live]
        else:
            console.print(
                "[yellow]Ollama daemon not reachable on localhost:11434. "
                "Using static catalog.[/yellow]"
            )
            choices = [
                questionary.Choice(d, value=v)
                for d, v in get_model_options("ollama", mode)
            ]
        choices.append(questionary.Choice("Custom model ID", value="custom"))

        choice = questionary.select(
            f"Select Your [{mode.title()}-Thinking LLM Engine]:",
            choices=choices,
            instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
            style=questionary.Style([
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]),
        ).ask()

        if choice is None:
            console.print(f"\n[red]No {mode} thinking llm engine selected. Exiting...[/red]")
            exit(1)
        if choice == "custom":
            return _prompt_custom_model_id()
        return choice

    choice = questionary.select(
        f"Select Your [{mode.title()}-Thinking LLM Engine]:",
        choices=[
            questionary.Choice(display, value=value)
            for display, value in get_model_options(provider, mode)
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print(f"\n[red]No {mode} thinking llm engine selected. Exiting...[/red]")
        exit(1)

    if choice == "custom":
        return _prompt_custom_model_id()

    return choice


def select_shallow_thinking_agent(provider) -> str:
    """Select shallow thinking llm engine using an interactive selection."""
    return _select_model(provider, "quick")


def select_deep_thinking_agent(provider) -> str:
    """Select deep thinking llm engine using an interactive selection."""
    return _select_model(provider, "deep")

def select_llm_provider() -> tuple[str, str | None]:
    """Select the LLM provider and its API endpoint."""
    # (display_name, provider_key, base_url)
    PROVIDERS = [
        ("Ollama", "ollama", "http://localhost:11434/v1"),
        ("DeepSeek", "deepseek", "https://api.deepseek.com"),
        ("OpenAI", "openai", "https://api.openai.com/v1"),
        ("Google", "google", None),
        ("Anthropic", "anthropic", "https://api.anthropic.com/"),
        ("xAI", "xai", "https://api.x.ai/v1"),
        ("Qwen", "qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        ("GLM", "glm", "https://open.bigmodel.cn/api/paas/v4/"),
        ("OpenRouter", "openrouter", "https://openrouter.ai/api/v1"),
        ("Azure OpenAI", "azure", None),
    ]

    choice = questionary.select(
        "Select your LLM Provider:",
        choices=[
            questionary.Choice(display, value=(provider_key, url))
            for display, provider_key, url in PROVIDERS
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()
    
    if choice is None:
        console.print("\n[red]No LLM provider selected. Exiting...[/red]")
        exit(1)

    provider, url = choice
    return provider, url


def ask_openai_reasoning_effort() -> str:
    """Ask for OpenAI reasoning effort level."""
    choices = [
        questionary.Choice("Medium (Default)", "medium"),
        questionary.Choice("High (More thorough)", "high"),
        questionary.Choice("Low (Faster)", "low"),
    ]
    return questionary.select(
        "Select Reasoning Effort:",
        choices=choices,
        style=questionary.Style([
            ("selected", "fg:cyan noinherit"),
            ("highlighted", "fg:cyan noinherit"),
            ("pointer", "fg:cyan noinherit"),
        ]),
    ).ask()


def ask_anthropic_effort() -> str | None:
    """Ask for Anthropic effort level.

    Controls token usage and response thoroughness on Claude 4.5+ and 4.6 models.
    """
    return questionary.select(
        "Select Effort Level:",
        choices=[
            questionary.Choice("High (recommended)", "high"),
            questionary.Choice("Medium (balanced)", "medium"),
            questionary.Choice("Low (faster, cheaper)", "low"),
        ],
        style=questionary.Style([
            ("selected", "fg:cyan noinherit"),
            ("highlighted", "fg:cyan noinherit"),
            ("pointer", "fg:cyan noinherit"),
        ]),
    ).ask()


def ask_gemini_thinking_config() -> str | None:
    """Ask for Gemini thinking configuration.

    Returns thinking_level: "high" or "minimal".
    Client maps to appropriate API param based on model series.
    """
    return questionary.select(
        "Select Thinking Mode:",
        choices=[
            questionary.Choice("Enable Thinking (recommended)", "high"),
            questionary.Choice("Minimal/Disable Thinking", "minimal"),
        ],
        style=questionary.Style([
            ("selected", "fg:green noinherit"),
            ("highlighted", "fg:green noinherit"),
            ("pointer", "fg:green noinherit"),
        ]),
    ).ask()


def ask_output_language() -> str:
    """Ask for report output language."""
    choice = questionary.select(
        "Select Output Language:",
        choices=[
            questionary.Choice("English (default)", "English"),
            questionary.Choice("Spanish (Español)", "Spanish"),
            questionary.Choice("Portuguese (Português)", "Portuguese"),
            questionary.Choice("Custom language", "custom"),
        ],
        style=questionary.Style([
            ("selected", "fg:yellow noinherit"),
            ("highlighted", "fg:yellow noinherit"),
            ("pointer", "fg:yellow noinherit"),
        ]),
    ).ask()

    if choice == "custom":
        return questionary.text(
            "Enter language name (e.g. Turkish, Vietnamese, Thai, Indonesian):",
            validate=lambda x: len(x.strip()) > 0 or "Please enter a language name.",
        ).ask().strip()

    return choice


# ---------------------------------------------------------------------------
# Thesis helpers
# ---------------------------------------------------------------------------

THESIS_TEMPLATE = """\
# Thesis: {TICKER}

**Date of thesis:** {DATE}
**Position size:** ~$
**Holding action stance:** HOLDING / ADDING / TRIMMING / WATCHING

## Position Context
[Portfolio profile, how this asset fits, allocation context. E.g. hard assets bucket, long-term structural hold.]

## Current Conviction
**[Bullish/Bearish, structural/tactical — qualifier]**

Key thesis drivers:
- [Driver 1]
- [Driver 2]

## Source Convergence (this is why this ticker triggered a hedge-fund consult)
[Trusted sources and their positions, where they agree/diverge. E.g. 3 of 4 sources bullish, one flags near-term retracement.]

## What Triggered This Consult
[Specific question — numbered list:]
1. [Question 1]
2. [Question 2]
3. [Question 3]

## What I Am NOT Asking
- [Explicit out-of-scope guardrail 1]
- [Explicit out-of-scope guardrail 2]

## Hard Constraints
- [Time horizon]
- [Sizing constraints]
- [Operational constraints]
"""


def list_available_theses(theses_dir: Path) -> list[Path]:
    """Return .md files in theses_dir sorted by modification time, newest first."""
    if not theses_dir.exists():
        return []
    return sorted(theses_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def format_mtime(p: Path) -> str:
    """Return a human-readable relative modification time string for a file."""
    delta = time.time() - p.stat().st_mtime
    if delta < 60:
        return "just now"
    elif delta < 3600:
        return f"{int(delta // 60)}m ago"
    elif delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


def select_thesis_interactive(theses_dir: Path) -> Optional[Path]:
    """Show picker: existing theses | write new | skip. Returns Path or None."""
    existing = list_available_theses(theses_dir)
    choices = []
    for p in existing:
        size_kb = p.stat().st_size / 1024
        label = f"{p.stem.upper()} — {p.name} ({size_kb:.1f}KB, {format_mtime(p)})"
        choices.append(questionary.Choice(label, value=p))
    choices.append(questionary.Choice("Write new thesis (wizard)", value="__new__"))
    choices.append(questionary.Choice("Skip — run without thesis", value=None))

    selected = questionary.select(
        "Select a thesis, write a new one, or skip:",
        choices=choices,
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style([
            ("selected", "fg:magenta noinherit"),
            ("highlighted", "fg:magenta noinherit"),
            ("pointer", "fg:magenta noinherit"),
        ]),
    ).ask()

    if selected == "__new__":
        return run_thesis_wizard(theses_dir)
    return selected  # Path or None


def run_thesis_wizard(theses_dir: Path, ticker_hint: Optional[str] = None) -> Path:
    """Collect ticker, open $EDITOR with silj.md-style template, preview, and save.

    Returns the path to the saved thesis file.
    """
    import datetime as _dt

    ticker_raw = questionary.text(
        "Ticker symbol (becomes filename, e.g. SILJ):",
        default=ticker_hint or "",
        validate=lambda x: len(x.strip()) > 0 or "Please enter a ticker symbol.",
        style=questionary.Style([
            ("text", "fg:green"),
            ("highlighted", "noinherit"),
        ]),
    ).ask()

    if not ticker_raw:
        console.print("\n[red]No ticker provided. Exiting...[/red]")
        exit(1)

    ticker = ticker_raw.strip().upper()
    safe_ticker = re.sub(r"[^\w.\-]", "_", ticker)
    save_path = theses_dir / f"{safe_ticker}.md"
    today = _dt.date.today().isoformat()

    if save_path.exists():
        overwrite = questionary.confirm(
            f"{save_path} already exists. Overwrite?", default=False
        ).ask()
        if not overwrite:
            console.print("[yellow]Wizard cancelled.[/yellow]")
            exit(0)

    prefilled = THESIS_TEMPLATE.format(TICKER=ticker, DATE=today)
    edited = typer.edit(prefilled, extension=".md")

    if not edited or not edited.strip():
        console.print("\n[red]Editor closed without content. Exiting...[/red]")
        exit(1)

    content = edited.strip()

    console.print()
    console.print(
        Panel(
            Markdown(content),
            title=f"Thesis Preview — {ticker}",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

    theses_dir.mkdir(parents=True, exist_ok=True)
    save_path.write_text(content, encoding="utf-8")
    console.print(f"[green]✓ Thesis saved to:[/green] {save_path}")
    return save_path
