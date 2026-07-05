"""Gradio frontend for the Deep Research Agent.

Streams the research pipeline live: you see intent detection, the discovery
search, the planned angles and each per-angle search happen in real time, then
the finished structured report is appended below the trace.
"""

import gradio as gr

from agent import deep_research


def respond(message: str, history: list):
    """Gradio streaming callback.

    `deep_research` is a generator that yields a growing Markdown string, so we
    just re-yield each step. Gradio replaces the message with each new value.
    """
    if not message or not message.strip():
        yield "Please type a question or a stock ticker (e.g. `NVDA`)."
        return
    for partial in deep_research(message):
        yield partial


demo = gr.ChatInterface(
    fn=respond,
    title="🔬 Deep Research Agent",
    description=(
        "Ask a question or enter a stock ticker (e.g. **NVDA**). The agent runs "
        "multi-step DuckDuckGo research and returns a structured, cited report. "
        "Powered by Pydantic AI + OpenAI gpt-5-mini."
    ),
    examples=[
        "NVDA",
        "AAPL",
        "Is intermittent fasting actually healthy?",
        "State of solid-state batteries in 2026",
    ],
)


if __name__ == "__main__":
    demo.launch()
