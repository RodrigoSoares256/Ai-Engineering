# 🔬 Deep Research Agent

An AI agent built with [Pydantic AI](https://ai.pydantic.dev/) that takes either
a **plain question** or a **stock ticker** (e.g. `NVDA`) and produces a
**structured, cited report** from multi-step web research using
[DuckDuckGo](https://duckduckgo.com/). It uses OpenAI's **gpt-5-mini** model and a
[Gradio](https://www.gradio.app/) chat interface as the frontend.

> Repo: https://github.com/RodrigoSoares256/Ai-Engineering

## How it works

The agent runs a small research pipeline, and you watch each step happen live in
the chat:

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

```
                      ┌─────────────────────────────────────────────┐
  "NVDA"  ──▶ intent  │ 1. detect_intent()   → ticker? company? query│
  or a       agent    └─────────────────────────────────────────────┘
  question                         │
                                   ▼
                       2. web_search()  ── DuckDuckGo discovery search
                                   │
                                   ▼
                       3. plan_angles()  ── 3–4 research angles (angle agent)
                                   │
                                   ▼
                       4. web_search() × N  ── one search per angle
                                   │
                                   ▼
                       5. write_report()  ── cited Markdown report (report agent)
```

Under the hood there are three small single-purpose Pydantic AI agents in
`agent.py` — `intent_agent`, `angle_agent`, and `report_agent` — orchestrated by
`deep_research()`, which streams progress and then appends the finished report.

## Project structure

| File               | Purpose                                                      |
| ------------------ | ------------------------------------------------------------ |
| `agent.py`         | The research pipeline: 3 agents, DuckDuckGo search, orchestration. |
| `app.py`           | The Gradio chat frontend (streams the pipeline live).        |
| `requirements.txt` | Python dependencies.                                         |
| `.env.example`     | Template for your API key — copy to `.env`.                  |
| `.env`             | Your OpenAI API key (git-ignored, never committed).          |
| `docs.md`          | Course reference material used while building the agent.     |
| `MyPrompts.txt`    | Notes / prompt scratchpad from the course.                   |

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
Copy the template and fill in your real key:

```powershell
copy .env.example .env
```

Then open `.env` and set:

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

### Example output (trimmed)

```
### 🔬 Research trace
1. Detecting intent…
→ Ticker NVDA = NVIDIA Corporation (semiconductors, GPUs, AI).
2. Discovery search: `NVIDIA NVDA stock analysis`
→ Found 6 results.
3. Planning research angles…
→ Angle 1: `NVIDIA SWOT analysis 2026`
→ Angle 2: `NVIDIA stock performance last 12 months`
→ Angle 3: `NVIDIA competition and market positioning`
→ Angle 4: `NVIDIA latest quarterly results forward guidance`
4. Researching each angle…
5. Writing the report…

---

## NVIDIA (NVDA) — snapshot ...
## SWOT analysis ...
## Sources
[1] ... — https://...
```

## Configuration
All knobs live at the top of `agent.py`:

- `MODEL` — the OpenAI model (default `"openai:gpt-5-mini"`).
- `DISCOVERY_RESULTS` — results pulled in the initial discovery search (default `6`).
- `ANGLE_RESULTS` — results pulled per research angle (default `5`).

To change *how* the agent thinks or writes, edit the `system_prompt` of the
relevant agent (`intent_agent`, `angle_agent`, `report_agent`).

## Notes
- Web research uses DuckDuckGo via the `ddgs` package — **no search API key needed**.
- The report is grounded only in the search snippets the agent collected, and it
  cites its sources — but always sanity-check anything used for real decisions.
- `.env` is git-ignored, so your API key is never committed. Keep it that way.
- The CLI forces UTF-8 output, so emoji/accents in reports render correctly even
  on Windows consoles.
