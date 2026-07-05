"""Deep Research Agent built with Pydantic AI + DuckDuckGo.

Give it a plain question ("Is intermittent fasting healthy?") or a stock ticker
("NVDA") and it runs a small multi-step research pipeline:

    1. Intent & entity detection  -> ticker vs. general query (resolve company).
    2. Initial discovery search    -> one DuckDuckGo search on the input.
    3. Research angle planning     -> 3-4 focused sub-queries from the snippets.
    4. Deep research               -> one DuckDuckGo search per angle.
    5. Report synthesis            -> a structured, cited Markdown report.

The heavy lifting is done by OpenAI's gpt-5-mini through Pydantic AI. Every step
is a small, testable function, and `deep_research` streams progress so the Gradio
frontend (app.py) can show the pipeline working live.
"""

from __future__ import annotations

from typing import Iterator

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# `ddgs` is the current package; fall back to the old name just in case.
try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover - legacy fallback
    from duckduckgo_search import DDGS

# Load OPENAI_API_KEY (and anything else) from the .env file.
load_dotenv()

MODEL = "openai:gpt-5-mini"

# Keep result counts modest so we don't blow up the prompt (and token cost).
DISCOVERY_RESULTS = 6
ANGLE_RESULTS = 5


# --------------------------------------------------------------------------- #
# Structured outputs (what we ask the model to return)
# --------------------------------------------------------------------------- #
class Intent(BaseModel):
    """Result of intent & entity detection on the user's input."""

    is_ticker: bool = Field(
        description="True if the input is (or clearly refers to) a stock ticker."
    )
    ticker: str | None = Field(
        default=None, description="The resolved ticker symbol, e.g. 'NVDA'."
    )
    company_name: str | None = Field(
        default=None, description="Full company name, e.g. 'NVIDIA Corporation'."
    )
    context: str | None = Field(
        default=None,
        description="Short context for a ticker, e.g. 'semiconductors, GPUs, AI'.",
    )
    search_query: str = Field(
        description="The best plain-text query to search the web for this input."
    )
    subject: str = Field(
        description="A concise human-readable label for the report title."
    )


class ResearchAngles(BaseModel):
    """A small set of focused follow-up searches to run."""

    angles: list[str] = Field(
        min_length=3,
        max_length=4,
        description=(
            "3-4 web-search-ready queries, each covering a different angle of the "
            "topic. For a company include the company name in every query."
        ),
    )


# --------------------------------------------------------------------------- #
# Agents (one small agent per reasoning step)
# --------------------------------------------------------------------------- #
intent_agent = Agent(
    MODEL,
    output_type=Intent,
    system_prompt=(
        "You classify a user's research request. Decide whether the input is a "
        "stock ticker (e.g. NVDA, AAPL, TSLA) or a general question/topic. "
        "If it is a ticker, resolve the ticker symbol, the full company name and a "
        "short context (sector, products, themes). Always produce a good plain-text "
        "web search query and a short subject label for the report title."
    ),
)

angle_agent = Agent(
    MODEL,
    output_type=ResearchAngles,
    system_prompt=(
        "You plan web research. Given a topic and snippets from an initial search, "
        "propose 3-4 distinct, high-value research angles as ready-to-run search "
        "queries. Angles must not overlap and should cover the important dimensions "
        "of the topic.\n"
        "For a company/ticker, prefer angles like: 'SWOT analysis', 'last 12 months "
        "stock performance', 'competition and market positioning', and 'latest "
        "quarterly results and forward guidance'. Include the company name in every "
        "query and add the current year when it helps freshness."
    ),
)

report_agent = Agent(
    MODEL,
    system_prompt=(
        "You are a research analyst. Using ONLY the search findings provided, write "
        "a clear, well-structured Markdown report. Rules:\n"
        "- Open with a one-paragraph executive summary.\n"
        "- Use a '## ' section per research angle, in a logical order.\n"
        "- Be specific: pull concrete facts, numbers and dates from the snippets.\n"
        "- Cite sources inline using [n] that map to the numbered Sources list you "
        "are given, and end with a '## Sources' section listing them.\n"
        "- If the findings are thin or conflicting, say so plainly. Never invent "
        "facts, figures or sources that are not in the findings.\n"
        "- Only when researching a company/ticker, add a short snapshot (name, "
        "ticker, sector) at the top. For general topics, do NOT include a snapshot."
    ),
)


# --------------------------------------------------------------------------- #
# Web search helpers
# --------------------------------------------------------------------------- #
def web_search(query: str, max_results: int) -> list[dict]:
    """Run one DuckDuckGo text search and return a list of result dicts.

    Each dict has 'title', 'href' and 'body'. Failures return an empty list so a
    single bad search never crashes the whole pipeline.
    """
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as exc:  # network hiccup, rate limit, etc.
        print(f"[web_search] '{query}' failed: {exc}")
        return []


def _format_results(results: list[dict]) -> str:
    """Turn raw results into compact text for a model prompt."""
    lines = []
    for r in results:
        title = r.get("title", "").strip()
        body = r.get("body", "").strip()
        href = r.get("href", "").strip()
        lines.append(f"- {title}\n  {body}\n  ({href})")
    return "\n".join(lines) if lines else "(no results)"


# --------------------------------------------------------------------------- #
# Pipeline steps
# --------------------------------------------------------------------------- #
def detect_intent(user_input: str) -> Intent:
    """Step 1 — classify the input and resolve a company if it's a ticker."""
    return intent_agent.run_sync(user_input).output


def plan_angles(intent: Intent, discovery: list[dict]) -> ResearchAngles:
    """Step 3 — turn the topic + discovery snippets into 3-4 research angles."""
    prompt = (
        f"Subject: {intent.subject}\n"
        f"Is a company/ticker: {intent.is_ticker}\n"
        f"Company: {intent.company_name or '-'} ({intent.context or '-'})\n\n"
        f"Initial search results:\n{_format_results(discovery)}\n\n"
        "Propose the research angles."
    )
    return angle_agent.run_sync(prompt).output


def write_report(
    intent: Intent, findings: list[tuple[str, list[dict]]]
) -> str:
    """Step 5 — synthesize all findings into a cited Markdown report.

    `findings` is a list of (angle_label, results) tuples. We build one numbered
    Sources list across all angles so the model can cite with [n].
    """
    sources: list[str] = []
    blocks: list[str] = []
    for label, results in findings:
        lines = [f"### Angle: {label}"]
        for r in results:
            sources.append(f"{r.get('title', '').strip()} — {r.get('href', '').strip()}")
            n = len(sources)
            lines.append(
                f"[{n}] {r.get('title', '').strip()}\n"
                f"    {r.get('body', '').strip()}\n"
                f"    {r.get('href', '').strip()}"
            )
        blocks.append("\n".join(lines))

    numbered_sources = "\n".join(f"[{i + 1}] {s}" for i, s in enumerate(sources))
    prompt = (
        f"Subject: {intent.subject}\n"
        f"Company/ticker: {intent.company_name or '-'} "
        f"({intent.ticker or '-'}; {intent.context or '-'})\n\n"
        f"FINDINGS BY ANGLE:\n{chr(10).join(blocks)}\n\n"
        f"NUMBERED SOURCES (cite these as [n]):\n{numbered_sources}\n\n"
        "Write the full structured report now."
    )
    return report_agent.run_sync(prompt).output


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def deep_research(user_input: str) -> Iterator[str]:
    """Run the full pipeline, yielding a growing Markdown string as it goes.

    Yields progress updates (a live "research trace") and finally appends the
    complete report below it. Designed to be consumed by a streaming UI, but you
    can also just take the last value for the finished output.
    """
    if not user_input or not user_input.strip():
        yield "Please enter a question or a stock ticker (e.g. `NVDA`)."
        return

    user_input = user_input.strip()
    trace: list[str] = ["### 🔬 Research trace"]

    def step(msg: str) -> str:
        trace.append(msg)
        return "\n".join(trace)

    # Step 1 — intent & entity detection.
    yield step("**1. Detecting intent…**")
    intent = detect_intent(user_input)
    if intent.is_ticker:
        yield step(
            f"→ Ticker **{intent.ticker}** = {intent.company_name} "
            f"({intent.context})."
        )
    else:
        yield step(f"→ General query: *{intent.subject}*.")

    # Step 2 — initial discovery search.
    yield step(f"**2. Discovery search:** `{intent.search_query}`")
    discovery = web_search(intent.search_query, DISCOVERY_RESULTS)
    yield step(f"→ Found {len(discovery)} results.")

    # Step 3 — plan research angles.
    yield step("**3. Planning research angles…**")
    angles = plan_angles(intent, discovery).angles
    yield step("\n".join(f"→ Angle {i + 1}: `{a}`" for i, a in enumerate(angles)))

    # Step 4 — deep research, one search per angle.
    yield step("**4. Researching each angle…**")
    findings: list[tuple[str, list[dict]]] = [(intent.search_query, discovery)]
    for i, angle in enumerate(angles):
        results = web_search(angle, ANGLE_RESULTS)
        findings.append((angle, results))
        yield step(f"→ [{i + 1}/{len(angles)}] `{angle}` — {len(results)} results.")

    # Step 5 — synthesize the report.
    yield step("**5. Writing the report…**")
    report = write_report(intent, findings)

    yield "\n".join(trace) + "\n\n---\n\n" + report


def research_sync(user_input: str) -> str:
    """Convenience wrapper: run the pipeline and return only the final output."""
    output = ""
    for output in deep_research(user_input):
        pass
    return output


if __name__ == "__main__":
    # Quick manual test from the terminal: `python agent.py NVDA`
    import sys

    # Force UTF-8 so emoji/accents in the report never crash on Windows consoles
    # (which default to cp1252).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # pragma: no cover - very old Pythons
        pass

    query = " ".join(sys.argv[1:]) or "NVDA"
    print(research_sync(query))
