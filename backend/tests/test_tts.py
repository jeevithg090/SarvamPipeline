import json

from tts import SentenceChunker, text_message, tts_config


def test_first_sentence_released_immediately():
    chunker = SentenceChunker(min_chars=40)
    assert chunker.feed("Hi") is None
    assert chunker.feed("!") == "Hi!"


def test_later_sentences_batched_until_min_chars():
    chunker = SentenceChunker(min_chars=20)
    assert chunker.feed("Hello.") == "Hello."
    assert chunker.feed(" Yes.") is None
    assert chunker.feed(" That works for me.") == " Yes. That works for me."


def test_devanagari_danda_is_a_sentence_boundary():
    chunker = SentenceChunker()
    assert chunker.feed("नमस्ते।") == "नमस्ते।"


def test_flush_returns_remainder_and_ignores_whitespace():
    chunker = SentenceChunker()
    chunker.feed("no boundary yet")
    assert chunker.flush() == "no boundary yet"
    assert chunker.flush() is None
    chunker.feed("   ")
    assert chunker.flush() is None


def test_messages_are_valid_json():
    assert json.loads(text_message("hi")) == {"type": "text", "data": {"text": "hi"}}
    config = tts_config("ta-IN", "shubh")
    assert config["data"]["target_language_code"] == "ta-IN"
    assert config["data"]["speaker"] == "shubh"
