# model-filtering Specification

## Purpose

Defines how sync decides which Lemonade server models are chat models for `opencode.json`: classification driven by the server-reported labels, mirroring Lemonade's own deployment-mode semantics, so new inference engines are picked up without tool updates. Ollama's capability-based detection is specified separately in `ollama-support`.

## Requirements

### Requirement: Chat models are identified by the chat label, regardless of recipe

Sync SHALL include a Lemonade model in the provider entry when its labels contain `chat`, whatever its recipe is. The recipe field SHALL NOT be used to allow or deny chat models — except the collection composites excluded by the "Collection recipes are excluded" requirement — so models served by any current or future engine (llamacpp, llamacpp-hrx, ryzenai-llm, vllm, ds4, rocmfpx, gufo, halogen, flm, or newer) are included by their labels alone.

#### Scenario: Model on a new engine is included

- **WHEN** the server lists a downloaded model `Qwen3.8-27B-Gufo` with recipe `gufo` and labels `[chat, reasoning, tool-calling, vision, mtp]`
- **THEN** sync includes it in the provider entry's models map

#### Scenario: Chat model with mixed capability labels stays chat

- **WHEN** a downloaded model's labels are `[chat, vision, chat-transcription]` (any-to-text omni model)
- **THEN** sync includes it as a chat model

#### Scenario: The chat label outranks a deployment label

- **WHEN** a downloaded model's labels contain `chat` together with a deployment label such as `transcription`
- **THEN** sync includes it as a chat model

### Requirement: Deployment labels exclude a model

Sync SHALL exclude a Lemonade model whose labels contain any deployment label and do not contain `chat`. Deployment labels are `embeddings`, `embedding`, `reranking`, `transcription`, `tts`, `image`, `audio-generation`, `classification`, `classifier`, and `3d`.

#### Scenario: Embedding model excluded

- **WHEN** a model's labels are `[embeddings]`
- **THEN** it does not appear in the provider entry

#### Scenario: New deployment modes are excluded

- **WHEN** a model's labels are `[audio-generation]`, `[classification]`, or `[3d]`
- **THEN** it does not appear in the provider entry

#### Scenario: Capability-only labels no longer force inclusion

- **WHEN** a model's labels are `[vision, transcription]` with no `chat` label
- **THEN** it does not appear in the provider entry

### Requirement: Models without mode labels are included

A Lemonade model whose labels name no mode at all (neither `chat` nor any deployment label) SHALL be included, mirroring Lemonade's default that a label-less model deploys as an LLM. This preserves user-installed models registered without explicit labels.

#### Scenario: Label-less user model included

- **WHEN** a downloaded model `user.MyModel-GGUF` reports recipe `llamacpp` and no labels
- **THEN** sync includes it in the provider entry

#### Scenario: Model with only capability labels included

- **WHEN** a downloaded model's labels are `[vision, tool-calling, mtp]` with no mode label
- **THEN** sync includes it in the provider entry

### Requirement: Collection recipes are excluded

Sync SHALL exclude models whose recipe is `collection.omni` or `collection.router`, even when their labels contain `chat`, because collections are composite routers rather than standalone chat models.

#### Scenario: Omni collection excluded

- **WHEN** the server lists a model with recipe `collection.omni` and labels `[chat]`
- **THEN** it does not appear in the provider entry

#### Scenario: Router collection excluded

- **WHEN** the server lists a model with recipe `collection.router`
- **THEN** it does not appear in the provider entry
