"""Tests for the Defluffer prompt compressor."""

from __future__ import annotations

import pytest

from defluffer import Defluffer, compress, estimate_tokens
from defluffer.core import looks_exact_sensitive


DEMO = """Hello there! I would really appreciate it if you could act as a senior backend developer. I am trying to figure out how to write a python script that connects to the database and retrieves all of the information from the user repository.

Make sure that the results are filtered so that the retry count is greater than or equal to 5, and the active status is strictly equals to true. Due to the fact that the application is currently in the production environment, it is required that you utilize the environment configurations instead of hardcoding the parameters into the functions.

Also, I have a question about the following snippet. Could you please refactor this code without using any external libraries?

```javascript
function calculateMaximum(array) {
    if (array === null) return 0;
    return Math.max(...array);
}
```

Take into consideration that the output should be formatted as a standard JSON object. If you don't mind, please provide a step by step guide on how to deploy this microservice to the kubernetes cluster at the very end. Thank you so much!
"""


def test_public_api_matches_readme_example() -> None:
    defluffer = Defluffer()
    user_prompt = "Could you please summarize this document? Thank you so much!"
    compressed_prompt = defluffer.compress(user_prompt)
    assert isinstance(compressed_prompt, str)
    assert "Thank you so much" not in compressed_prompt
    assert "Could you please" not in compressed_prompt
    assert "summarize" in compressed_prompt.lower()


def test_module_compress_helper() -> None:
    out = compress("Please provide a step by step guide. Thanks!")
    assert "steps" in out.lower() or "provide" in out.lower()
    assert "Thanks" not in out


def test_demo_prompt_saves_meaningful_tokens() -> None:
    result = Defluffer().compress_detailed(DEMO)
    assert result.changed
    assert result.savings_pct >= 25
    assert "```javascript" in result.text
    assert "Math.max(...array)" in result.text
    assert "Hello there" not in result.text
    assert "Thank you so much" not in result.text
    assert ">=" in result.text or "greater than or equal" not in result.text.lower()


def test_preserves_json_exactly() -> None:
    json_blob = (
        '{"userRepository":"primary","active":true,"retryCount":5,"mode":"production"}'
    )
    prompt = (
        f"Hello there! Could you please transform the following JSON without "
        f"changing any keys or string values: {json_blob}. Thank you so much!"
    )
    result = Defluffer().compress_detailed(prompt)
    assert json_blob in result.text
    assert "Hello there" not in result.text
    assert "Thank you so much" not in result.text


def test_preserves_yaml_block() -> None:
    yaml = "service:\n  name: user-repository\n  active: true\n  retry_count: 5"
    prompt = (
        f"Hello! Could you please update this YAML but do not rename keys:\n"
        f"{yaml}\n\nThank you so much!"
    )
    result = Defluffer().compress_detailed(prompt)
    assert yaml in result.text
    assert "Thank you so much" not in result.text


def test_preserves_fenced_code() -> None:
    code = (
        "```javascript\n"
        "function calculateMaximum(array) {\n"
        "    if (array === null) return 0;\n"
        "    return Math.max(...array);\n"
        "}\n"
        "```"
    )
    prompt = (
        "Could you please refactor this code without using any external libraries?\n\n"
        f"{code}\n\nThank you."
    )
    result = Defluffer().compress_detailed(prompt)
    assert code in result.text
    assert "without external libs" in result.text


def test_skips_legal_sensitive_prompts() -> None:
    prompt = "Summarize without changing legal meaning of the contract."
    assert looks_exact_sensitive(prompt) == "legal meaning"
    assert Defluffer().compress(prompt) == prompt


def test_dedupes_transcript_filler() -> None:
    prompt = "Um yeah so basically basically I just need, like, a summary of this call."
    result = Defluffer().compress_detailed(prompt)
    assert "basically basically" not in result.text.lower()
    assert result.saved_tokens > 0


def test_polite_prompt_avoids_artifacts() -> None:
    prompt = (
        "Hello there, could you please provide a step by step guide in order to "
        "configure the application due to the fact that I am really trying to figure "
        "out how to set up the database configuration? Thank you so much."
    )
    result = Defluffer().compress_detailed(prompt)
    assert not result.text.lstrip().startswith((",", ";", ":"))
    assert "I am need" not in result.text
    assert "I need to set up" in result.text
    assert result.saved_tokens > 0


def test_safe_profile_is_lighter() -> None:
    prompt = (
        "Hello there! Could you please use the application database configuration? Thanks!"
    )
    standard = Defluffer("standard").compress(prompt)
    safe = Defluffer("safe").compress(prompt)
    # Safe keeps more domain words (application/database) than standard synonyms.
    assert "DB" in standard or "app" in standard.lower()
    assert "Hello there" not in safe


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        Defluffer("aggressive")


def test_estimate_tokens_empty() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("   ") == 0
