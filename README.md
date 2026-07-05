# 🔬 Deep Research Agent

An AI agent built with [Pydantic AI](https://ai.pydantic.dev/) that takes either
a **plain question** or a **stock ticker** (e.g. `NVDA`) and produces a
**structured, cited report** from multi-step web research using
[DuckDuckGo](https://duckduckgo.com/). It uses OpenAI's **gpt-5-mini** model and a
[Gradio](https://www.gradio.app/) chat interface as the frontend.

## How it works

The agent runs a small research pipeline, and you watch each step happen live:

1. **Intent & entity detection** — is the input a ticker or a general query?
   If it's a ticker, it's resolved to a company and context
   (e.g. `NVDA` → *NVIDIA Corporation — semiconductors, GPUs, AI*).
2. **Discovery search** — one DuckDuckGo search on the input.
3. **Research angle planning** — 3–4 focused, non-overlapping follow-up queries
   are generated from the discovery snippets. For a company these lean toward
   *SWOT analysis*, *last 12 months stock performance*, *competition & market
   positioning*, and *latest quarterly results & forward guidance*.
4. **Deep research** — one DuckDuckGo search per angle.
5. **Report synthesis** — all findings are written up as a structured Markdown
   report with inline `[n]` citations and a Sources list.

## What's inside

| File               | Purpose                                                   |
| ------------------ | --------------------------------------------------------- |
| `agent.py`         | The research pipeline (agents + DuckDuckGo + orchestration). |
| `app.py`           | The Gradio chat frontend (streams the pipeline live).     |
| `requirements.txt` | Python dependencies.                                      |
| `.env`             | Your OpenAI API key (keep it secret).                     |

## Setup (step by step)

### 1. Install Python
Make sure you have **Python 3.10 or newer** installed:

```powershell
python --version
```

### 2. (Recommended) Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install the dependencies

```powershell
pip install -r requirements.txt
```

### 4. Add your OpenAI API key
Open the `.env` file and replace the placeholder with your real key:

```
OPENAI_API_KEY=sk-...your-key...
```

You can get a key at https://platform.openai.com/api-keys

### 5. Run the app

```powershell
python app.py
```

Gradio will print a local URL (usually http://127.0.0.1:7860). Open it in your
browser, then type a ticker like `NVDA` or a question and watch the research run.

## Test just the agent (optional)
Without the frontend, you can run the pipeline directly from the terminal:

```powershell
python agent.py NVDA
python agent.py "Is intermittent fasting actually healthy?"
```

## Notes
- Web research uses DuckDuckGo via the `ddgs` package — no search API key needed.
- To change how angles or the report are written, edit the `system_prompt` of the
  relevant agent (`intent_agent`, `angle_agent`, `report_agent`) in `agent.py`.
- To use a different model, change `MODEL` in `agent.py`.
- The report is grounded only in the search snippets the agent collected, and it
  cites its sources — but always sanity-check anything used for real decisions.
