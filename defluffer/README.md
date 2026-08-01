# Defluffer

Local, zero-dependency Python tool that strips fluff and filler from LLM prompts to cut token usage — typically ~35–50% on verbose natural-language prompts.

Inspired by [GrahamTheDev’s Defluffer](https://dev.to/grahamthedev/defluffer-reduce-token-usage-by-45-26jj).

## Install

From this repo:

```bash
pip install -e ./defluffer
```

Or add the `src` path to `PYTHONPATH`:

```bash
export PYTHONPATH=defluffer/src:$PYTHONPATH
```

## Usage

```python
from defluffer import Defluffer

defluffer = Defluffer()
user_prompt = "Your verbose prompt here..."
compressed_prompt = defluffer.compress(user_prompt)
```

Module-level helper:

```python
from defluffer import compress

compressed = compress("Could you please summarize this ASAP? Thank you!")
```

Detailed metrics:

```python
result = Defluffer().compress_detailed(user_prompt)
print(result.text, result.savings_pct, result.warnings)
```

### Profiles

| Profile | Behavior |
|---------|----------|
| `standard` (default) | Phrase collapse, synonyms, filler blacklist, guarded sensitive spans, adjacent-word dedupe |
| `safe` | Pleasantries + light synonyms only |
| `standardGuardedDedupe` | Alias of `standard` |

### CLI

```bash
defluffer "Could you please refactor this code? Thank you so much!" --stats
echo "Hello there, please summarize..." | defluffer --stats
```

## What it protects

- Fenced and inline code
- Detected JSON / YAML snippets
- URLs, `ENV_VARS`, CLI flags, quoted strings
- Legal / defined-term / exact-file-output prompts (skipped by default)

## Notes

- Runs entirely locally — no API calls.
- Best for polite, verbose task prompts. Avoid blind use on legal, policy, or exact-wording tasks.
- Compression is syntactic; verify critical prompts still carry the intent you need.

## Tests

```bash
pip install -e "./defluffer[dev]"
pytest defluffer/tests
```
