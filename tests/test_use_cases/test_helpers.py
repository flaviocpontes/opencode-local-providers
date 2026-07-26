"""Tests for helper functions: model filtering, name derivation, entry building."""

import pytest

from opencode_config.use_cases.helpers import (
    is_chat_model,
    derive_display_name,
    model_to_entry,
)
from opencode_config.domain.entities import Model


# ── is_chat_model ──────────────────────────────────────────────────────

class TestIsChatModel:
    def test_llamacpp_no_labels(self):
        m = Model(id="x", recipe="llamacpp", labels=[])
        assert is_chat_model(m) is True

    def test_llamacpp_vision(self):
        m = Model(id="x", recipe="llamacpp", labels=["vision", "tool-calling"])
        assert is_chat_model(m) is True

    def test_llamacpp_reasoning(self):
        m = Model(id="x", recipe="llamacpp", labels=["reasoning"])
        assert is_chat_model(m) is True

    def test_sd_cpp_excluded(self):
        m = Model(id="x", recipe="sd-cpp", labels=["image"])
        assert is_chat_model(m) is False

    def test_whispercpp_excluded(self):
        m = Model(id="x", recipe="whispercpp", labels=["transcription"])
        assert is_chat_model(m) is False

    def test_kokoro_excluded(self):
        m = Model(id="x", recipe="kokoro", labels=["tts"])
        assert is_chat_model(m) is False

    def test_collection_omni_excluded(self):
        m = Model(id="x", recipe="collection.omni", labels=[])
        assert is_chat_model(m) is False

    def test_embedding_label_excluded(self):
        m = Model(id="x", recipe="llamacpp", labels=["embeddings"])
        assert is_chat_model(m) is False

    def test_image_label_excluded(self):
        m = Model(id="x", recipe="llamacpp", labels=["image"])
        assert is_chat_model(m) is False

    def test_tts_label_excluded(self):
        m = Model(id="x", recipe="llamacpp", labels=["tts"])
        assert is_chat_model(m) is False

    def test_transcription_label_excluded(self):
        m = Model(id="x", recipe="llamacpp", labels=["transcription"])
        assert is_chat_model(m) is False


# ── derive_display_name ────────────────────────────────────────────────

class TestDeriveDisplayName:
    @pytest.mark.parametrize("model_id,expected", [
        ("user.Qwen3.6-27B-GGUF-UD-Q4_K_XL", "Qwen3.6-27B"),
        ("Gemma-4-31B-it-GGUF", "Gemma-4-31B"),
        ("Hermes-4.3-36B-GGUF-Q4_K_M", "Hermes-4.3-36B"),
        ("Qwen3.5-27B-GGUF", "Qwen3.5-27B"),
        ("gpt-oss-120b-mxfp-GGUF", "gpt-oss-120b-mxfp"),
        ("GLM-4.7-Flash-GGUF", "GLM-4.7-Flash"),
        ("Qwen3.5-122B-A10B-MTP-GGUF", "Qwen3.5-122B-A10B-MTP"),
        ("Flux-2-Klein-4B", "Flux-2-Klein-4B"),
        ("kokoro-v1", "kokoro-v1"),
        ("Qwen3.6-40B-Claude-4.6-Opus-Deckard-Heretic-Uncensored-Thinking-NEO-CODE-Di-IMatrix-MAX-GGUF-Q4_K_M",
         "Qwen3.6-40B-Deckard-Heretic-Uncensored"),
    ])
    def test_derivations(self, model_id, expected):
        assert derive_display_name(model_id) == expected


# ── model_to_entry ─────────────────────────────────────────────────────

class TestModelToEntry:
    def test_basic_llm(self):
        m = Model(id="GLM-4.7-Flash-GGUF", max_context_window=202752,
                  labels=[], recipe="llamacpp")
        entry = model_to_entry(m)
        assert entry["name"] == "GLM-4.7-Flash"
        assert entry["limit"]["context"] == 202752
        assert entry["limit"]["output"] == 32768
        assert "modalities" not in entry

    def test_vision_model(self):
        m = Model(id="Gemma-4-31B-it-GGUF", max_context_window=262144,
                  labels=["vision"], recipe="llamacpp")
        entry = model_to_entry(m)
        assert entry["name"] == "Gemma-4-31B"
        assert entry["limit"]["context"] == 262144
        assert entry["modalities"] == {
            "input": ["text", "image", "pdf"],
            "output": ["text"],
        }

    def test_reasoning_model(self):
        m = Model(id="gpt-oss-120b-mxfp-GGUF", max_context_window=131072,
                  labels=["reasoning"], recipe="llamacpp")
        entry = model_to_entry(m)
        assert entry["name"] == "gpt-oss-120b-mxfp"
        assert entry["limit"]["context"] == 131072
        assert entry["limit"]["output"] == 65536

    def test_no_context_window(self):
        m = Model(id="no-ctx-model", recipe="llamacpp")
        entry = model_to_entry(m)
        assert entry["name"] == "no-ctx-model"
        assert entry["limit"]["output"] == 32768
        assert "context" not in entry["limit"]

    def test_user_model(self):
        m = Model(id="user.Qwen3.6-27B-GGUF-UD-Q4_K_XL",
                  max_context_window=262144, labels=[], recipe="llamacpp")
        entry = model_to_entry(m)
        assert entry["name"] == "Qwen3.6-27B"
        assert entry["limit"]["context"] == 262144
