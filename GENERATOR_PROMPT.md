# Generator Prompt

> This is a self-contained prompt. Paste it into an AI coding agent (Claude Code,
> Cursor, etc.) inside an empty directory to regenerate this entire repository from
> scratch. It encodes every requirement, file, and design decision.

---

## PROMPT

You are building a **public, educational GitHub repository** for a graduate finance
course ("IA Generativa y Mercado de Capitales", Magíster en Finanzas, Universidad de
los Andes). The repo is a reference implementation of a **multi-agent AI system** that
builds a stock portfolio. The audience is finance students who are new to coding.

### Pedagogical goal
The class lesson: a single loose prompt produces inconsistent results because the AI
fills unspecified gaps with its defaults. The fix is **process** — split the task into
roles with explicit criteria. This repo demonstrates that with a team of 4 agents.

The metaphor (from the lecture) maps directly to code:
- **Agent** = the worker (a role).
- **Skills** = what it knows how to do = its **prompt**.
- **Tools** = real-world connections it can execute = **Python functions**.

### Hard requirements
1. **Public & secret-safe**: a strict `.gitignore`, a `.env.example` with placeholders,
   and **zero** real secrets anywhere. API keys load only from the environment.
2. **Pedagogical & easy**: a finance student can install and run it in ~5 steps.
3. **Transparent & editable**: students must be able to **see and change** each agent
   easily. Each agent is its own human-readable file; the LLM plumbing is hidden away.
4. **LLM-agnostic**: works with Claude, OpenAI, or Gemini — the student drops in any
   one API key and the same code runs. Changing provider = changing one line.
5. **Live data**: market data comes live from Yahoo Finance via `yfinance` (no
   committed CSV).
6. **Language**: all docs, prompts, and comments in **Spanish**; code identifiers
   (variables, functions) in **English**.

### Architecture
The pedagogical heart is the `agents/` folder: **one self-contained file per agent**,
with YAML frontmatter (model, temperature, tools) + the Spanish prompt below it (same
format as Claude Code subagents). The LLM plumbing lives behind a single `chat()`
function using **litellm**, so the thing students touch is the agent, not the wiring.

```
.
├── README.md              # Spanish: what it is, install, run, edit agents, security
├── config.yaml            # default model, ticker universe, portfolio parameters
├── .env.example           # key placeholders (copy to .env)
├── .gitignore             # ignores .env, venvs, caches, output/, OS files
├── requirements.txt       # litellm, yfinance, pandas, numpy, pyyaml, python-dotenv, rich
├── run.py                 # entry point: `python run.py`
├── agents/                # ⭐ what students read and edit
│   ├── research.md
│   ├── quant.md
│   ├── risk.md
│   └── portfolio_manager.md
├── src/
│   ├── __init__.py
│   ├── config.py          # loads config.yaml + .env (python-dotenv)
│   ├── llm.py             # agnostic chat() over litellm, supports tool-calling
│   ├── agent.py           # Agent class: parses the .md, runs the tool-calling loop
│   ├── tools.py           # tools: list_universe, get_market_data, compute_metrics
│   └── orchestrator.py    # runs Research→Quant→Risk→PM, prints each turn (rich)
├── docs/
│   ├── COMO_FUNCIONA.md       # maps Agent/Skills/Tools to the lecture; the flow
│   └── COMO_EDITAR_AGENTES.md # how to change prompt/model/temp/tools; add an agent
└── output/
    └── .gitkeep           # generated reports go here (gitignored except .gitkeep)
```

### The 4 agents (sequential pipeline, each builds on the prior output)
1. **Research** — `tools: [list_universe, get_market_data]`, temperature ~0.4.
   Filters the universe to a shortlist of candidates with brief justification.
2. **Quant** — `tools: [compute_metrics]`, temperature ~0.1. Computes return,
   volatility, Sharpe, and average correlation; ranks by risk/return profile.
3. **Risk** — `tools: [compute_metrics]`, temperature ~0.2. Drops overly volatile or
   highly correlated names and flags concentration (max weight from config).
4. **Portfolio Manager** — `tools: []`, temperature ~0.3. Synthesizes the team's work
   into the final N-stock portfolio with weights (summing to 100%, none above the cap)
   and a one-line rationale per position, output as a markdown table + summary.

An **orchestrator** coordinates this flow, passing each agent the previous agents'
outputs as context, printing every turn with `rich` (a colored panel per agent showing
which tools it called and its conclusion), and saving the PM's final report to
`output/cartera_YYYYMMDD_HHMM.md`.

### Agent file format (example `agents/research.md`)
```markdown
---
name: research
role: Analista de Research
model: default          # "default" inherits config.yaml; or override e.g. openai/gpt-4o
temperature: 0.4
tools: [list_universe, get_market_data]
---

Eres el Analista de Research de un equipo de inversión institucional...
(Spanish prompt = the agent's "skills": how it works, its criteria, what it delivers)
```

### `src/` implementation notes
- **config.py**: `load_config()` reads `config.yaml`; `load_dotenv()` loads `.env` into
  the environment. Export `AGENTS_DIR` and `OUTPUT_DIR` paths relative to the repo root.
- **llm.py**: a single `chat(model, messages, tools, temperature, max_tokens)` calling
  `litellm.completion(...)` and returning `response.choices[0].message`. Set
  `litellm.suppress_debug_info = True`. Students rarely touch this file.
- **agent.py**: an `Agent` class that parses frontmatter + body (split on `---`),
  resolves `model: default` against config, and runs a **tool-calling loop**: call the
  LLM; if it returns `tool_calls`, execute each via the tools registry, append results
  as `{"role": "tool", "tool_call_id": ..., "content": ...}`, and repeat until the
  model returns plain text. Cap iterations (~8). Append assistant messages back via
  `message.model_dump()`. Accept an optional `on_tool(name, args)` callback for display.
- **tools.py**: three functions returning JSON strings — `list_universe()`,
  `get_market_data(tickers, period)`, `compute_metrics(tickers, period)`. Use
  `yf.download(..., auto_adjust=True)["Close"]`, handle the single-vs-multi-ticker
  shape, annualize with 252 trading days, Sharpe = annual_return/annual_vol (rf=0), and
  average pairwise correlation per ticker. Provide a `TOOL_REGISTRY` (name→function),
  `TOOL_SCHEMAS` (OpenAI-style function-calling schemas, descriptions in Spanish), a
  `run_tool(name, arguments)` dispatcher that catches exceptions and returns them as
  JSON, and `schemas_for(tool_names)`.
- **orchestrator.py**: `run_pipeline()` reads portfolio params from config, prints the
  mission, runs the 4 agents in order with `rich` panels, threads prior outputs into
  each agent's task string, then saves the report. Use `datetime.now()` for the
  filename stamp.
- **run.py**: calls `run_pipeline()` inside a try/except that prints a friendly Spanish
  troubleshooting message (deps installed? `.env` created? model matches the key?
  internet?) instead of a raw traceback.

### `config.yaml` shape
```yaml
llm:
  model: "anthropic/claude-sonnet-4-6"   # or openai/gpt-4o, gemini/gemini-2.0-flash
  temperature: 0.3
  max_tokens: 4096
universe:
  tickers: [AAPL, MSFT, NVDA, GOOGL, AMZN, ...]   # ~25 large-cap US tickers, commented
portfolio:
  size: 10
  lookback_period: "1y"
  max_weight: 0.20
```

### Security (public repo) — critical
- `.gitignore` must cover: `.env`, `.env.*` (with `!.env.example`), `__pycache__/`,
  `*.py[cod]`, `.venv/`, `venv/`, `output/*` (with `!output/.gitkeep`), `.DS_Store`,
  `.vscode/`, `.idea/`.
- `.env.example` contains placeholders only (`ANTHROPIC_API_KEY=tu_key_aqui`, plus
  OpenAI and Gemini lines) and instructions to `cp .env.example .env`.
- No key in any tracked file, ever. README has a security section: never commit `.env`,
  check `git status` before pushing, revoke a leaked key immediately.

### `requirements.txt`
`litellm`, `yfinance`, `pandas`, `numpy`, `pyyaml`, `python-dotenv`, `rich`.

### Documentation (Spanish)
- **README.md**: hero description tying to the class, an ASCII diagram of the 4-agent
  team, a 5-step quickstart (clone → venv + `pip install` → `cp .env.example .env` →
  paste key → `python run.py`), a provider/key table (Claude/OpenAI/Gemini with where
  to get each key), an "edit the agents" section showing the frontmatter, a security
  section, a project-structure tree, and an educational disclaimer (not financial
  advice). Requires Python 3.9+.
- **docs/COMO_FUNCIONA.md**: maps Agent/Skills/Tools to the lecture, explains the flow
  and why process beats a loose prompt, and traces what happens during one run.
- **docs/COMO_EDITAR_AGENTES.md**: anatomy of an agent file, a table of frontmatter
  fields, things to try (change prompt/temperature/model, change universe/limits), the
  list of available tools, and how to add a brand-new agent (create the `.md`, wire it
  into the orchestrator, optionally add a tool to `tools.py`).

### Verification before finishing
1. Create a venv, `pip install -r requirements.txt`, confirm imports.
2. Test the data tools directly (no API key) against live yfinance.
3. Confirm agents parse and `model: default` resolves; orchestrator imports cleanly.
4. Run `python run.py` with no key → confirm the graceful Spanish error message.
5. (With a key) run the full pipeline → 4 agent turns print and a report is saved.
6. Confirm `git status` does NOT show `.env`; scan staged content for real key patterns.

Build all files now. Keep the code clean and well-commented (comments in Spanish),
favor clarity over cleverness, and make the `agents/` files the obvious place a student
goes to change behavior.
