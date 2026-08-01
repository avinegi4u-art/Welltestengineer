"""Defluffer core — local, regex-based prompt fluff removal."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .dictionaries import PROFILES, Dictionary

_WORD_RE = re.compile(r"\b[a-zA-Z0-9_'-]+\b")
_TOKEN_SPLIT_RE = re.compile(r"(\b[a-zA-Z0-9_'-]+\b)")
_PROT_RE = re.compile(r"^PROT\d+PROT$")
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_URL_RE = re.compile(r"https?://[^\s)\]}>,]+")
# Require an underscore so common acronyms (JSON, API, HTML) stay editable.
_ENV_RE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")
_PATH_RE = re.compile(r"(?:\.\.?/|/|[A-Za-z]:\\)[^\s,;:)\]}]+")
_FLAG_RE = re.compile(r"--[a-zA-Z0-9][a-zA-Z0-9_-]*")
_QUOTED_RE = re.compile(r"(['\"])(?:(?!\1).|\\.)*\1")
_SENSITIVE_RE = re.compile(
    r"\b(?:do not|don't|never)\s+replace\s+defined\s+terms?[^.?!]*",
    re.IGNORECASE,
)
_YAML_LINE_RE = re.compile(r"^\s{0,8}[A-Za-z0-9_-]+:\s*(?:[^\n]*)\r?\n?$")
_ADJ_DUP_RE = re.compile(r"\b([A-Za-z][A-Za-z'-]*)([\s,]+)\1\b", re.IGNORECASE)

_EXACT_SENSITIVE_CHECKS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\blegal meaning\b", re.IGNORECASE), "legal meaning"),
    (re.compile(r"\bdefined terms?\b", re.IGNORECASE), "defined terms"),
    (re.compile(r"\b(MUST|SHOULD|MAY)\b"), "RFC/legal keywords"),
    (
        re.compile(r"\bdo not replace defined terms?\b", re.IGNORECASE),
        "defined-term preservation",
    ),
    (
        re.compile(r"\boutput only the file content\b", re.IGNORECASE),
        "exact file content",
    ),
]


@dataclass(frozen=True)
class CompressionResult:
    """Detailed result of a compress pass."""

    original: str
    text: str
    profile: str
    original_tokens: int
    defluffed_tokens: int
    saved_tokens: int
    savings_pct: float
    changed: bool
    safe: bool
    reason: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class _Span:
    start: int
    end: int
    text: str


def escape_regex(value: str) -> str:
    return re.escape(value)


def estimate_tokens(text: str) -> int:
    """Cheap local token estimate (not model-specific)."""
    normalized = text.strip()
    if not normalized:
        return 0
    pieces = re.findall(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]", normalized)
    total = 0
    for piece in pieces:
        if re.fullmatch(r"[A-Za-z0-9_]+", piece):
            total += max(1, int((len(piece) + 4.2 - 1e-9) // 4.2))
        else:
            total += 1
    return total


def cleanup(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^\s*[,;:]\s*", "", text)
    text = re.sub(r"\s+([.,?!;:)\]}])", r"\1", text)
    text = re.sub(r"([({\[])\s+", r"\1", text)
    text = re.sub(r",{2,}", ",", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r",[.\s]*,", ",", text)
    text = re.sub(r"\.\s*,", ".", text)
    text = re.sub(r",\s*([.!?])", r"\1", text)
    text = re.sub(r"\?\s*\.+", "?", text)
    text = re.sub(r"!\s*\.+", "!", text)
    text = re.sub(r"\.\s*\?", "?", text)
    text = re.sub(r"\.\s*!", "!", text)
    text = re.sub(r"^!+\s+(?=[A-Za-z])", "", text)
    return text.strip()


def _non_overlapping(spans: Iterable[_Span]) -> list[_Span]:
    result: list[_Span] = []
    for span in sorted(spans, key=lambda s: (s.start, -(s.end - s.start))):
        if any(span.start < kept.end and span.end > kept.start for kept in result):
            continue
        result.append(span)
    return result


def find_json_spans(text: str) -> list[_Span]:
    spans: list[_Span] = []
    start = 0
    while start < len(text):
        opener = text[start]
        if opener not in "{[":
            start += 1
            continue

        stack = ["}" if opener == "{" else "]"]
        in_string = False
        escaped = False
        i = start + 1
        while i < len(text):
            char = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                i += 1
                continue

            if char == '"':
                in_string = True
            elif char in "{[":
                stack.append("}" if char == "{" else "]")
            elif char in "}]":
                if not stack or stack.pop() != char:
                    break
                if not stack:
                    candidate = text[start : i + 1]
                    try:
                        json.loads(candidate)
                        spans.append(_Span(start, i + 1, candidate))
                        start = i
                    except json.JSONDecodeError:
                        pass
                    break
            i += 1
        start += 1
    return _non_overlapping(spans)


def find_yaml_spans(text: str) -> list[_Span]:
    lines = re.split(r"(?<=\n)", text)
    spans: list[_Span] = []
    offset = 0
    block_start: Optional[int] = None
    block_end = 0
    yaml_lines = 0

    def flush() -> None:
        nonlocal block_start, block_end, yaml_lines
        if block_start is not None and yaml_lines >= 2:
            text_block = text[block_start:block_end].rstrip()
            spans.append(
                _Span(block_start, block_start + len(text_block), text_block)
            )
        block_start = None
        block_end = 0
        yaml_lines = 0

    for line in lines:
        bare = line.rstrip("\r\n")
        if _YAML_LINE_RE.match(line) and ". " not in bare:
            if block_start is None:
                block_start = offset
            block_end = offset + len(line)
            yaml_lines += 1
        elif bare.strip() == "" and block_start is not None:
            block_end = offset + len(line)
        else:
            flush()
        offset += len(line)
    flush()
    return _non_overlapping(spans)


def _protect_spans(text: str, spans: list[_Span], protected: list[str]) -> str:
    for span in sorted(spans, key=lambda s: s.start, reverse=True):
        protected.append(span.text)
        placeholder = f"PROT{len(protected) - 1}PROT"
        text = text[: span.start] + placeholder + text[span.end :]
    return text


def _protect_structured(text: str, protected: list[str]) -> str:
    text = _protect_spans(text, find_json_spans(text), protected)
    text = _protect_spans(text, find_yaml_spans(text), protected)
    return text


def _protect_extended(text: str, protected: list[str]) -> str:
    patterns = (
        _CODE_FENCE_RE,
        _INLINE_CODE_RE,
        _URL_RE,
        _ENV_RE,
        _PATH_RE,
        _FLAG_RE,
        _QUOTED_RE,
    )
    for pattern in patterns:

        def _repl(match: re.Match[str], _protected: list[str] = protected) -> str:
            value = match.group(0)
            if _PROT_RE.match(value):
                return value
            _protected.append(value)
            return f"PROT{len(_protected) - 1}PROT"

        text = pattern.sub(_repl, text)
    return text


def _protect_sensitive(text: str, protected: list[str]) -> str:
    def _repl(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"PROT{len(protected) - 1}PROT"

    return _SENSITIVE_RE.sub(_repl, text)


def _apply_phrase_map(
    text: str, mapping: dict[str, str], protected: list[str]
) -> str:
    entries = sorted(
        ((p, r) for p, r in mapping.items() if p),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for phrase, replacement in entries:
        regex = re.compile(rf"\b{escape_regex(phrase)}\b", re.IGNORECASE)

        def _repl(
            _match: re.Match[str],
            _replacement: str = replacement,
            _protected: list[str] = protected,
        ) -> str:
            if not _replacement or not _replacement.strip():
                return " "
            _protected.append(_replacement)
            return f"PROT{len(_protected) - 1}PROT"

        text = regex.sub(_repl, text)
    return text


def _apply_token_map(
    text: str, blacklist: set[str], synonyms: dict[str, str]
) -> str:
    parts: list[str] = []
    for token in _TOKEN_SPLIT_RE.split(text):
        if not _WORD_RE.fullmatch(token):
            parts.append(token)
            continue
        if _PROT_RE.match(token):
            parts.append(token)
            continue
        lower = token.lower()
        if lower in blacklist:
            parts.append("")
            continue
        if lower in synonyms:
            parts.append(synonyms[lower])
            continue
        parts.append(token)
    return "".join(parts)


def _restore_protected(text: str, protected: list[str]) -> str:
    for index, item in enumerate(protected):
        placeholder = f"PROT{index}PROT"
        while placeholder in text:
            text = text.replace(placeholder, item)
    return text


def _remove_adjacent_duplicates(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _ADJ_DUP_RE.sub(r"\1", text)
    return text


def _artifact_warnings(text: str, original: str) -> list[str]:
    warnings: list[str] = []
    if not re.match(r"^\s*[,;:]", original) and re.match(r"^\s*[,;:]", text):
        warnings.append("leading punctuation artifact")
    if re.search(r"\bI\s+am\s+need\b", text, re.IGNORECASE):
        warnings.append("grammar artifact: I am need")
    if re.search(r"[?!]\s*\.(?:\s|$)", text):
        warnings.append("punctuation artifact")
    return warnings


def looks_exact_sensitive(text: str) -> Optional[str]:
    """Return a reason if the prompt should not be aggressively rewritten."""
    for regex, reason in _EXACT_SENSITIVE_CHECKS:
        if regex.search(text):
            return reason
    return None


def extract_protected_spans(text: str) -> list[str]:
    code_blocks = _CODE_FENCE_RE.findall(text)
    without_fences = _CODE_FENCE_RE.sub(" ", text)
    return [
        *code_blocks,
        *[span.text for span in find_json_spans(without_fences)],
        *[span.text for span in find_yaml_spans(without_fences)],
        *_INLINE_CODE_RE.findall(without_fences),
        *_URL_RE.findall(text),
        *_ENV_RE.findall(text),
        *_FLAG_RE.findall(text),
    ]


class Defluffer:
    """Compress verbose prompts by removing fluff, filler, and verbose phrasing.

    Example:
        >>> from defluffer import Defluffer
        >>> defluffer = Defluffer()
        >>> defluffer.compress("Could you please summarize this?")
        'summarize this?'
    """

    def __init__(
        self,
        profile: str = "standard",
        dictionaries: Optional[Dictionary] = None,
        *,
        skip_sensitive: bool = True,
    ) -> None:
        if dictionaries is not None:
            self._dict: Dictionary = dictionaries
            self.profile = "custom"
        else:
            if profile not in PROFILES:
                known = ", ".join(sorted(PROFILES))
                raise ValueError(f"Unknown profile {profile!r}. Choose from: {known}")
            self._dict = PROFILES[profile]
            self.profile = profile
        self.skip_sensitive = skip_sensitive

    def compress(self, prompt: str) -> str:
        """Return a defluffed prompt string."""
        return self.compress_detailed(prompt).text

    def compress_detailed(self, prompt: str) -> CompressionResult:
        """Return a detailed compression result with token estimates and warnings."""
        original_tokens = estimate_tokens(prompt)
        warnings: list[str] = []

        if self.skip_sensitive:
            reason = looks_exact_sensitive(prompt)
            if reason:
                return CompressionResult(
                    original=prompt,
                    text=prompt,
                    profile=self.profile,
                    original_tokens=original_tokens,
                    defluffed_tokens=original_tokens,
                    saved_tokens=0,
                    savings_pct=0.0,
                    changed=False,
                    safe=True,
                    reason=f"skipped: {reason}",
                    warnings=warnings,
                )

        dict_ = self._dict
        protected_spans = extract_protected_spans(prompt)
        protected: list[str] = []
        text = prompt

        text = _protect_structured(text, protected)
        text = _protect_extended(text, protected)
        if dict_.get("guard_sensitive"):
            text = _protect_sensitive(text, protected)

        blacklist = set(dict_.get("blacklist") or [])
        for entry in blacklist:
            if " " not in entry:
                continue
            text = re.sub(
                rf"\b{escape_regex(entry)}\b", "", text, flags=re.IGNORECASE
            )

        phrase_map = {
            **(dict_.get("phrases") or {}),
            **(dict_.get("logic") or {}),
        }
        text = _apply_phrase_map(text, phrase_map, protected)
        text = _apply_token_map(text, blacklist, dict_.get("synonyms") or {})
        if dict_.get("dedupe_adjacent_words"):
            text = _remove_adjacent_duplicates(text)
        text = cleanup(text)
        text = _restore_protected(text, protected).strip()

        missing = [span for span in protected_spans if span not in text]
        if missing:
            warnings.append(f"protected span changed ({len(missing)})")

        original_had_negation = bool(
            re.search(r"\b(must not|do not|never|not|without|no)\b", prompt, re.I)
        )
        next_has_negation = bool(
            re.search(r"\b(must not|do not|never|not|without|no)\b|!", text, re.I)
        )
        if original_had_negation and not next_has_negation:
            warnings.append("negation marker lost")

        warnings.extend(_artifact_warnings(text, prompt))

        defluffed_tokens = estimate_tokens(text)
        saved = original_tokens - defluffed_tokens
        savings = (saved / original_tokens * 100.0) if original_tokens else 0.0
        safe = len(warnings) == 0

        return CompressionResult(
            original=prompt,
            text=text,
            profile=self.profile,
            original_tokens=original_tokens,
            defluffed_tokens=defluffed_tokens,
            saved_tokens=saved,
            savings_pct=savings,
            changed=text != prompt,
            safe=safe,
            reason=None if safe else "; ".join(warnings),
            warnings=warnings,
        )


def compress(
    prompt: str,
    profile: str = "standard",
    *,
    skip_sensitive: bool = True,
) -> str:
    """Module-level convenience wrapper around :class:`Defluffer`."""
    return Defluffer(profile=profile, skip_sensitive=skip_sensitive).compress(prompt)
