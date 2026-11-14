"""Language selection for the TTS voice.

Bulbul v3 speaks 11 languages. We prefer the language reported by the STT
engine (it can tell Marathi from Hindi, which share a script) and fall back
to counting characters per Unicode script block in the transcript.
"""

from __future__ import annotations

# Language codes accepted by Bulbul v3 (`target_language_code`).
TTS_LANGUAGES: frozenset[str] = frozenset(
    {
        "bn-IN",
        "en-IN",
        "gu-IN",
        "hi-IN",
        "kn-IN",
        "ml-IN",
        "mr-IN",
        "od-IN",
        "pa-IN",
        "ta-IN",
        "te-IN",
    }
)

# (first code point, last code point, language) — one entry per script block.
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0900, 0x097F, "hi-IN"),  # Devanagari
    (0x0980, 0x09FF, "bn-IN"),  # Bengali
    (0x0A00, 0x0A7F, "pa-IN"),  # Gurmukhi
    (0x0A80, 0x0AFF, "gu-IN"),  # Gujarati
    (0x0B00, 0x0B7F, "od-IN"),  # Odia
    (0x0B80, 0x0BFF, "ta-IN"),  # Tamil
    (0x0C00, 0x0C7F, "te-IN"),  # Telugu
    (0x0C80, 0x0CFF, "kn-IN"),  # Kannada
    (0x0D00, 0x0D7F, "ml-IN"),  # Malayalam
    (0x0041, 0x005A, "en-IN"),  # Latin upper
    (0x0061, 0x007A, "en-IN"),  # Latin lower
)


def detect_language_from_text(text: str, default: str = "en-IN") -> str:
    """Return the TTS language whose script dominates `text`.

    Returns `default` when the text contains no letters from a known script.
    Ties are broken by the order of `_SCRIPT_RANGES`.
    """
    counts: dict[str, int] = {}
    for char in text:
        code = ord(char)
        for start, end, lang in _SCRIPT_RANGES:
            if start <= code <= end:
                counts[lang] = counts.get(lang, 0) + 1
                break
    if not counts:
        return default
    best = max(counts.values())
    for _, _, lang in _SCRIPT_RANGES:
        if counts.get(lang) == best:
            return lang
    return default  # pragma: no cover - unreachable


def choose_tts_language(stt_language: str | None, text: str, default: str = "en-IN") -> str:
    """Pick the TTS language for a reply to `text`.

    Uses the STT-reported language when Bulbul can speak it, otherwise the
    script-based guess.
    """
    if stt_language in TTS_LANGUAGES:
        return stt_language
    return detect_language_from_text(text, default=default)
