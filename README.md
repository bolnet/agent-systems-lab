# agent-systems-lab

**Reproducible research on production AI agents: what they cost, how to judge them, and what frontier models
can do.** Four studies, every number re-runnable from committed logs. MIT, runs locally on
[Ollama](https://ollama.com) or against any OpenRouter model, 413 tests.

> Formerly `context-clock`. The Python package and CLI keep that name (`python -m context_clock.run`).

## The experiments

| # | Study | Headline result | Read |
|---|---|---|---|
| 1 | **Context clock**: token growth vs. memory | Re-sending the conversation grows input tokens O(n²); retrieved memory cuts them **~21×** at **100% recall**, identically across six open and closed models | [live](https://bolnet.github.io/agent-systems-lab/) · [deep-dive](https://bolnet.github.io/agent-systems-lab/context-clock-benchmark.html) · [details below](#study-1-context-clock) |
| 2 | **cachecost**: where agent money goes with prompt caching | A lapsed cache rewrites the same prefix at 1.25× instead of 0.1×: a **12.5× jump on identical work**; 30 claims checked against the price card | [token economics](https://bolnet.github.io/agent-systems-lab/agent-token-economics.html) · [`CACHE_CLAIMS.md`](CACHE_CLAIMS.md) · [`CACHECOST_METHODOLOGY.md`](CACHECOST_METHODOLOGY.md) |
| 3 | **Typed judges**: typed decision models as code-review judges | Nine systems on a 150-case known-verdict corpus; we caught our own faked 30/30 (the label leaked through file paths). Against Claude on 1,834 questions: Claude Opus 5 **91.5%**, Jev 85.4%; Claude 5.5 rerun: Opus 5.5 **94.5%** | [report](https://bolnet.github.io/agent-systems-lab/typed-judges/report.html) · [Claude 5.5 rerun](https://bolnet.github.io/agent-systems-lab/typed-judges-claude-5-5/report.html) · [`REPORT.md`](docs/typed-judges/REPORT.md) |
| 4 | **Weight-space programming**: replicating MIT's experiments | Models write all 20,486 weights of a game-playing network directly, with no training; on Breakout, Opus 5.5's network scored **559.6** vs 25.3 for MIT's PPO at 500M steps | [page](https://bolnet.github.io/agent-systems-lab/weight-space-programming.html) · [`WEIGHTSPACE_REPLICATION.md`](WEIGHTSPACE_REPLICATION.md) · [how we did it](WEIGHTSPACE_HOW_WE_DID_IT.md) |

---

## Study 1: Context clock

### The finding

Re-sending the whole conversation to the model every turn (the default agent loop) makes the
**input tokens** it must read grow **O(n²)** — a parabola that compounds with every session.
You have two bad options, and one good one:

| Strategy | Input tokens | Recall |
|---|---|---|
| **Grow the context** (re-send all) | **O(n²)** — 1.33M by turn 100 (gpt-5.4) | 100% |
| **Cap the context** (truncate old) | flat-ish | **rots to 0% by turn 10** |
| **Retrieve what's needed** (memory) | **O(n)** — flat ~200 tok/call | **100%** |

Capping is mechanical: once the window fills, the oldest turns drop and recall decays in an
identical staircase (`100% ×7 → 67 → 33 → 0`) from a 3B model to a 671B one. Retrieval escapes
the trap — flat per-call context **and** perfect recall.

### Input-token reduction at turn 100 — measured, 6 models, 100% recall both sides

| Model | Provider | input × | cost (raw → mem) |
|---|---|---|---|
| gpt-5.4 | OpenAI | **21.5×** | $0.57 → $0.19 |
| gpt-5.4-mini | OpenAI | **21.5×** | $0.22 → $0.06 |
| claude-opus-4 | Anthropic | **22.2×** | $24.15 → $1.24 |
| claude-sonnet-4 | Anthropic | **22.1×** | $4.83 → $0.25 |
| kimi-k2.6 | Moonshot (open) | **21.0×** | $0.43 → $0.17 |
| deepseek-v3.2 | DeepSeek (open) | **22.5×** | $0.16 → $0.009 |

Input × is set by workload geometry, not the model — every model traces the same curve:
5.6× (t24) → 11× (t50) → 16× (t75) → ~21–22.5× (t100). *Cost* reduction varies with provider
prompt-caching and answer verbosity; **input tokens are the universal number.**

---

## Quickstart

### Local, zero-cost (Ollama — no API keys)
```bash
ollama pull llama3.2                       # 3B dev model, arc completes fast
python -m context_clock.run --until-rotted --turns 100   # watch input go O(n²), recall rot
python -m context_clock.run --memory --turns 100         # the fix: flat context, 100% recall
```

### Any model via OpenRouter
```bash
export OPENROUTER_API_KEY=sk-or-...
python -m context_clock.run --provider openrouter --model openai/gpt-5.4 \
  --until-rotted --turns 100 --probe-max-tokens 2048
```

### Against a real memory backend (Attestor)
```bash
# with a local `attestor api` running on :8090
python -m context_clock.run --provider openrouter --model openai/gpt-5.4 \
  --memory --memory-backend attestor --turns 100 --cadence 1
```

Each run prints the per-turn arc and writes `results/<tag>.csv` + a chart. API runs record the
**real billed cost** from OpenRouter's `usage.cost` — not list-price math.

## What it measures

- **Input (context) tokens** — the tokens the model reads each turn. This is the hero metric:
  raw grows quadratically; memory stays flat. (Output tokens are the model's answer, unchanged
  by memory, so they're excluded from "what memory saves.")
- **Recall** — answer-level grading: an unpredictable code (`k9f3a2`) is planted in each memo;
  we ask for a specific memo's code later and check the exact string comes back.
- **Cost** — real billed dollars per call (OpenRouter `usage.cost`).

## Knobs

| Knob | Meaning |
|------|---------|
| `--model` | Ollama name, or an OpenRouter slug with `--provider openrouter` |
| `--turns` | session length (the curve is most dramatic at 100) |
| `--until-rotted` | rot stress test: probe every turn, run until recall stays at 0% |
| `--memory` / `--memory-backend {retrieval,attestor}` | retrieve-what's-needed instead of re-sending all |
| `--client-window N` | cap an API model's prompt to N tokens (reproduces cap-and-rot) |
| `--cadence` | probe every N turns |
| `--probe-max-tokens` | answer budget per probe (raise for reasoning models) |

## Where the money goes — the cache-cost ledger

Growing context does not just cost tokens, it costs *differently* depending on whether the prompt
cache is warm. Cached prefixes bill at **0.1×** the input rate; the moment a 5-minute entry lapses,
the same prefix is rewritten at **1.25×** — a **12.5× jump on identical work**. `cachecost` prices
that cliff and validates 30 claims from a talk on Claude Code session economics:

```bash
python -m context_clock.cachecost.verify --scenarios   # the ledger, re-derived from the price card
```

Findings and evidence live in **[`CACHE_CLAIMS.md`](CACHE_CLAIMS.md)**. Two that matter:

- The heartbeat break-even is **12.5 cache reads** — ~50 minutes of keep-warm. Past that, take the
  miss. Between ~30 and ~60 minutes idle, a 1-hour TTL beats both.
- A miss is not only a clock event. A cache breakpoint walks back at most **20 content blocks**, so
  one turn appending more than 20 — routine in an agentic loop — misses with *zero* elapsed time,
  at the same 12.5× penalty. No timing rule fixes that one.

## Reproduce

```bash
pip install -r requirements.txt && pytest   # 413 tests (one needs a local Ollama model), deterministic, no network
```

`BENCHMARK_LOG.md` is the committed source of truth — every measured run, every number, with CSV
pointers. `CACHE_CLAIMS.md` is its counterpart for the cache-cost work: every verdict re-derives
from the published price card at print time, and nothing there is presented as measured.

## The fix

context-clock measures the problem. **[Attestor](https://attestor.dev)** is the open-source
memory layer that fixes it — flat ~200 tokens per call, 21× fewer input tokens, 100% recall, two
API calls (`add()` / `recall()`). Both tools are MIT.

## License

MIT. No lock-in.

## Related report

[Typed decision models as code-review judges](docs/typed-judges/REPORT.md) ([page](https://bolnet.github.io/agent-systems-lab/typed-judges/report.html)) — Jev and every open-source Jev-class alternative on a 150-case known-verdict review corpus: the label leak that faked a 30/30, the grader route a constant answer can game, and per-question calibration for each system; updated 2026-09-27 with CLM-8B, the Stanford/NVIDIA open System One model, on the same questions (Jev 86.5%, CLM-8B 56.1%).
