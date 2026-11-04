# Repeating MIT's weight-space programming experiments

We reran two of the eight experiments in [Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/) (Takehi, Teoh, Zhang, Khattab) with their prompts, networks and scoring rules. GPT-6 Astra did what they reported on both, though its Seaquest score came out at about half of theirs. We also gave Opus 5.5 the same prompts, and it scored higher than Astra on all three games. Each game got one run per model, so that lead is a first result and doesn't yet establish that Opus is better.

Every figure here is recorded in `BENCHMARK_LOG.md`. The prompts, answers, networks and raw logs are in `weightspace_runs/`. For every step from prompt to score, see [WEIGHTSPACE_HOW_WE_DID_IT.md](WEIGHTSPACE_HOW_WE_DID_IT.md).

## What weight-space programming means

An ordinary network gets its weights from gradient descent over many examples. In these experiments a language model reads or writes the weights directly as numbers. It gets no training, data, loss, gradients, or tools, and it never sees the network play.

## Experiment 5: writing a player from scratch

Each model gets the game's rules and source code, a 600 -> 32 -> 32 -> 6 tanh network with all 20,486 weights at zero, and a small language for setting them. It replies once. We build the network from the last `edits` block and play 1,000 episodes, sampling actions from the softmax, with sticky actions at 0.1 and a 10,000-step cap.

| Game | PPO, 500M steps (MIT) | Astra, MIT's run | Astra, our run | Opus 5.5, our run |
|---|---|---|---|---|
| Breakout | 25.3 | 517.4 | 520.7 ± 8.1 | 559.6 ± 6.4 |
| Seaquest | 88.9 | 53.1 | 27.7 ± 0.7 | 63.5 ± 1.6 |
| Asterix | 55.2 | 53.2 | 59.9 ± 1.1 | 87.5 ± 1.5 |

We did not retrain the PPO networks, so that column is MIT's. Against it, written networks win Breakout by a factor of 20 or more. On Asterix, Opus's network beats the PPO score and Astra's two runs land near it. PPO still leads on Seaquest.

The ± figures only measure how precisely 1,000 episodes pin down one network's score. They say nothing about how much a second reply from the same model would differ. Astra's two Seaquest replies scored 53.1 and 27.7 from the same prompt, a gap far larger than either error bar. To compare the models properly, each one needs several replies per game.

## How the models do it

Both models wrote programs, with the weights as the code. Their replies design a controller first and then compile it into numbers. Neither tried to imitate what training would produce.

Very large weights turn tanh units into near-perfect logic gates, since a large positive input gives about +1 and a large negative one about -1. The Breakout networks show the pattern. In the first layer, each unit adds up numbers from the ball, trail and paddle cells, so a single linear unit can compute "landing column minus paddle column" including wall bounces. The second layer combines these signals with AND gates, and the output layer turns the gates into large action logits, so play is almost deterministic. Opus's reply states that it solved its landing-position tables by hand and traced an opening sequence, with nothing run.

The two models' Seaquest designs may help explain why results vary between runs. Astra fixed the submarine in one column, disabled horizontal movement and scored 27.7. Opus parked it against the left wall as a turret that shoots along rows and waits for divers to cross its column, and scored 63.5. Each model commits to one strategy with no chance to test it. We haven't measured how much of the score gap comes from the strategy and how much from errors in the weights.

## Experiment 1: naming a game from its weights

Each model gets all 17,253 weights of a trained network as text, along with channel and action meanings that describe no game in particular. It has to name the game. None of the four prompts contains a game's name.

| Game | Astra, MIT's run | Astra, our run | Opus 5.5, our run |
|---|---|---|---|
| Breakout | right, 99% | right, 98% | right, 93% |
| Pong | right, 96% | right, 97% | right, 80% |
| Pac-Man | right, 96% | right, 97% | right, 82% |
| Freeway | right, 97% | right, 97% | right, 80% |

Both models got four of four. Astra and Opus both called the Freeway network Frogger, which MIT's rules count as correct. Astra's reasoning cites specific weights: strong agent weights confined to the bottom row suggest a paddle, and reward weights confined to the top rows suggest bricks.

## Where our runs differ from MIT's

- OpenAI refuses `gpt-6-astra` on a ChatGPT login in Codex, with the message "not supported when using Codex with a ChatGPT account". We reached Astra through OpenRouter, so MIT's Codex wrapper and its detailed reasoning summaries weren't part of our runs. Effort, instructions and prompts match.
- Astra read 2,616 to 4,609 input tokens on Experiment 5 here, where MIT's runs recorded 6,119 to 8,112. On Experiment 1 it wrote 4,111 to 7,215 output tokens, where MIT's wrote 1,679 to 1,838. We have not established the cause of either gap.
- MIT's full keyword list for scoring Experiment 1 isn't published, so ours is reconstructed. All eight of our answers name the game outright, and the same reader marks MIT's four answers correctly.
- Our first Experiment 1 reader missed `## Game` headings and marked three correct Astra answers as blank. We fixed it, added tests, and marked the saved answers again with no new model calls.
- Opus ran through `claude -p` with tools, settings, hooks and MCP servers off. The CLI may still add text of its own, so Opus's setup isn't identical to a bare API call.
- Opus wrote this code and this report while also being one of the models compared. As an outside check on the scorer, we played MIT's published Astra networks through it. It gave 502.9 ± 7.7, 55.2 ± 1.3 and 54.3 ± 1.1, against their 517.4 ± 7.4, 53.1 and 53.2. The reader also rebuilds all three of their networks exactly.

## Not rerun

Experiments 2, 3, 4, 6, 7 and 8 were not run. Experiment 4 would have taken Astra past the $10 budget at MIT's token counts and needs a Kinetix scorer. Experiment 8 needs rented GPUs, roughly estimated at $150 to $220.

## Cost

Astra cost $8.74 on OpenRouter: $4.08 for Experiment 5, including a $0.0005 access check, and $4.67 for Experiment 1. The account balance fell by exactly that amount. Opus ran on a Claude subscription with no separate charge.

## Running it

```bash
pip install -r requirements-weightspace.txt
python -m context_clock.weightspace.replicate --exp 5 --engine opus --game breakout \
  --mit PATH_TO_MIT_LOGS --out weightspace_runs
```

`--engine astra` reads `OPENROUTER_API_KEY` from the environment or `.env`, and stops any call whose worst case could take recorded spend past $10. Run Astra jobs one at a time when the remaining budget is small, because each call checks spend only when it starts. A finished turn is never asked again, so rerunning only repeats the scoring.
