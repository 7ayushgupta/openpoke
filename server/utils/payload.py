"""Shared utilities for encoding and decoding payload strings."""

from __future__ import annotations

from html import escape, unescape


def encode_payload(payload: str) -> str:
    """Encode payload for storage by normalizing line endings and escaping HTML.
    
    Args:
        payload: The raw payload string to encode
        
    Returns:
        HTML-escaped string with normalized line endings (\\n for newlines)
    """
    normalized = payload.replace("\r\n", "\n").replace("\r", "\n")
    collapsed = normalized.replace("\n", "\\n")
    return escape(collapsed, quote=False)


def decode_payload(payload: str) -> str:
    """Decode payload from storage by unescaping HTML and restoring newlines.
    
    Args:
        payload: The encoded payload string to decode
        
    Returns:
        Decoded string with restored newlines
    """
    return unescape(payload).replace("\\n", "\n")


__all__ = ["encode_payload", "decode_payload"]

