"""Defluffer — strip fluff from LLM prompts to reduce token usage."""

from .core import CompressionResult, Defluffer, compress, estimate_tokens

__all__ = [
    "CompressionResult",
    "Defluffer",
    "compress",
    "estimate_tokens",
]

__version__ = "1.0.0"
