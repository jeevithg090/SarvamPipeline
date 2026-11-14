import pytest

from language import TTS_LANGUAGES, choose_tts_language, detect_language_from_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("नमस्ते, आप कैसे हैं?", "hi-IN"),
        ("আপনি কেমন আছেন", "bn-IN"),
        ("ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "pa-IN"),
        ("કેમ છો", "gu-IN"),
        ("ନମସ୍କାର", "od-IN"),
        ("வணக்கம்", "ta-IN"),
        ("నమస్కారం", "te-IN"),
        ("ನಮಸ್ಕಾರ", "kn-IN"),
        ("നമസ്കാരം", "ml-IN"),
        ("Hello, how are you?", "en-IN"),
    ],
)
def test_detects_script(text, expected):
    assert detect_language_from_text(text) == expected
    assert expected in TTS_LANGUAGES


def test_majority_script_wins_in_mixed_text():
    assert detect_language_from_text("ok नमस्ते दोस्तों") == "hi-IN"
    assert detect_language_from_text("Please book a cab यार") == "en-IN"


@pytest.mark.parametrize("text", ["", "123 !?", "🙂🙂"])
def test_falls_back_to_default_without_letters(text):
    assert detect_language_from_text(text) == "en-IN"
    assert detect_language_from_text(text, default="hi-IN") == "hi-IN"


def test_choose_prefers_supported_stt_language():
    # Marathi shares Devanagari with Hindi; STT can tell them apart.
    assert choose_tts_language("mr-IN", "तुम्ही कसे आहात") == "mr-IN"


@pytest.mark.parametrize("stt_language", [None, "unknown", "ur-IN"])
def test_choose_falls_back_to_script_detection(stt_language):
    assert choose_tts_language(stt_language, "வணக்கம்") == "ta-IN"
    assert choose_tts_language(stt_language, "...", default="hi-IN") == "hi-IN"
