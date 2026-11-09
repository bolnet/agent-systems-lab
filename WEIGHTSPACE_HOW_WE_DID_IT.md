# How we repeated MIT's weight-space programming experiments

This guide covers Experiments 1 and 5 from [Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/) (Takehi, Teoh, Zhang, Khattab): what the authors did, what we ran, every step between prompt and score, what went wrong, and where each log is. The shorter results report is [WEIGHTSPACE_REPLICATION.md](WEIGHTSPACE_REPLICATION.md), and the source of truth for every figure is the weight-space section of [BENCHMARK_LOG.md](BENCHMARK_LOG.md).

We ran 2 of the paper's 8 experiments. Experiments 2, 3, 4, 6, 7 and 8 were not run, so nothing here confirms or disputes them.

## Results

Experiment 5 asks a model to write a game-playing network from scratch in one reply. Scores are the mean over 1,000 games.

| Game | PPO, 500M steps (MIT's figure) | Astra, MIT's run | Astra, our run | Opus 5.5, our run |
|---|---|---|---|---|
| Breakout | 25.3 | 517.4 | 520.7 ± 8.1 | 559.6 ± 6.4 |
| Seaquest | 88.9 | 53.1 | 27.7 ± 0.7 | 63.5 ± 1.6 |
| Asterix | 55.2 | 53.2 | 59.9 ± 1.1 | 87.5 ± 1.5 |

Experiment 1 asks a model to name the game a trained network plays, from its weights alone.

| Game | Astra, MIT's run | Astra, our run | Opus 5.5, our run |
|---|---|---|---|
| Breakout | right, 99% | right, 98% | right, 93% |
| Pong | right, 96% | right, 97% | right, 80% |
| Pac-Man | right, 96% | right, 97% | right, 82% |
| Freeway | right, 97% | right, 97% | right, 80% |

Our Astra runs reproduce MIT's results, apart from Seaquest, which came out at about half their score. Opus scored higher than Astra on all three games, but each model replied once per game, so that lead is unproven. Astra's two Seaquest replies scored 53.1 and 27.7 from the same prompt.

## What weight-space programming means

A network normally gets its weights from gradient descent over many examples. Here, a language model reads or writes the weights directly as numbers. It gets no training, data, loss, gradients, or tools, and the network never plays before it is scored.

## MIT's materials

MIT published its logs at [RikiyaT/lm_understand-logs](https://github.com/RikiyaT/lm_understand-logs). The head of that repository when we checked was commit `4d09ba6d6a7e891dd8063974dfe81b3d78e3494f`. We took the following from it:

- the exact prompts (`runs/<game>/message.txt` for Experiment 5, `runs/<game>/prompt.txt` for Experiment 1)
- the system instructions, one line for every run: `Answer the user's request.`
- the reasoning effort: `xhigh` for Experiment 5, `high` for Experiment 1
- the scoring rules from each experiment's README
- MIT's own answers, networks and scores, used for comparison and for testing our code

MIT did not publish its reader for the `edits` language or its full keyword list for Experiment 1, so we wrote both from the rules MIT states.

## Setup

Run everything from the repo root:

```bash
pip install -r requirements-weightspace.txt
git clone https://github.com/RikiyaT/lm_understand-logs
```

`requirements-weightspace.txt` pins `minatar==1.0.15`, the game version MIT scored on. The clone is only needed to run new turns or compare prompts. The checks in [Check every result yourself](#check-every-result-yourself) work without it.

## Experiment 5, step by step

The commands below show the Opus and Astra forms for one game. We ran the same pair for Breakout, Seaquest and Asterix.

```bash
python -m context_clock.weightspace.replicate --exp 5 --engine opus --game breakout \
  --mit lm_understand-logs --out weightspace_runs
python -m context_clock.weightspace.replicate --exp 5 --engine astra --game breakout \
  --mit lm_understand-logs --out weightspace_runs
```

`context_clock/weightspace/replicate.py` then does the following.

1. It reads MIT's prompt without changing a byte. The prompt holds the task, the rules, the game's MinAtar source file, the input and output layout, the network, how it is scored, and the language for writing weights.
2. It asks the model once, in a fresh conversation with no tools.
3. It saves the reply as `answer.md`. `exp5.py` and `edits.py` read the last `edits` block in the reply and build the network.
4. It plays the network with `minatar_eval.py` and saves `score.json`.

### What the model has to write

The network is `600 -> 32 -> 32 -> 6` with tanh activations and 20,486 weights, and every weight starts at 0:

```
h1 = tanh(x @ W1 + b1)          W1: 600 x 32, b1: 32
h2 = tanh(h1 @ W2 + b2)         W2: 32 x 32,  b2: 32
logits = h2 @ W3 + b3           W3: 32 x 6,   b3: 6
```

The input is a 10 x 10 grid with 6 channels: player, danger, reward, projectile, trail and gauge. Input number `i` is `(row * 10 + column) * 6 + channel`. The six outputs are logits for no-op, left, up, right, down and fire.

The model sets weights in the `edits` language, for example:

```edits
W1[12, 0] = 2.5                     # one entry: row 12, column 0
b1[0:4] = -1                        # fill a range
W1[3:600:60, 0] = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]   # column 0 of channel 3, rows 0..9 -> unit 0
```

Statements apply in order, and a statement that can't be read is skipped. Every statement in all six of our replies was read with no errors. Replies are model output, so `edits.py` parses values with `ast.literal_eval` and never executes them.

### How a network is scored

`minatar_eval.py` follows the protocol in MIT's README:

- 1,000 episodes of MinAtar 1.0.15
- each action sampled from the softmax of the logits
- sticky actions at 0.1, so the game sometimes repeats the previous action
- each episode cut off at 10,000 steps

The random seed is 0, so replaying a network gives exactly the same score. The ± figure is the standard error over episodes. It says nothing about how a second reply from the same model would score.

### Run details

| Game | Model | Mean ± SE | Output tokens | Seconds | Statements read | Nonzero weights of 20,486 | Billed |
|---|---|---:|---:|---:|---:|---:|---:|
| Breakout | Astra | 520.707 ± 8.09 | 27,606 | 790.9 | 191 | 1,811 | $1.4130 |
| Seaquest | Astra | 27.663 ± 0.69 | 26,505 | 825.8 | 193 | 1,085 | $1.3829 |
| Asterix | Astra | 59.892 ± 1.08 | 24,944 | 761.4 | 119 | 780 | $1.2809 |
| Breakout | Opus 5.5 | 559.558 ± 6.44 | 92,210 | 840.7 | 172 | 1,217 | subscription |
| Seaquest | Opus 5.5 | 63.450 ± 1.57 | 107,504 | 1070.0 | 232 | 680 | subscription |
| Asterix | Opus 5.5 | 87.529 ± 1.51 | 66,210 | 622.8 | 275 | 709 | subscription |

## Experiment 1, step by step

```bash
python -m context_clock.weightspace.replicate --exp 1 --engine opus --game breakout \
  --mit lm_understand-logs --out weightspace_runs
```

We ran that on both models for Breakout, Pong, Pac-Man and Freeway, with Astra's four turns one at a time so that each saw the real spend before starting.

MIT trained these networks with PPO on its own 10 x 10 versions of the four games. Each is `500 -> 32 -> 32 -> 5` with 17,253 weights. The prompt describes the grid, the five channels (agent, moving objects, reward targets, obstacles, previous frame) and the actions in terms that fit any game, then lists every weight to 3 decimals. It names no games and offers no list to choose from. The model has to answer in this order: observations, reasoning, game, description, confidence.

`which_game.py` finds the `Game:` line and maps it to a game by keyword. Frogger counts as Freeway, as MIT's README says, and both of our models called that network Frogger.

The model's evidence is in the answer. Astra's Breakout reply, for example, starts from weights it can quote: `W1[405,15] = 4.066` is an agent input at row 8, and strong agent weights only on that row suggest a paddle. Compare [our Astra's answer](weightspace_runs/astra/exp1/breakout/answer.md) with [the prompt](weightspace_runs/astra/exp1/breakout/prompt.txt) to check any quoted value.

## How we reached each model

Our first route was Codex CLI, the same one MIT used. Codex 0.166.0 refused with "The 'gpt-6-astra' model is not supported when using Codex with a ChatGPT account", so `codex_run.py` stayed unused and Astra went through OpenRouter as `openai/gpt-6-astra`. The call is in `openrouter_run.py`:

```json
{
  "model": "openai/gpt-6-astra",
  "messages": [
    {"role": "system", "content": "Answer the user's request."},
    {"role": "user", "content": "<MIT's prompt>"}
  ],
  "reasoning": {"effort": "xhigh"},
  "max_tokens": "<set per turn, at most 64000>",
  "usage": {"include": true},
  "stream": true
}
```

The request has no `tools` field, so no tools can be called. The runner records `tool_free: true` for that reason; it doesn't inspect Astra's stream for tool calls.

Opus ran through `claude -p` on a subscription, from a new empty temp folder, with any API key removed from the environment. The command is saved in every `run.json`:

```bash
claude -p --model claude-opus-5-5 --effort xhigh --tools "" --setting-sources "" \
  --strict-mcp-config --disable-slash-commands --no-session-persistence \
  --system-prompt "Answer the user's request." --output-format stream-json --verbose
```

The prompt goes in on stdin. `claude_run.py` reads the event stream and marks the turn as not tool-free if any tool was offered or called. The CLI may still add text of its own, so Opus's setup isn't identical to a bare API call.

### Spending limit

Astra had a $10 cap. Before each turn, `allowed_output_tokens` adds up the cost recorded in every saved `run.json`, estimates the input cost at a pessimistic 1.5 characters per token, and sets `max_tokens` so that the worst case stays inside the cap at $10 and $50 per million tokens. The runner only retries before a reply starts, because a retry after that could be billed twice.

Astra came to $8.7446: $4.08 for Experiment 5, including a $0.00047 access check, and $4.67 for Experiment 1. The OpenRouter balance fell from $14.5358 to $5.7912, which matches exactly. Our estimate for Experiment 1 had been $3.29, and it came in higher because Astra wrote 4,111 to 7,215 output tokens where MIT's runs wrote 1,679 to 1,838.

Opus had no separate charge. Its logs do carry a `total_cost_usd` field from the CLI, adding up to $9.1362 across the seven turns. That is the CLI's own number and was never billed to us.

## Check every result yourself

`verify_runs.py` derives the results again from the saved replies. It calls no model and writes no files.

```bash
python -m context_clock.weightspace.verify_runs --no-play
python -m context_clock.weightspace.verify_runs --mit lm_understand-logs
```

The first command takes under a second and needs no game replays. The second replays all six networks and compares every prompt with MIT's, and took 4 minutes 25 seconds on our Mac. For each of the 14 model turns it checks:

- Experiment 5: the reply builds exactly the saved network, and replaying that network gives exactly the saved score.
- Experiment 1: marking the saved answer again gives the saved mark.
- Every turn: the saved audit says tool-free, and with `--mit`, the prompt is byte-identical to MIT's.

Our last run ended with `42 of 42 checks passed`.

We also ran MIT's own material through our code, because Opus wrote this code while also being one of the models compared. MIT's published Astra networks scored 502.88 ± 7.75, 55.157 ± 1.34 and 54.26 ± 1.07 on our scorer, against their 517.4 ± 7.42, 53.1 and 53.2. Our reader rebuilds all three of their `hand.npz` files exactly from their replies, and marks their four Experiment 1 answers correctly.

Don't use `replicate.py` to spot-check a score. It rewrites `score.json`, so running it with a different `--episodes` replaces the published figure. Use `minatar_eval.py` or `verify_runs.py`, which only read.

To run new turns, pass a new `--out` folder, because a folder with a saved `run.json` is never asked again. Spend is counted per `--out` folder, so a new folder also starts the cap from zero.

## What went wrong along the way

1. Codex refused Astra on a ChatGPT login, as described above. We moved to OpenRouter on the owner's instruction, which meant losing MIT's Codex wrapper and its detailed reasoning summaries.
2. Our first Experiment 1 reader missed `## Game` headings and marked Astra's Breakout, Pac-Man and Freeway answers blank. We fixed `which_game.py`, added tests and marked the saved answers again with no new model calls.
3. One of our spending-limit tests had the wrong arithmetic (19,800 where 18,000 is correct). The test was wrong and the code was right.
4. `tests/test_provider.py::test_complete_returns_text_and_real_token_counts` fails on our Mac because Ollama is running without `llama3.2`. It has nothing to do with this work and we left it alone.
5. Astra's token counts differ from MIT's. It read 2,616 to 4,609 input tokens on Experiment 5 here, where MIT's runs recorded 6,119 to 8,112, and it wrote far more on Experiment 1. We don't know why.

MIT hit a reader problem of its own: its first reader rejected some lists written as `[ [ ... ], ... ]`, then it fixed the reader and read the same replies again. Its README documents this.

## What the answers show

Both models write programs, with the weights as the code. Each Experiment 5 reply designs a controller first and then compiles it into numbers.

The trick is that large weights turn a tanh unit into a near on/off switch: a large positive input gives about +1 and a large negative one about -1. [Opus's Breakout reply](weightspace_runs/opus/exp5/breakout/answer.md) shows the whole pattern:

- Each unit in layer 1 adds up numbers from the ball, trail and paddle cells, so one linear unit can compute "landing column minus paddle column", including wall bounces. Opus writes these as `R = tanh(8(S-p-0.5))` for "move right". The largest weight in `W1` is 200.
- Layer 2 combines those signals with AND gates of the form "mode flag and direction".
- The output gives left and right a logit of +10 when their gate is on and -10 when it's off, so play is almost deterministic.

The reply also says what wasn't tested: "I traced this by hand through a full opening sequence and wall cases, but nothing has been run." It uses 1,217 of the 20,486 weights, and the rest stay at 0.

The Seaquest replies took different strategies. Astra fixed the submarine in one column, with horizontal movement disabled, and scored 27.7. Opus parked it against the left wall to shoot along rows and wait for divers to cross its column, and scored 63.5. We haven't measured how much of that gap comes from strategy and how much from mistakes in the weights.

A model gets one reply and never sees the result, so a bad decision stays in the score. PPO still wins Seaquest at 88.9.

## Where our runs differ from MIT's

- Astra ran through OpenRouter instead of Codex. Prompts, instructions and effort match.
- The token counts differ, as listed above, and the cause is unknown.
- We didn't retrain PPO, so the PPO column is MIT's figure.
- MIT's Experiment 1 keyword list isn't published, so ours is reconstructed. All eight of our answers name the game outright.
- Astra's reasoning in our logs is whatever OpenRouter passed along, which is short. Opus's reasoning isn't in the logs at all: the stream gives only token counts and an empty thinking block.

## Where the logs are

Each model turn has its own folder, `weightspace_runs/<engine>/exp<N>/<game>/`. The index is [weightspace_runs/README.md](weightspace_runs/README.md).

| File | What it holds |
|---|---|
| `prompt.txt` | The exact prompt sent, byte-identical to MIT's |
| `answer.md` | The model's full reply |
| `run.json` | Model, effort, command or route, seconds, tokens, cost, tool audit |
| `score.json` | The recorded score or mark |
| `apply.json` | Experiment 5 only: statements read, errors, nonzero weights, largest weight per tensor |
| `network.npz` | Experiment 5 only: the network built from the reply, with MIT's array names |
| `events.jsonl` | Opus only: the raw CLI event stream |
| `stderr.log` | Opus only: the CLI's stderr, empty in every run |
| `reasoning.txt` | Astra only: the reasoning text OpenRouter returned |

We changed one thing in the raw logs before publishing. In `events.jsonl`, the fields `cwd`, `original_cwd`, `memory_paths`, `messaging_socket_path` and `credential_expires_at` now read `[redacted]`, because they held local paths, including a username. Every other field is as the CLI wrote it, though each line was re-serialized as JSON.

Two things are not in this repo. The Astra stream was read as it arrived and not saved raw, so its record is `answer.md`, `reasoning.txt` and `run.json`. The chat session that built all this stays private, since it also holds unrelated personal context.

### Commits

- [`c726dc708c8488f4b0e190c26cffaaeb935f30ba`](https://github.com/bolnet/agent-systems-lab/commit/c726dc708c8488f4b0e190c26cffaaeb935f30ba) has the code, tests, answers, scores and first report.
- The commit after it adds this guide, `verify_runs.py`, the raw prompts, event logs and networks.
- [Pull request #22](https://github.com/bolnet/agent-systems-lab/pull/22) holds both.

`git log -- weightspace_runs context_clock/weightspace` lists them.

## Licences

The repo's MIT License covers our code. MIT's prompts, logs and networks are CC BY 4.0, from the authors of the paper, and the Experiment 1 prompts contain their network weights. The MinAtar source inside the Experiment 5 prompts, by Kenny Young and Tian Tian, is GPL-3.0, and its text is in [weightspace_runs/LICENSE-MinAtar](weightspace_runs/LICENSE-MinAtar).

## Showing it on video

These scenes use files and commands that exist today, and we ran each command.

1. Open the Experiment 5 prompt, [weightspace_runs/opus/exp5/breakout/prompt.txt](weightspace_runs/opus/exp5/breakout/prompt.txt). Point out "EVERY WEIGHT STARTS AT 0".
2. Open [the reply](weightspace_runs/opus/exp5/breakout/answer.md). Show the design, then the `edits` block of plain numbers.
3. Show that it had no tools: open `weightspace_runs/opus/exp5/breakout/run.json` and find `"tool_free": true`, then find the empty `"tools": []` in the first line of `events.jsonl`.
4. Play it live. This took about 4 seconds and gave 569.95 ± 42.71 over 20 games, and 1,000 games gave 559.558.

   ```bash
   python -m context_clock.weightspace.minatar_eval --game breakout \
     --npz weightspace_runs/opus/exp5/breakout/network.npz --episodes 20
   ```

5. Show the results table, including PPO at 25.3 on Breakout and 88.9 on Seaquest.
6. Move to Experiment 1. Scroll the wall of numbers in [the prompt](weightspace_runs/astra/exp1/freeway/prompt.txt), then open [the answer](weightspace_runs/astra/exp1/freeway/answer.md), which says Frogger.
7. Run the checker to show that the whole result set comes back from the saved files:

   ```bash
   python -m context_clock.weightspace.verify_runs --no-play
   ```

8. Finish with the limits: one reply per game, Seaquest varied from 53.1 to 27.7, and six experiments were not run.

The repo has no way to draw a game being played. The scorer only prints numbers, so footage of a network playing Breakout would need a small renderer first.
