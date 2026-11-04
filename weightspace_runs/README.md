# Weight-space programming run logs

These are the saved runs behind [WEIGHTSPACE_REPLICATION.md](../WEIGHTSPACE_REPLICATION.md). The step-by-step account is in [WEIGHTSPACE_HOW_WE_DID_IT.md](../WEIGHTSPACE_HOW_WE_DID_IT.md).

```
astra/access_check/          a $0.00047 test call to confirm access to the model
astra/exp1/<game>/           GPT-6 Astra through OpenRouter, Experiment 1
astra/exp5/<game>/           GPT-6 Astra through OpenRouter, Experiment 5
opus/exp1/<game>/            Opus 5.5 through claude -p, Experiment 1
opus/exp5/<game>/            Opus 5.5 through claude -p, Experiment 5
LICENSE-MinAtar              GPL-3.0 text for the MinAtar source in the Experiment 5 prompts
```

Experiment 1 games are `breakout`, `pong`, `pacman` and `freeway`. Experiment 5 games are `breakout`, `seaquest` and `asterix`.

To check every result from these files, run this from the repo root. It calls no model and writes nothing:

```bash
python -m context_clock.weightspace.verify_runs
```

## Licences and credit

The prompts and the Experiment 1 weights inside them come from "Sparks of Weight-Space Programming" by Takehi, Teoh, Zhang and Khattab, published at https://github.com/RikiyaT/lm_understand-logs under CC BY 4.0. We use them unchanged.

Each Experiment 5 prompt contains a game's source file from MinAtar 1.0.15 (https://github.com/kenjyoung/MinAtar) by Kenny Young and Tian Tian, unchanged, with its author header. That source is GPL-3.0, and the licence text is in `LICENSE-MinAtar`.

In the Opus `events.jsonl` files, the fields `cwd`, `original_cwd`, `memory_paths`, `messaging_socket_path` and `credential_expires_at` were replaced with `[redacted]` because they held local paths.
