"""Model, price and budget settings for the Astra-through-OpenRouter runs."""

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-6-astra"
INPUT_USD_PER_TOKEN = 10.0 / 1_000_000
OUTPUT_USD_PER_TOKEN = 50.0 / 1_000_000
CHARS_PER_TOKEN = 1.5  # MIT's weight-heavy prompts measured 1.56; lower means a safer budget check.
BUDGET_USD = 10.0
MAX_OUTPUT_TOKENS = 64_000  # MIT's largest Experiment 5 turn used 28,993.
MIN_OUTPUT_TOKENS = 2_000
STREAM_TIMEOUT_SECONDS = 900
