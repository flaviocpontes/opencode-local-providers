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
    # ── chat label includes, regardless of recipe ──

    def test_gufo_engine_chat_model_included(self):
        m = Model(id="Qwen3.8-27B-Gufo", recipe="gufo",
                  labels=["chat", "reasoning", "tool-calling", "vision", "mtp"])
        assert is_chat_model(m) is True

    @pytest.mark.parametrize("recipe", [
        "llamacpp", "llamacpp-hrx", "ryzenai-llm", "vllm", "ds4", "rocmfpx",
        "gufo", "halogen", "flm", "ollama",
    ])
    def test_chat_label_included_regardless_of_recipe(self, recipe):
        m = Model(id="x", recipe=recipe, labels=["chat"])
        assert is_chat_model(m) is True

    def test_omni_capability_mix_included(self):
        m = Model(id="Qwen2.5-Omni-7B", recipe="llamacpp",
                  labels=["chat", "vision", "chat-transcription"])
        assert is_chat_model(m) is True

    def test_chat_outranks_deployment_label(self):
        m = Model(id="Gemma-4", recipe="llamacpp",
                  labels=["chat", "vision", "reasoning", "transcription"])
        assert is_chat_model(m) is True

    # ── deployment labels exclude ──

    @pytest.mark.parametrize("label", [
        "embeddings", "embedding", "reranking", "transcription", "tts", "image",
        "audio-generation", "classification", "classifier", "3d",
    ])
    def test_deployment_label_excluded(self, label):
        m = Model(id="x", recipe="llamacpp", labels=[label])
        assert is_chat_model(m) is False

    def test_capability_labels_do_not_beat_deployment(self):
        m = Model(id="x", recipe="llamacpp", labels=["vision", "transcription"])
        assert is_chat_model(m) is False

    # ── no mode label: default chat (label-less user models) ──

    def test_label_less_user_model_included(self):
        m = Model(id="user.MyModel-GGUF", recipe="llamacpp", labels=[])
        assert is_chat_model(m) is True

    def test_capability_only_labels_included(self):
        m = Model(id="x", recipe="llamacpp",
                  labels=["vision", "tool-calling", "mtp"])
        assert is_chat_model(m) is True

    def test_chat_transcription_alone_defaults_to_chat(self):
        m = Model(id="Qwen2.5-Omni", recipe="llamacpp",
                  labels=["chat-transcription"])
        assert is_chat_model(m) is True

    def test_realtime_transcription_alone_still_chat(self):
        # realtime-transcription is a WebSocket capability, not a deployment mode
        m = Model(id="x", recipe="llamacpp", labels=["realtime-transcription"])
        assert is_chat_model(m) is True

    # ── collection recipes exclude ──

    def test_collection_omni_excluded_even_with_chat(self):
        m = Model(id="x", recipe="collection.omni", labels=["chat"])
        assert is_chat_model(m) is False

    def test_collection_router_excluded(self):
        m = Model(id="x", recipe="collection.router", labels=[])
        assert is_chat_model(m) is False

    # ── Ollama adapter label encoding ──

    def test_ollama_chat_marker_included(self):
        m = Model(id="qwen3:8b", recipe="ollama", labels=["vision", "chat"])
        assert is_chat_model(m) is True

    def test_ollama_not_chat_marker_excluded(self):
        m = Model(id="nomic-embed-text", recipe="ollama", labels=["not-chat"])
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
        ("gemma4:latest", "gemma4"),
        ("qwen3:8b", "qwen3:8b"),
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
